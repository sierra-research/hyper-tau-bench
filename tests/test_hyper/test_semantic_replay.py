"""Trusted canonical replay tests for host-backed Client API trajectories."""

import pytest

from tau2.data_model.message import (
    AssistantMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.environment.db import DB
from tau2.environment.environment import Environment
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool
from tau2.hyper.client_api.runtime import ClientAPIRuntime
from tau2.hyper.sandbox.sealed_runner import (
    SealedCandidateEnvironment,
    SealedRunnerConfig,
)


class _ReplayDB(DB):
    events: list[str] = []


class _CanonicalTools(ToolKitBase):
    def __init__(self, db):
        super().__init__(db)
        self.observed = False

    @is_tool(ToolType.READ)
    def observe(self) -> str:
        self.observed = True
        return "observed"

    @is_tool(ToolType.WRITE)
    def record_event(self, label: str) -> str:
        if not self.observed:
            raise RuntimeError("observe must run before record_event")
        self.db.events.append(label)
        return label


class _UserTools(ToolKitBase):
    @is_tool(ToolType.WRITE)
    def record_user_event(self, label: str) -> str:
        self.db.events.append(label)
        return label


class _Runner:
    def __init__(self):
        self.calls = []

    def request(self, method, payload=None):
        self.calls.append((method, payload or {}))
        if method == "tool_call":
            return "outer tool executed"
        if method == "snapshot":
            return {}
        return {"ok": True}


def _metadata():
    schema = {
        "type": "function",
        "function": {
            "name": "developer_wrapper",
            "description": "A deliberately non-reproducible outer wrapper.",
            "parameters": {"type": "object", "properties": {}},
        },
    }
    return {
        "domain": "tiny",
        "policy": "",
        "tools": {
            "developer_wrapper": {
                "schema": schema,
                "return_schema": {"type": "string"},
                "info": {"tool_type": "read"},
                "mutates_state": False,
            }
        },
    }


def _config(tmp_path, *, mock=None):
    return SealedRunnerConfig(
        kit_path=tmp_path,
        image="tau2-construction-runtime:contract-v7",
        domain="tiny",
        client_api_mode="rest",
        client_api_mock=mock,
    )


def _runtime():
    db = _ReplayDB()
    environment = Environment(
        domain_name="tiny",
        policy="",
        tools=_CanonicalTools(db),
        user_tools=_UserTools(db),
    )
    return ClientAPIRuntime(environment)


def _outer_exchange(call_id, semantic_calls):
    return [
        AssistantMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id=call_id,
                    name="developer_wrapper",
                    arguments={},
                    requestor="assistant",
                )
            ],
        ),
        ToolMessage(
            id=call_id,
            role="tool",
            content="recorded outer response that cannot be reproduced",
            semantic_tool_calls=semantic_calls,
        ),
    ]


def _semantic(outer_id, index, name, arguments=None):
    return ToolCall(
        id=f"{outer_id}:client-api:{index}",
        name=name,
        arguments=arguments or {},
        requestor="assistant",
    )


def test_host_backed_replay_uses_semantics_and_preserves_user_order(tmp_path):
    runner = _Runner()
    runtime = _runtime()
    environment = SealedCandidateEnvironment(
        _config(tmp_path),
        metadata=_metadata(),
        runner=runner,
        client_api_runtime=runtime,
    )
    history = [
        *_outer_exchange(
            "outer-1",
            [
                _semantic("outer-1", 0, "observe"),
                _semantic("outer-1", 1, "record_event", {"label": "first"}),
            ],
        ),
        UserMessage(
            role="user",
            tool_calls=[
                ToolCall(
                    id="user-1",
                    name="record_user_event",
                    arguments={"label": "user"},
                    requestor="user",
                )
            ],
        ),
        ToolMessage(
            id="user-1",
            role="tool",
            content="user",
            requestor="user",
        ),
        *_outer_exchange(
            "outer-2",
            [_semantic("outer-2", 0, "record_event", {"label": "second"})],
        ),
    ]

    environment.set_state(None, None, history)

    assert runtime.snapshot()["events"] == ["first", "user", "second"]
    assert [call.operation_id for call in runtime.operation_calls] == [
        "observe",
        "record_event",
        "record_event",
    ]
    assert not [call for call in runner.calls if call[0] == "tool_call"]


def test_user_tool_responses_never_record_semantic_traces(tmp_path):
    # Regression (2026-08-30): live recording attached an empty trace list
    # to EVERY tool response while the Client runtime was active — including
    # user tools (telecom device tools). Replay then failed the whole
    # conversation with "must belong to assistant calls", zeroing every
    # telecom eval task whose user sim touched a tool.
    runner = _Runner()
    runtime = _runtime()
    environment = SealedCandidateEnvironment(
        _config(tmp_path),
        metadata=_metadata(),
        runner=runner,
        client_api_runtime=runtime,
    )
    response = environment.get_response(
        ToolCall(
            id="user-1",
            name="record_user_event",
            arguments={"label": "user"},
            requestor="user",
        )
    )
    assert response.semantic_tool_calls is None


