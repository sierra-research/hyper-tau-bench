"""Shared data models for the Rho-Bank customer-service agent.

This agent does not read the shipped ``knowledge_base/`` directory at
runtime; the procedure corpus it works from is authored directly in the
agent's prompt (see ``agent.py``) as policy text distilled from the
handbook and the approved case files. This module defines the small amount of state the
agent threads between turns so that any single model call can be
reconstructed from that state plus the fixed policy text.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProcedureDoc(BaseModel):
    """A single self-contained knowledge-base procedure record.

    Mirrors the "one document per procedure" shape described in the
    handbook: eligibility rules, step-by-step instructions, fee amounts,
    and (when applicable) the exact REST operation a procedure unlocks.
    Not currently populated at runtime, but kept as a stable shape for any
    future structured-retrieval extension of the policy text.
    """

    doc_id: str
    category: str
    title: str
    keywords: List[str] = Field(default_factory=list)
    content: str
    api_operations: List[str] = Field(default_factory=list)
    requires_transfer: bool = False


class TranscriptEntry(BaseModel):
    """One entry in the agent's self-contained working transcript.

    ``role`` is one of "customer", "agent", or "tool". Tool entries record
    either the outgoing call (``tool_name``/``tool_args``) or the inbound
    result (``tool_result``), never both, so each entry can be replayed
    verbatim inside a single model call without consulting any other
    process state.
    """

    role: str
    text: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None


class VerificationState(BaseModel):
    """Identity-verification bookkeeping for the active conversation."""

    verified: bool = False
    matched_factors: List[str] = Field(default_factory=list)
    customer_id: Optional[str] = None
    profile_search_attempts: int = 0


class AgentState(BaseModel):
    """Opaque state threaded between agent turns.

    Everything the next model call needs beyond the live message list is
    captured here (the running transcript, verification status, transfer
    escalation counter, and any pending-confirmation note) so that the
    call producing the next assistant message can be reconstructed in
    isolation from this state plus the fixed policy text.
    """

    transcript: List[TranscriptEntry] = Field(default_factory=list)
    verification: VerificationState = Field(default_factory=VerificationState)
    human_transfer_request_count: int = 0
    pending_confirmation: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    ended: bool = False
