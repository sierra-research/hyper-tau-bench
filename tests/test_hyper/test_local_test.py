"""Tests for the host-side local simulation service."""

import json

import pytest

from tau2.environment.environment import Environment
from tau2.hyper.data_model import EvaluationResult
from tau2.hyper.sandbox.local_test import (
    LocalTestService,
    LocalTestWiring,
    SandboxToolError,
    _developer_test_scenario_id,
    _parse_local_client_api_scenario,
    _validate_mock_client_api_task,
)


def test_run_local_test_is_candidate_only(
    tmp_path,
    monkeypatch,
):
    kit_path = tmp_path
    workspace = kit_path / "workspace"
    workspace.mkdir()
    task_path = workspace / "my_test.json"
    task_path.write_text(
        json.dumps(
            {
                "id": "custom_ref_test",
                "user_scenario": {"instructions": "The customer says hello."},
                "initial_state": {
                    "development_fixture": "airplane_mode",
                    "initialization_actions": [
                        {
                            "env_type": "assistant",
                            "func_name": "prepare_developer_case",
                            "arguments": {"case_id": "known-case"},
                        }
                    ],
                },
            }
        )
    )
    framework_dir = kit_path / "framework"
    framework_dir.mkdir()
    (framework_dir / "deployment_manifest.json").write_text(
        json.dumps(
            {
                "allowed_agent_models": [
                    {
                        "model": "gpt-5.5",
                        "constraints": {"reasoning_effort": "none"},
                    },
                    {
                        "model": "gpt-5.6",
                        "constraints": {"reasoning_effort": "xhigh"},
                    },
                ],
            }
        )
    )

    from tau2.hyper import _inner
    from tau2.hyper.sandbox.sealed_runner import (
        SealedCandidateEnvironment,
        create_sealed_candidate_agent,
    )

    captured = {}
    client_runtime_calls = []

    def fake_client_runtime_factory(domain, **kwargs):
        client_runtime_calls.append((domain, kwargs))
        return object()

    monkeypatch.setattr(
        "tau2.hyper.client_api.runtime.create_domain_client_api_runtime",
        fake_client_runtime_factory,
    )

    def fake_template(cls, config):
        del cls
        assert config.kit_path == kit_path.resolve()
        assert config.domain == "telecom"
        assert config.client_api_mode == "rest"
        config.client_api_factory(solo_mode=False)
        return Environment(domain_name="telecom", policy="test policy")

    def fake_run_inner_simulation(**kwargs):
        captured.update(kwargs)
        return EvaluationResult(
            task_id=kwargs["task"].id,
            reward=1.0,
            reward_breakdown={"DB": 1.0},
            messages=[],
            client_api_defect_report={
                "events": [{"defect_id": "private-hidden-defect"}],
                "verification": {"status": "passed", "violations": []},
            },
        )

    monkeypatch.setattr(
        SealedCandidateEnvironment,
        "template",
        classmethod(fake_template),
    )
    monkeypatch.setattr(_inner, "run_inner_simulation", fake_run_inner_simulation)

    host_defect_profile = object()
    toolkit = LocalTestService(
        kit_path,
        local_test_wiring=LocalTestWiring(
            domain="telecom",
            user_llm="gpt-5.5",
            user_llm_args={"reasoning_effort": "none"},
            client_api_mode="rest",
            client_api_defect_profile=host_defect_profile,
        ),
    )
    output = toolkit.run_local_test(
        "workspace/my_test.json", verbose=True, max_steps=17
    )

    assert captured["domain"] == "telecom"
    assert captured["policy"] == "test policy"
    assert captured["agent_llm"] == "gpt-5.5"
    assert captured["agent_llm_args"] == {"reasoning_effort": "none"}
    assert captured["allowed_agent_models"][1] == {
        "model": "gpt-5.6",
        "constraints": {"reasoning_effort": "xhigh"},
    }
    assert captured["user_llm"] == "gpt-5.5"
    assert captured["user_llm_args"] == {"reasoning_effort": "none"}
    assert captured["max_steps"] == 17
    assert captured["agent_factory"] is create_sealed_candidate_agent
    assert captured["custom_environment"].domain_name == "telecom"
    assert captured["use_reference_gold_environment"] is False
    assert captured["task"].initial_state.initialization_actions is None
    assert captured["task"].initial_state.development_fixture is None
    assert [action.model_dump() for action in captured["developer_setup_actions"]] == [
        {
            "env_type": "assistant",
            "func_name": "prepare_developer_case",
            "arguments": {"case_id": "known-case"},
        }
    ]
    assert captured["development_fixture"] == "airplane_mode"
    assert captured["client_api_execution_mode"] == "developer_test"
    scenario_id = captured["client_api_developer_test_scenario_id"]
    assert len(scenario_id) == 64
    assert scenario_id != captured["task"].id
    from tau2.data_model.tasks import Task

    authored_task = Task.model_validate(json.loads(task_path.read_text()))
    assert scenario_id == _developer_test_scenario_id(authored_task)
    artifact = next((kit_path / "simulations").glob("local_run_*.json"))
    artifact_payload = json.loads(artifact.read_text())
    assert "client_api_defect_report" not in artifact_payload["records"][0]["result"]
    assert "private-hidden-defect" not in artifact.read_text()
    assert client_runtime_calls == [
        (
            "telecom",
            {
                "solo_mode": False,
                "development_seed": True,
                "defect_profile": host_defect_profile,
            },
        )
    ]
    assert "Assistant implementation: Developer submission" in output
    assert "Client API: sandbox implementation of client_api/openapi.yaml" in output
    assert "Customer/user runtime" in output
    assert "Scenarios: Developer-authored (1)" in output
    assert "canonical" not in output.lower()
    # The source-domain name is runtime wiring the Developer never sees.
    assert "telecom" not in output
    assert "custom_ref_test" in output
    assert "1/1 passed" in output
    assert "Saved artifact: simulations/local_run_" in output

    artifacts = sorted((kit_path / "simulations").glob("local_run_*.json"))
    assert len(artifacts) == 1
    artifact = json.loads(artifacts[0].read_text())
    assert "domain" not in artifact
    assert "user_llm" not in artifact
    assert "user_llm_args" not in artifact
    assert "agent_llm" not in artifact
    assert "agent_llm_args" not in artifact
    assert artifact["allowed_agent_models"][0] == {
        "model": "gpt-5.5",
        "constraints": {"reasoning_effort": "none"},
    }
    assert artifact["max_steps"] == 17
    assert artifact["task_paths"] == ["workspace/my_test.json"]
    assert artifact["summary"] == {
        "total": 1,
        "valid": 1,
        "errors": 0,
        "passed": 1,
        "avg_reward": 1.0,
    }
    assert artifact["records"][0]["task_id"] == "custom_ref_test"
    assert artifact["records"][0]["status"] == "pass"


