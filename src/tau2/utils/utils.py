import hashlib
import importlib.metadata
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from deepdiff import DeepDiff
from dotenv import load_dotenv
from loguru import logger

res = load_dotenv()
if not res:
    logger.warning("No .env file found")

# Try to get data directory from environment variable first
DATA_DIR_ENV = os.getenv("TAU2_DATA_DIR")

if DATA_DIR_ENV:
    # Use environment variable if set
    DATA_DIR = Path(DATA_DIR_ENV)
    logger.info(f"Using data directory from environment: {DATA_DIR}")
else:
    # Fallback to source directory (for development)
    SOURCE_DIR = Path(__file__).parents[3]
    DATA_DIR = SOURCE_DIR / "data"
    logger.info(f"Using data directory from source: {DATA_DIR}")

# Check if data directory exists and is accessible
if not DATA_DIR.exists():
    logger.warning(f"Data directory does not exist: {DATA_DIR}")
    logger.warning(
        "Set TAU2_DATA_DIR environment variable to point to your data directory"
    )
    logger.warning("Or ensure the data directory exists in the expected location")


def get_dict_hash(obj: dict) -> str:
    """
    Generate a unique hash for dict.
    Returns a hex string representation of the hash.
    """
    hash_string = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(hash_string.encode()).hexdigest()


def normalize_for_compare(obj):
    """Recursively normalize a JSON-serializable structure for
    order-insensitive comparison.

    All lists are sorted by their JSON serialization, recursively. The
    transformation is applied symmetrically to both sides of any
    comparison, so any incidental sorting of an order-meaningful list
    affects both sides equally and does not change the result of an
    equality test — equality after normalization corresponds to
    multiset equality of list elements.

    Used by construction-task scoring to compare developer-toolkit DB
    state against reference-toolkit DB state. The two toolkits often
    diverge on conventional list ordering (e.g. the reference's
    ``return_delivered_order_items`` does ``sorted(item_ids)`` before
    storing while the developer's stores in user-call order; the
    reference's ``modify_pending_order_payment`` records
    ``payment_history`` as ``[charge, refund]`` while the developer's
    records ``[refund, charge]``) without any difference in semantic
    meaning. Sorting before hashing forgives those conventions.

    Caveat: this can also forgive list orderings that genuinely matter
    (e.g. flight segments in a round-trip reservation, or items in an
    order). For construction-task scoring this trade-off is the right
    call — the developer is graded on building a working domain, not
    on byte-level reproduction of the reference's conventions.
    """
    if isinstance(obj, dict):
        return {k: normalize_for_compare(v) for k, v in obj.items()}
    if isinstance(obj, list):
        normalized = [normalize_for_compare(x) for x in obj]
        # Sort by canonical JSON representation. ``sort_keys`` makes the
        # serialization deterministic; ``default=str`` handles non-JSON
        # primitives (e.g. datetimes).
        return sorted(
            normalized, key=lambda x: json.dumps(x, sort_keys=True, default=str)
        )
    # Coerce numeric types to a single canonical form so int/float schema
    # choices don't diverge on serialization. Without this, a price stored
    # as ``int`` in one schema and ``float`` in another (e.g. ``87`` vs
    # ``87.0``) hashes differently. Treat bool separately — bool is a
    # subclass of int in Python but must not be coerced to float here.
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        return float(obj)
    return obj