def test_user_tool_with_recorded_empty_trace_replays_normally(tmp_path):
    # Histories recorded before the get_response requestor guard carry
    # semantic_tool_calls=[] on user-tool responses; replay must fall back
    # to the normal path instead of raising.
    runner = _Runner()
    runtime = _runtime()
    environment = SealedCandidateEnvironment(
        _config(tmp_path),
        metadata=_metadata(),
        runner=runner,
        client_api_runtime=runtime,
    )
    history = [
        UserMessage(
            role="user",
            tool_calls=[
                ToolCall(
                    id="user-1",
                    name="record_user_event",
                    arguments={"label": "user"},
                    requestor="user",
                )
            ],
        ),
        ToolMessage(
            id="user-1",
            role="tool",
            content="user",
            requestor="user",
            semantic_tool_calls=[],
        ),
    ]

    environment.set_state(None, None, history)

    assert runtime.snapshot()["events"] == ["user"]


def test_user_tool_with_nonempty_trace_still_fails_closed(tmp_path):
    environment = SealedCandidateEnvironment(
        _config(tmp_path),
        metadata=_metadata(),
        runner=_Runner(),
        client_api_runtime=_runtime(),
    )
    history = [
        UserMessage(
            role="user",
            tool_calls=[
                ToolCall(
                    id="user-1",
                    name="record_user_event",
                    arguments={"label": "user"},
                    requestor="user",
                )
            ],
        ),
        ToolMessage(
            id="user-1",
            role="tool",
            content="user",
            requestor="user",
            semantic_tool_calls=[_semantic("user-1", 0, "record_event")],
        ),
    ]

    with pytest.raises(ValueError, match="must belong to assistant calls"):
        environment.set_state(None, None, history)


def test_trusted_empty_trace_replays_as_noop(tmp_path):
    runner = _Runner()
    runtime = _runtime()
    environment = SealedCandidateEnvironment(
        _config(tmp_path),
        metadata=_metadata(),
        runner=runner,
        client_api_runtime=runtime,
    )
    environment.set_state(None, None, _outer_exchange("outer-1", []))

    assert not [call for call in runner.calls if call[0] == "tool_call"]
    assert runtime.operation_calls == ()


def test_legacy_trace_without_semantic_annotation_reexecutes_outer_tool(tmp_path):
    runner = _Runner()
    runtime = _runtime()
    environment = SealedCandidateEnvironment(
        _config(tmp_path),
        metadata=_metadata(),
        runner=runner,
        client_api_runtime=runtime,
    )
    history = _outer_exchange("outer-1", [])
    history[1] = history[1].model_copy(update={"semantic_tool_calls": None})

    environment.set_state(None, None, history)

    assert len([call for call in runner.calls if call[0] == "tool_call"]) == 1
    assert runtime.operation_calls == ()


def test_developer_owned_mock_never_trusts_semantic_annotations(tmp_path):
    runner = _Runner()
    environment = SealedCandidateEnvironment(
        _config(
            tmp_path,
            mock={"module": "workspace/mock_client_api.py", "config": {}},
        ),
        metadata=_metadata(),
        runner=runner,
    )

    environment.set_state(
        None,
        None,
        _outer_exchange(
            "outer-1",
            [_semantic("outer-1", 0, "candidate_authored_private_call")],
        ),
    )

    assert len([call for call in runner.calls if call[0] == "tool_call"]) == 1


@pytest.mark.parametrize(
    ("semantic_call", "message"),
    [
        (
            ToolCall(
                id="unattributed",
                name="observe",
                arguments={},
                requestor="assistant",
            ),
            "not attributed",
        ),
        (
            _semantic("outer-1", 0, "missing_canonical_operation"),
            "missing_canonical_operation",
        ),
    ],
)
def test_invalid_trusted_semantic_trace_fails_closed(tmp_path, semantic_call, message):
    environment = SealedCandidateEnvironment(
        _config(tmp_path),
        metadata=_metadata(),
        runner=_Runner(),
        client_api_runtime=_runtime(),
    )

    with pytest.raises(ValueError, match=message):
        environment.set_state(
            None,
            None,
            _outer_exchange("outer-1", [semantic_call]),
        )


@pytest.mark.parametrize("domain", ["airline_plus", "retail_plus", "telecom"])
def test_semantic_replay_preserves_conversation_transfer_runtime_state(domain):
    from tau2.hyper.client_api.runtime import create_domain_client_api_runtime

    live = create_domain_client_api_runtime(domain, conversation_id="conv_live")
    accepted = live.request(
        method="POST",
        path="/v1/conversations/conv_live/transfers",
        body={"summary": "Customer requested a person"},
    )
    operation = live.operation_calls[0]
    replay = create_domain_client_api_runtime(domain, conversation_id="conv_replay")

    replay.replay_operation(
        ToolCall(
            id="outer-1:client-api:0",
            name=operation.operation_id,
            arguments=operation.arguments,
            requestor="assistant",
        )
    )

    assert replay.conversation_transfer is not None
    assert replay.conversation_transfer.model_dump() == accepted.body
    assert replay.operation_calls == (operation,)
