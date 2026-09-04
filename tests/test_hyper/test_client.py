"""
Tests for the Hyper-τ ClientSimulator.

Unit tests that don't require LLM calls test initialization and state.
Integration tests that require API keys are gated with markers.
"""

import os

import pytest

from tau2.hyper.client import ClientSimulator
from tau2.hyper.data_model import ClientState

# Gate LLM-dependent tests
requires_api_key = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)

SAMPLE_INSTRUCTIONS = """\
You are a business stakeholder who wants the developer to build a \
customer service agent. You care about refund policies.

Rules:
- Refunds are only allowed within 30 days of purchase.
- Premium members get priority support.
- Be cooperative and answer questions directly.
"""


class TestClientSimulatorInit:
    """Tests for ClientSimulator initialization (no LLM calls)."""

    def test_init(self):
        client = ClientSimulator(
            llm="gpt-4.1-mini",
            client_instructions=SAMPLE_INSTRUCTIONS,
        )
        assert client.llm == "gpt-4.1-mini"
        assert client.client_instructions == SAMPLE_INSTRUCTIONS

    def test_system_prompt_is_client_instructions(self):
        """system_prompt should be exactly client_instructions."""
        client = ClientSimulator(
            llm="gpt-4.1-mini",
            client_instructions=SAMPLE_INSTRUCTIONS,
        )
        assert client.system_prompt == SAMPLE_INSTRUCTIONS

    def test_get_init_state(self):
        client = ClientSimulator(
            llm="gpt-4.1-mini",
            client_instructions=SAMPLE_INSTRUCTIONS,
        )
        state = client.get_init_state()
        assert isinstance(state, ClientState)
        assert len(state.system_messages) == 1
        assert state.system_messages[0].content == SAMPLE_INSTRUCTIONS
        assert len(state.messages) == 0

    def test_llm_args_passed_through(self):
        client = ClientSimulator(
            llm="gpt-4.1-mini",
            client_instructions=SAMPLE_INSTRUCTIONS,
            llm_args={"temperature": 0.5},
        )
        assert client.llm_args == {"temperature": 0.5}


@requires_api_key
class TestClientSimulatorLLM:
    """Integration tests that require an LLM API key."""

    def test_generate_initial_brief(self):
        """Test that the Client LLM generates an opening message."""
        client = ClientSimulator(
            llm="gpt-4.1-mini",
            client_instructions=SAMPLE_INSTRUCTIONS,
            llm_args={"temperature": 0.0},
        )
        brief_msg, state = client.generate_initial_brief()

        # Brief should be a UserMessage (from Developer's perspective)
        assert brief_msg.role == "user"
        assert len(brief_msg.content) > 10
        # State should have 1 message (the brief as assistant)
        assert len(state.messages) == 1

    def test_generate_response_basic(self):
        """Test that the Client can respond to a simple question."""
        client = ClientSimulator(
            llm="gpt-4.1-mini",
            client_instructions=SAMPLE_INSTRUCTIONS,
            llm_args={"temperature": 0.0},
        )
        state = client.get_init_state()

        response, state = client.generate_response(
            developer_message="What is the refund policy?",
            state=state,
        )

        assert response
        assert len(response) > 10
        # State should have 2 messages (developer question + client response)
        assert len(state.messages) == 2

    def test_multi_turn_conversation(self):
        """Test that state persists across turns."""
        client = ClientSimulator(
            llm="gpt-4.1-mini",
            client_instructions=SAMPLE_INSTRUCTIONS,
            llm_args={"temperature": 0.0},
        )
        state = client.get_init_state()

        # Turn 1
        response1, state = client.generate_response(
            developer_message="What is the refund policy?",
            state=state,
        )
        assert len(state.messages) == 2

        # Turn 2
        response2, state = client.generate_response(
            developer_message="Are there any exceptions for premium members?",
            state=state,
        )
        assert len(state.messages) == 4
        assert response2