def canonicalize_new_ids(pred_state: dict, gold_state: dict) -> tuple[dict, dict]:
    """Pair newly-created entity IDs across predicted and gold states and
    rename both sides to canonical placeholders.

    Tau2 DBs are dicts of dicts: ``state[table_name][entity_id] = entity``.
    During scoring, "new" entities are those whose ID appears in one
    side but not the other (the agent and the gold action sequence
    created them with different IDs — common when the ID generator is
    a hardcoded fixture like the airline reference's ``["HATHAT",
    "HATHAU", "HATHAV"]`` or an arbitrary scheme like a developer's
    ``"RSV0001"``). The exact ID is a detail no scoring-correct
    implementation should care about.

    Pairing is content-based: within each table, sort the one-sided
    entries by their JSON content (excluding fields that are just the
    ID echo'd back) and pair them positionally. Identical entities
    map to the same canonical placeholder regardless of which ID the
    generator happened to produce. The placeholder propagates through
    every cross-reference in the tree (e.g. ``user.reservations``
    lists, ``payment_history.payment_id``) by exact string match.

    Unpaired entries (one side has more new IDs than the other) get
    side-tagged placeholders so the hash mismatch still surfaces.
    """
    if not isinstance(pred_state, dict) or not isinstance(gold_state, dict):
        return pred_state, gold_state

    # ID-shaped fields that just echo the table key — exclude from
    # content hashing so the same entity matches regardless of which
    # ID it carries.
    _ID_FIELDS = {
        "id",
        "reservation_id",
        "order_id",
        "user_id",
        "payment_id",
        "certificate_id",
    }

    def _content_key(value):
        if isinstance(value, dict):
            stripped = {k: v for k, v in value.items() if k not in _ID_FIELDS}
            return json.dumps(stripped, sort_keys=True, default=str)
        return json.dumps(value, sort_keys=True, default=str)

    rename_pred: dict[str, str] = {}
    rename_gold: dict[str, str] = {}
    counter = 0

    for table_name in sorted(set(pred_state.keys()) | set(gold_state.keys())):
        pred_table = pred_state.get(table_name)
        gold_table = gold_state.get(table_name)
        if not isinstance(pred_table, dict) or not isinstance(gold_table, dict):
            continue
        pred_only = sorted(set(pred_table.keys()) - set(gold_table.keys()))
        gold_only = sorted(set(gold_table.keys()) - set(pred_table.keys()))
        if not pred_only and not gold_only:
            continue

        pred_only.sort(key=lambda k: _content_key(pred_table[k]))
        gold_only.sort(key=lambda k: _content_key(gold_table[k]))

        n_paired = min(len(pred_only), len(gold_only))
        for i in range(n_paired):
            canon = f"__NEW_{table_name.upper()}_{counter}__"
            rename_pred[pred_only[i]] = canon
            rename_gold[gold_only[i]] = canon
            counter += 1
        for k in pred_only[n_paired:]:
            rename_pred[k] = f"__UNPAIRED_PRED_{table_name.upper()}_{counter}__"
            counter += 1
        for k in gold_only[n_paired:]:
            rename_gold[k] = f"__UNPAIRED_GOLD_{table_name.upper()}_{counter}__"
            counter += 1

    if not rename_pred and not rename_gold:
        return pred_state, gold_state

    def _rewrite(obj, mp):
        if isinstance(obj, dict):
            return {
                mp.get(k, k) if isinstance(k, str) else k: _rewrite(v, mp)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_rewrite(x, mp) for x in obj]
        if isinstance(obj, str):
            return mp.get(obj, obj)
        return obj

    return _rewrite(pred_state, rename_pred), _rewrite(gold_state, rename_gold)


def get_dict_hash_normalized(obj: dict) -> str:
    """Hash a dict after applying :func:`normalize_for_compare`.

    Use this when you want byte-equality of two dicts to imply
    semantic equivalence in the order-insensitive sense — typically
    when comparing two DB end-states produced by different toolkits
    that may differ in conventions (sorting, etc.) but not meaning.
    """
    return get_dict_hash(normalize_for_compare(obj))


def show_dict_diff(dict1: dict, dict2: dict) -> str:
    """
    Show the difference between two dictionaries.
    """
    diff = DeepDiff(dict1, dict2)
    return diff


def get_now(use_compact_format: bool = False) -> str:
    """
    Returns the current date and time.

    Args:
        use_compact_format: If True, returns format YYYYMMDD_HHMMSS.
                          If False, returns ISO format (YYYY-MM-DDTHH:MM:SS.ffffff).
    """
    now = datetime.now()
    return format_time(now, use_compact_format=use_compact_format)


def format_time(time: datetime, use_compact_format: bool = True) -> str:
    """
    Format the time.

    Args:
        time: The datetime object to format.
        use_compact_format: If True, returns format YYYYMMDD_HHMMSS.
                          If False, returns ISO format (YYYY-MM-DDTHH:MM:SS.ffffff).
    """
    if use_compact_format:
        return time.strftime("%Y%m%d_%H%M%S")
    else:
        return time.isoformat()


def get_tau2_version() -> str:
    """Get the installed tau2 package version."""
    try:
        return importlib.metadata.version("tau2")
    except importlib.metadata.PackageNotFoundError:
        return "dev"


def get_commit_hash() -> str:
    """
    Get the commit hash of the current directory.
    """
    try:
        # timeout guards against a hung gitdir (e.g. virtiofs); TimeoutExpired
        # is an Exception, so the except below returns "unknown" as usual.
        commit_hash = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=5)
            .strip()
            .split("\n")[0]
        )
    except Exception as e:
        logger.error(f"Failed to get git hash: {e}")
        commit_hash = "unknown"
    return commit_hash
