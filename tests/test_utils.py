import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_data_dir_environment_variable():
    """Test that DATA_DIR can be set via environment variable."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_data_dir = Path(temp_dir) / "custom_data"
        temp_data_dir.mkdir()

        with patch.dict(os.environ, {"TAU2_DATA_DIR": str(temp_data_dir)}):
            # Re-import to get the new DATA_DIR value
            import importlib

            import tau2.utils.utils

            importlib.reload(tau2.utils.utils)

            assert tau2.utils.utils.DATA_DIR == temp_data_dir


def test_data_dir_fallback_to_source():
    """Test that DATA_DIR falls back to source directory when env var is not set."""
    # Clear environment variable
    with patch.dict(os.environ, {}, clear=True):
        # Re-import to get the fallback DATA_DIR value
        import importlib

        import tau2.utils.utils

        importlib.reload(tau2.utils.utils)

        # Check that DATA_DIR points to the source directory
        # Calculate expected path from utils.py location
        utils_file = Path(tau2.utils.utils.__file__)
        expected_source_dir = utils_file.parents[3] / "data"
        assert tau2.utils.utils.DATA_DIR == expected_source_dir


def test_get_commit_hash_passes_timeout():
    """git rev-parse must run with a timeout so a hung gitdir can't block runs."""
    from tau2.utils.utils import get_commit_hash

    with patch("tau2.utils.utils.subprocess.check_output") as mock_check_output:
        mock_check_output.return_value = "abc123\n"
        assert get_commit_hash() == "abc123"
        assert mock_check_output.call_args.kwargs.get("timeout") == 5


def test_get_commit_hash_timeout_returns_unknown():
    """A TimeoutExpired from git rev-parse falls back to 'unknown'."""
    from tau2.utils.utils import get_commit_hash

    with patch(
        "tau2.utils.utils.subprocess.check_output",
        side_effect=subprocess.TimeoutExpired(cmd="git rev-parse HEAD", timeout=5),
    ):
        assert get_commit_hash() == "unknown"
