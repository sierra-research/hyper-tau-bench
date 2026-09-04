"""Agent for the Rho-Bank banking_knowledge domain.

The runtime imports this file and calls ``create_agent()`` to build the
inner-loop agent. The design goal is that every single call to the model is
self-contained: it carries the operating policy, whatever knowledge-base and
case-precedent material is relevant to the current turn, a small set of
deterministic working notes, and the full conversation transcript so far, all
rendered into one message. An auditor can replay any one logged call and see
exactly what the model saw; nothing lives only in Python-process memory
between calls.

Knowledge retrieval is keyword-based and runs against the kit's own
``knowledge_base/`` and ``uploaded_materials/`` files through
``context.resources`` at call time, so it reflects whatever the deployed kit
actually ships (and degrades gracefully if a deployment prunes those
directories) rather than a snapshot baked in at authoring time.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from tau2.data_model.message import (
    AssistantMessage,
    UserMessage,
    ToolCall,
    ToolMessage,
    MultiToolMessage,
)
from tau2.hyper.agent_context import get_agent_context

from data_model import WorkingNotes


# ---------------------------------------------------------------------------
# Policy text embedded into every model call.
# ---------------------------------------------------------------------------

AGENT_PREAMBLE = """\
You are the Rho-Bank customer service agent. You act inside an automated
system: the customer never sees anything except your final reply text, and
any tool calls you make are executed by the environment and their results
are given back to you before your next turn. You must decide, on every
turn, whether to (a) send the customer a text reply, or (b) call one or
more tools to gather information or take an action. Never do both in the
same turn."""

POLICY_TEXT = """\
## Operating policy (Rho-Bank customer service handbook, condensed)

General conduct
- Be polite and professional. Never invent policies, fees, eligibility
  rules, or available actions. If a procedure is not covered by the
  policy below, the retrieved knowledge-base/case material, or the
  available tools, say plainly that you cannot find that procedure.
- Before taking any action that modifies the customer's accounts or
  records (opening/closing accounts, transfers, payments, card actions,
  disputes, limit changes, etc.), describe what you are about to do and
  get an explicit "yes" from the customer before calling the tool.
- Never ask the customer for documentation, receipts, or other materials
  unless a retrieved procedure explicitly says you may.
- Use the get_current_time tool for the current date/time whenever a
  procedure is date-sensitive. Never assume or guess the date.

Identity verification
- Before reading, modifying, or acting on any account-specific
  information, verify the customer's identity. Ask for any two of: date
  of birth, email address, phone number, home address. Both must match
  what is on file. Knowing the customer's name or user ID alone is never
  sufficient.
- Do not disclose any account information before verification succeeds.
- If the customer does not know their user ID, use search_customers with
  one identifying detail (name, email, phone, or address) to locate a
  candidate profile, then verify the two factors against that profile.
  If the details match multiple profiles or no profile, ask for another
  factor, or escalate per the transfer rules below if that fails.
- Once verified, the customer does not need to re-verify later in the
  same conversation.

Scope
- You may help with: personal and business bank accounts (checking and
  savings) - opening, closing, transfers, deposits, statement questions;
  credit cards - applications, activations, payments, limit changes,
  closures, replacements; debit cards - activations, PIN changes,
  freezes/unfreezes, replacements, recurring-transaction blocks; disputes
  and rewards - credit/debit disputes, cash-back disputes, dispute
  history; referrals and applications - referral tracking, credit-card
  applications, credit-limit-increase requests.
- Anything outside that scope, or outside what a retrieved procedure
  actually documents, is out of scope. Decline it and offer a human
  transfer.
- Some customer actions (for example, capturing and submitting a mobile
  check deposit) must be completed by the customer in their own banking
  app, not by you. When a retrieved procedure says so, use
  enable_customer_self_service_action and walk the customer through the
  app steps; do not perform that action yourself.

Escalation / human transfer
- Offer a transfer only after you have tried to help and confirmed there
  is genuinely no procedure covering the request, or when a retrieved
  procedure explicitly directs a transfer (for example: attorney or
  power-of-attorney inquiries, complex billing disputes needing
  specialist review, bank-initiated fraud alerts, a customer who
  persists after being told an offer or promotion does not exist).
- If the customer explicitly asks for a human, first try to help with
  the underlying issue. If they ask for a human four times in the same
  conversation, transfer them regardless of whether you think you could
  still help.