def test_local_run_artifact_seals_message_metadata(tmp_path, monkeypatch):
    """Local-run artifacts are sandbox-readable, so persisted messages must
    pass the developer-visible allowlist: litellm's ``raw_data`` echoes the
    request back, including the user simulator's system prompt."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "seal_test.json").write_text(
        json.dumps(
            {
                "id": "seal_test",
                "user_scenario": {"instructions": "The customer says hello."},
            }
        )
    )
    (tmp_path / "framework").mkdir()
    (tmp_path / "framework" / "deployment_manifest.json").write_text(
        json.dumps(
            {
                "allowed_agent_models": [
                    {"model": "gpt-5.5", "constraints": {"reasoning_effort": "none"}}
                ],
            }
        )
    )

    from tau2.data_model.message import AssistantMessage, UserMessage
    from tau2.hyper import _inner
    from tau2.hyper.sandbox.sealed_runner import SealedCandidateEnvironment

    user_sim_prompt = (
        "# User Simulation Guidelines\nYou are playing the role of a customer."
    )

    def fake_template(cls, config):
        del cls
        return Environment(domain_name="telecom", policy="test policy")

    def fake_run_inner_simulation(**kwargs):
        return EvaluationResult(
            task_id=kwargs["task"].id,
            reward=1.0,
            reward_breakdown={"DB": 1.0},
            messages=[
                UserMessage(
                    role="user",
                    content="Hello, I need help.",
                    raw_data={"messages": [{"content": user_sim_prompt}]},
                    usage={"prompt_tokens": 12},
                    cost=0.01,
                ),
                AssistantMessage(
                    role="assistant",
                    content="Happy to help.",
                    raw_data={"messages": [{"content": "agent request echo"}]},
                ),
            ],
        )

    monkeypatch.setattr(
        SealedCandidateEnvironment, "template", classmethod(fake_template)
    )
    monkeypatch.setattr(_inner, "run_inner_simulation", fake_run_inner_simulation)

    toolkit = LocalTestService(
        tmp_path,
        local_test_wiring=LocalTestWiring(
            domain="telecom",
            user_llm="gpt-5.4",
            user_llm_args={"reasoning_effort": "none"},
        ),
    )
    toolkit.run_local_test("workspace/seal_test.json")

    artifact_path = next((tmp_path / "simulations").glob("local_run_*.json"))
    artifact_text = artifact_path.read_text()
    assert "raw_data" not in artifact_text
    assert "User Simulation Guidelines" not in artifact_text
    assert "request echo" not in artifact_text

    artifact = json.loads(artifact_text)
    sealed_messages = artifact["records"][0]["result"]["messages"]
    assert [message["role"] for message in sealed_messages] == ["user", "assistant"]
    assert sealed_messages[0]["content"] == "Hello, I need help."
    for message in sealed_messages:
        for banned in ("raw_data", "usage", "cost", "timestamp"):
            assert banned not in message


@pytest.mark.parametrize(
    "initial_state",
    [
        {"initialization_data": {"agent_data": {"private_table": {}}}},
        {"initialization_data": {"user_data": {"private_device": {}}}},
        {
            "initialization_actions": [
                {
                    "env_type": "user",
                    "func_name": "private_user_setup",
                    "arguments": {},
                }
            ]
        },
    ],
)
def test_run_local_test_rejects_private_rest_setup(
    tmp_path,
    monkeypatch,
    initial_state,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "private_setup.json").write_text(
        json.dumps(
            {
                "id": "private_setup",
                "user_scenario": {"instructions": "Test private setup."},
                "initial_state": initial_state,
            }
        )
    )
    (tmp_path / "framework").mkdir()
    (tmp_path / "framework" / "deployment_manifest.json").write_text(
        json.dumps(
            {
                "allowed_agent_models": [{"model": "gpt-5.5", "constraints": {}}],
            }
        )
    )

    from tau2.hyper import _inner
    from tau2.hyper.sandbox.sealed_runner import SealedCandidateEnvironment

    monkeypatch.setattr(
        SealedCandidateEnvironment,
        "template",
        classmethod(
            lambda cls, config: Environment(domain_name="telecom", policy="test policy")
        ),
    )
    monkeypatch.setattr(
        _inner,
        "run_inner_simulation",
        lambda **kwargs: pytest.fail("private setup reached the simulation runtime"),
    )

    output = LocalTestService(
        tmp_path,
        local_test_wiring=LocalTestWiring(
            domain="telecom", user_llm="gpt-5.5", client_api_mode="rest"
        ),
    ).run_local_test("workspace/private_setup.json")

    assert (
        "REST-mode Developer scenarios cannot initialize private Client state" in output
    )
    assert "private_table" not in output
    assert "private_device" not in output
    assert "private_user_setup" not in output


def test_local_client_api_scenario_modes_are_exclusive_and_workspace_scoped(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    mock_module = workspace / "mock_client_api.py"
    mock_module.write_text("def create_mock_client_api(config): return None\n")
    task_data = {
        "id": "mock_case",
        "client_api": {
            "mode": "mock",
            "module": "workspace/mock_client_api.py",
            "config": {"sequence": [200, 503]},
        },
    }

    cleaned, mode, mock = _parse_local_client_api_scenario(
        task_data,
        sandbox_root=tmp_path,
        rest_mode=True,
    )

    assert cleaned == {"id": "mock_case"}
    assert mode == "mock"
    assert mock == {
        "module": "workspace/mock_client_api.py",
        "config": {"sequence": [200, 503]},
    }
    assert task_data["client_api"]["mode"] == "mock"

    with pytest.raises(SandboxToolError, match="cannot include mock"):
        _parse_local_client_api_scenario(
            {"client_api": {"mode": "seeded", "config": {}}},
            sandbox_root=tmp_path,
            rest_mode=True,
        )
    with pytest.raises(SandboxToolError, match="inside workspace"):
        _parse_local_client_api_scenario(
            {"client_api": {"mode": "mock", "module": "../mock.py"}},
            sandbox_root=tmp_path,
            rest_mode=True,
        )


def test_mock_client_api_scenarios_reject_db_grading_and_seed_fixtures():
    from tau2.data_model.tasks import Task

    task = Task.model_validate(
        {
            "id": "mock_db_case",
            "user_scenario": {"instructions": "Test a mocked mutation."},
            "evaluation_criteria": {"reward_basis": ["DB"]},
        }
    )

    with pytest.raises(SandboxToolError, match="cannot use DB grading"):
        _validate_mock_client_api_task(task, None)

    transcript_task = task.model_copy(
        update={
            "evaluation_criteria": task.evaluation_criteria.model_copy(
                update={"reward_basis": []}
            )
        }
    )
    with pytest.raises(SandboxToolError, match="development_fixture"):
        _validate_mock_client_api_task(transcript_task, "airplane_mode")


@pytest.mark.parametrize(
    "report",
    [
        {
            "trace": [],
            "verification": {
                "status": "failed",
                "error": {"type": "AssertionError", "message": "missing call"},
            },
        },
        {
            "trace": [
                {
                    "request": {"path": "/v1/test"},
                    "error": {"type": "RuntimeError", "message": "boom"},
                }
            ],
            "verification": {"status": "not_configured"},
        },
    ],
)
def test_mock_client_api_report_failures_zero_local_reward(report):
    from tau2.hyper._inner import _apply_client_api_mock_report

    result = EvaluationResult(
        task_id="mock_failure",
        reward=1.0,
        reward_breakdown={"NL_ASSERTION": 1.0},
    )

    _apply_client_api_mock_report(result, report)

    assert result.reward == 0.0
    assert result.reward_breakdown == {
        "NL_ASSERTION": 1.0,
        "CLIENT_API_MOCK": 0.0,
    }
    assert result.client_api_mock_report == report


def test_run_local_test_uses_mock_backend_without_a_client_runtime(
    tmp_path, monkeypatch
):
    from tau2.hyper.runtime_contract import DEFAULT_CONSTRUCTION_RUNTIME_IMAGE

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "mock_client_api.py").write_text(
        "def create_mock_client_api(config): return lambda request: {}\n"
    )
    (workspace / "mock_scenario.json").write_text(
        json.dumps(
            {
                "id": "mock_scenario",
                "client_api": {
                    "mode": "mock",
                    "module": "workspace/mock_client_api.py",
                    "config": {"account": "acct_test"},
                },
                "user_scenario": {"instructions": "Test the mock."},
                "evaluation_criteria": {
                    "nl_assertions": ["The test completed."],
                    "reward_basis": ["NL_ASSERTION"],
                },
            }
        )
    )
    (tmp_path / "framework").mkdir()
    (tmp_path / "framework" / "deployment_manifest.json").write_text(
        json.dumps(
            {
                "allowed_agent_models": [{"model": "gpt-5.5", "constraints": {}}],
            }
        )
    )

    from tau2.hyper import _inner
    from tau2.hyper.sandbox.sealed_runner import SealedCandidateEnvironment

    metadata = {"domain": "telecom", "policy": "test policy", "tools": {}}
    captured = {}

    def fake_template(cls, config):
        return cls(config, metadata=metadata, runner=None)

    def fake_run_inner_simulation(**kwargs):
        captured.update(kwargs)
        assert kwargs["custom_environment"].client_api_runtime is None
        assert kwargs["custom_environment"].config.client_api_factory is None
        assert kwargs["custom_environment"].config.client_api_mock == {
            "module": "workspace/mock_client_api.py",
            "config": {"account": "acct_test"},
        }
        assert (
            kwargs["custom_environment"].config.image
            == DEFAULT_CONSTRUCTION_RUNTIME_IMAGE
        )
        return EvaluationResult(
            task_id=kwargs["task"].id,
            reward=1.0,
            messages=[],
            client_api_mock_report={
                "trace": [{"request": {"path": "/v1/test"}}],
                "verification": {"status": "passed"},
            },
        )

    monkeypatch.setattr(
        SealedCandidateEnvironment,
        "template",
        classmethod(fake_template),
    )
    monkeypatch.setattr(_inner, "run_inner_simulation", fake_run_inner_simulation)

    output = LocalTestService(
        tmp_path,
        local_test_wiring=LocalTestWiring(
            domain="telecom", user_llm="gpt-5.5", client_api_mode="rest"
        ),
    ).run_local_test("workspace/mock_scenario.json")

    assert captured["development_fixture"] is None
    assert "Client API mode: mock" in output
    artifact = json.loads(next((tmp_path / "simulations").glob("*.json")).read_text())
    assert artifact["records"][0]["client_api_mode"] == "mock"
    assert artifact["records"][0]["result"]["client_api_mock_report"]["trace"] == [
        {"request": {"path": "/v1/test"}}
    ]


def test_run_local_test_blocks_paths_outside_sandbox(tmp_path):
    toolkit = LocalTestService(
        tmp_path,
        local_test_wiring=LocalTestWiring(domain="telecom", user_llm="gpt-5.5"),
    )

    with pytest.raises(SandboxToolError, match="Path escapes sandbox"):
        toolkit.run_local_test("../outside.json")


def test_orchestrator_hands_phrasing_pack_to_builder_not_kit_config():
    """Grader phrasing assertions reach the local-test harness side only."""
    from tau2.hyper.harnesses.codex import CodexSandboxBuilder
    from tau2.hyper.response_phrasing import (
        load_selected_response_phrasing_rule_pack_for_task,
    )
    from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence"
        "_response_phrasing_performance_medium"
    )
    pack = load_selected_response_phrasing_rule_pack_for_task(task)
    assert pack is not None

    builder = CodexSandboxBuilder(llm="gpt-5.4")
    assert builder.response_phrasing_pack is None

    orchestrator = SandboxOrchestrator(task, builder)
    orchestrator._apply_sandbox_config_to_builder()

    assert builder.response_phrasing_pack is not None
    assert [
        assertion.id for assertion in builder.response_phrasing_pack.response_assertions
    ] == [assertion.id for assertion in pack.response_assertions]


def test_orchestrator_hands_defect_profile_to_builder_host_side(monkeypatch):
    """Deployment configuration reaches local tests without entering the kit."""
    from tau2.hyper.harnesses.codex import CodexSandboxBuilder
    from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "002_airline_plus_construction_core_evidence_seeded_performance_hard"
    )
    task = task.model_copy(
        update={
            "hyper": task.hyper.model_copy(
                update={"client_api_deployment_manifest": "airline_plus/all_defects_v1"}
            )
        }
    )
    profile = object()
    monkeypatch.setattr(
        "tau2.hyper.client_api.defects.load_defect_profile",
        lambda *args, **kwargs: profile,
    )
    builder = CodexSandboxBuilder(llm="gpt-5.4")

    SandboxOrchestrator(task, builder)._apply_sandbox_config_to_builder()

    assert builder.local_test_wiring is not None
    assert builder.local_test_wiring.client_api_defect_profile is profile