- When you transfer, first call the transfer_to_human_agent tool with a
  short internal summary of the issue. Only after that tool call
  succeeds do you send the customer a text reply, and that reply must be
  exactly: "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
  Do not send that sentence in the same turn as the tool call itself.

Using retrieved material
- Sections below under "Relevant internal knowledge-base procedures" and
  "Relevant approved case precedent" are internal reference material.
  Use them to determine the correct rule, fee, eligibility check, or API
  operation for the customer's request. Never read document titles, tool
  names, or raw internal notes aloud to the customer; translate them into
  plain, helpful language.
- If nothing retrieved covers the request and you are not confident a
  procedure exists, say so honestly instead of guessing, and offer a
  transfer."""

FINAL_INSTRUCTION = """\
## What to produce now

Decide the single next step in this conversation:
- If you need information or need to take an action, call the necessary
  tool(s) now and send no text.
- Otherwise, send the customer a concise, professional text reply and
  make no tool calls.
Follow the operating policy above exactly, including the verification,
confirmation, scope, and transfer rules. Do not fabricate account data,
fees, or eligibility outcomes; rely on tool calls and the retrieved
material above for anything account-specific."""


# ---------------------------------------------------------------------------
# Lightweight keyword retrieval over knowledge_base/ and uploaded_materials/
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "your", "with",
    "have", "this", "that", "from", "was", "were", "will", "can", "how",
    "what", "when", "where", "why", "who", "does", "did", "about",
    "into", "just", "also", "its", "them", "they", "their", "there",
    "then", "than", "been", "being", "would", "could", "should",
    "please", "thanks", "thank", "hello", "customer", "agent", "console",
    "support", "yes", "okay", "sure", "hey", "hi",
}


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
    return [w for w in words if w not in _STOPWORDS]


def _score_doc(terms: List[str], title: str, text: str) -> int:
    if not terms:
        return 0
    title_lower = title.lower()
    text_lower = text.lower()
    score = 0
    for term in set(terms):
        score += title_lower.count(term) * 5
        score += text_lower.count(term)
    return score


def _extract_excerpt(text: str, terms: List[str], window: int = 900) -> str:
    lower = text.lower()
    pos = -1
    for term in terms:
        idx = lower.find(term)
        if idx != -1:
            pos = idx
            break
    if pos == -1:
        excerpt = text[: window * 2]
    else:
        start = max(0, pos - window)
        end = min(len(text), pos + window)
        excerpt = text[start:end]
    return excerpt.strip()


class DocIndex:
    """Keyword search over the kit's knowledge_base/ and uploaded_materials/
    files, loaded lazily through ``context.resources`` and cached for the
    life of one conversation."""

    def __init__(self, context: Any):
        self._context = context
        self._docs: Optional[List[Dict[str, str]]] = None

    def _ensure_loaded(self) -> None:
        if self._docs is not None:
            return
        docs: List[Dict[str, str]] = []
        try:
            files = self._context.resources.files
        except Exception:
            files = ()
        for relpath in files:
            if not (
                relpath.startswith("knowledge_base/")
                or relpath.startswith("uploaded_materials/")
            ):
                continue
            try:
                raw = self._context.resources.read_text(relpath)
            except Exception:
                continue
            title = relpath.rsplit("/", 1)[-1]
            text = raw
            if relpath.startswith("knowledge_base/") and relpath.endswith(".json"):
                try:
                    parsed = json.loads(raw)
                    title = parsed.get("title", title)
                    text = parsed.get("content", raw)
                except Exception:
                    pass
            docs.append({"title": title, "source": relpath, "text": text})
        self._docs = docs

    def search(
        self, prefix: str, query: str, top_k: int = 3, max_chars: int = 1600
    ) -> List[Dict[str, str]]:
        self._ensure_loaded()
        terms = _tokenize(query)
        if not terms or not self._docs:
            return []
        scored: List[Tuple[int, Dict[str, str]]] = []
        for doc in self._docs:
            if not doc["source"].startswith(prefix):
                continue
            score = _score_doc(terms, doc["title"], doc["text"])
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda pair: -pair[0])
        results = []
        for _, doc in scored[:top_k]:
            excerpt = _extract_excerpt(doc["text"], terms, window=max_chars // 2)
            if len(excerpt) > max_chars:
                excerpt = excerpt[:max_chars] + " …[truncated]"
            results.append({"title": doc["title"], "source": doc["source"], "excerpt": excerpt})
        return results


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

_MODEL_PRIORITY = [
    "anthropic/claude-haiku-4-5",
    "google/gemini-3-flash-preview",
    "qwen/qwen3.8-27b",
    "google/gemma-4-31b-it",
    "gpt-5.6-luna",
    "moonshotai/kimi-k2.6",
    "gpt-5.6-terra",
    "anthropic/claude-sonnet-5",
]


def _model_attr(entry: Any, *names: str) -> Any:
    for name in names:
        if isinstance(entry, dict):
            if name in entry and entry[name] is not None:
                return entry[name]
        else:
            value = getattr(entry, name, None)
            if value is not None:
                return value
    return None


def _select_model(context: Any) -> Tuple[str, Dict[str, Any]]:
    """Pick an allowed model and build the constrained keyword arguments
    ``generate`` needs to resolve exactly one configuration. Choice
    constraints (``{"one_of": [...]}``) have no default, so we must supply
    a value for each; pinned constraints are filled in automatically by the
    gateway and are left alone here."""
    models = list(context.model_gateway.models)
    if not models:
        raise RuntimeError("No models are available from the model gateway.")
    by_name: Dict[str, Any] = {}
    for entry in models:
        name = _model_attr(entry, "model")
        if name and name not in by_name:
            by_name[name] = entry
    chosen = None
    for name in _MODEL_PRIORITY:
        if name in by_name:
            chosen = by_name[name]
            break
    if chosen is None:
        chosen = models[0]
    model_name = _model_attr(chosen, "model")
    constraints = _model_attr(chosen, "constraints") or {}
    call_kwargs: Dict[str, Any] = {}
    if isinstance(constraints, dict):
        for key, value in constraints.items():
            if isinstance(value, dict) and "one_of" in value:
                options = value.get("one_of") or []
                if not options:
                    continue
                preferred = None
                for candidate in ("low", "minimal", "fast", "small"):
                    if candidate in options:
                        preferred = candidate
                        break
                call_kwargs[key] = preferred if preferred is not None else options[0]
    return model_name, call_kwargs


# ---------------------------------------------------------------------------
# Transcript rendering
# ---------------------------------------------------------------------------

_HUMAN_REQUEST_RE = re.compile(
    r"(human agent|real person|live agent|actual person|human being|"
    r"speak (to|with) (a )?(person|human|agent|representative)|"
    r"talk (to|with) (a )?(person|human|agent|representative)|"
    r"transfer me|connect me to a person)",
    re.IGNORECASE,
)

MAX_TRANSCRIPT_CHARS = 12000


def _obj_attr(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return default


def _render_tool_call(tc: Any) -> str:
    name = _obj_attr(tc, "name", "tool_name", default="unknown_tool")
    args = _obj_attr(tc, "arguments", "args", default={})
    call_id = _obj_attr(tc, "id", "tool_call_id", default="")
    try:
        args_text = json.dumps(args, default=str)
    except Exception:
        args_text = str(args)
    return f"[agent called tool {call_id}] {name}({args_text})"


def _render_tool_message(tm: Any) -> str:
    call_id = _obj_attr(tm, "tool_call_id", "id", default="")
    name = _obj_attr(tm, "name", "tool_name", default="")
    content = _obj_attr(tm, "content", default="")
    label = f"{name} " if name else ""
    return f"[tool result {call_id}] {label}{content}"


def _render_message(msg: Any) -> List[str]:
    lines: List[str] = []
    if isinstance(msg, UserMessage):
        content = _obj_attr(msg, "content", default="") or ""
        lines.append(f"Customer: {content}")
    elif isinstance(msg, AssistantMessage):
        content = _obj_attr(msg, "content", default=None)
        if content:
            lines.append(f"Agent: {content}")
        tool_calls = _obj_attr(msg, "tool_calls", default=None)
        if tool_calls:
            for tc in tool_calls:
                lines.append(_render_tool_call(tc))
    elif isinstance(msg, MultiToolMessage):
        inner = _obj_attr(msg, "tool_messages", "messages", default=None)
        if inner:
            for tm in inner:
                lines.append(_render_tool_message(tm))
        else:
            try:
                for tm in msg:
                    lines.append(_render_tool_message(tm))
            except TypeError:
                lines.append(f"[tool results] {msg}")
    elif isinstance(msg, ToolMessage):
        lines.append(_render_tool_message(msg))
    else:
        lines.append(str(msg))
    return lines


def _trim_transcript(lines: List[str]) -> List[str]:
    total = sum(len(line) for line in lines)
    if total <= MAX_TRANSCRIPT_CHARS:
        return lines
    trimmed = list(lines)
    while trimmed and sum(len(line) for line in trimmed) > MAX_TRANSCRIPT_CHARS:
        trimmed.pop(0)
    return ["[earlier conversation history truncated for length]"] + trimmed


class ConversationState:
    """Opaque per-conversation state threaded through every turn."""

    def __init__(self) -> None:
        self.transcript: List[str] = []
        self.working_notes = WorkingNotes()


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class BankingKnowledgeAgent:
    def __init__(self, context: Any):
        self._context = context
        self._tools = context.action_interface.available
        self._model_name, self._call_kwargs = _select_model(context)
        self._doc_index = DocIndex(context)

    # -- required interface -------------------------------------------------

    def get_init_state(self, message_history: Optional[List[Any]] = None) -> ConversationState:
        state = ConversationState()
        if message_history:
            for msg in message_history:
                state.transcript.extend(_render_message(msg))
            state.transcript = _trim_transcript(state.transcript)
        return state

    def generate_next_message(
        self, message: Any, state: ConversationState
    ) -> Tuple[AssistantMessage, ConversationState]:
        if isinstance(message, UserMessage):
            content = _obj_attr(message, "content", default="") or ""
            if _HUMAN_REQUEST_RE.search(content):
                state.working_notes.human_transfer_request_count += 1

        state.transcript.extend(_render_message(message))
        state.transcript = _trim_transcript(state.transcript)

        query = " ".join(state.transcript[-8:])
        kb_hits = self._doc_index.search("knowledge_base/", query, top_k=3, max_chars=1500)
        case_hits = self._doc_index.search(
            "uploaded_materials/", query, top_k=3, max_chars=1500
        )

        prompt_text = self._build_prompt(state, kb_hits, case_hits)

        try:
            response = self._context.model_gateway.generate(
                model=self._model_name,
                messages=[UserMessage(role="user", content=prompt_text)],
                actions=self._tools,
                tool_choice="auto",
                **self._call_kwargs,
            )
        except Exception:
            response = AssistantMessage(
                role="assistant",
                content=(
                    "I'm having trouble processing that right now. Could you "
                    "please repeat your last message?"
                ),
            )

        tool_calls = _obj_attr(response, "tool_calls", default=None)
        if tool_calls:
            for tc in tool_calls:
                name = _obj_attr(tc, "name", "tool_name", default="")
                if name == "transfer_to_human_agent":
                    state.working_notes.transferred = True

        state.transcript.extend(_render_message(response))
        state.transcript = _trim_transcript(state.transcript)

        return response, state

    def is_stop(self, message: Any) -> bool:
        if not isinstance(message, AssistantMessage):
            return False
        content = _obj_attr(message, "content", default=None)
        return bool(content) and "TRANSFERRED TO A HUMAN AGENT" in content

    def stop(self) -> None:
        return None

    # -- internals ------------------------------------------------------

    def _build_prompt(
        self,
        state: ConversationState,
        kb_hits: List[Dict[str, str]],
        case_hits: List[Dict[str, str]],
    ) -> str:
        parts: List[str] = [AGENT_PREAMBLE, POLICY_TEXT]

        if kb_hits:
            section = ["## Relevant internal knowledge-base procedures"]
            for hit in kb_hits:
                section.append(f"### {hit['title']} ({hit['source']})\n{hit['excerpt']}")
            parts.append("\n\n".join(section))

        if case_hits:
            section = [
                "## Relevant approved case precedent "
                "(handling-standard reference only; do not quote verbatim to the customer)"
            ]
            for hit in case_hits:
                section.append(f"### {hit['title']} ({hit['source']})\n{hit['excerpt']}")
            parts.append("\n\n".join(section))

        parts.append("## Working notes\n" + state.working_notes.render())
        parts.append("## Conversation so far\n" + "\n".join(state.transcript))
        parts.append(FINAL_INSTRUCTION)

        return "\n\n".join(parts)


def create_agent() -> BankingKnowledgeAgent:
    """Build and return the agent evaluated by the runtime."""
    context = get_agent_context()
    return BankingKnowledgeAgent(context)
