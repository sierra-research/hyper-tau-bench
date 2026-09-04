"""Tests for construction-mode evaluation plumbing."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage, UserMessage
from tau2.data_model.tasks import (
    Action,
    EnvAssertion,
    EvaluationCriteria,
    InitializationData,
    RewardType,
    Task,
)
from tau2.domains.telecom.environment import get_environment, get_tasks_small
from tau2.environment.db import DB
from tau2.environment.environment import Environment
from tau2.environment.toolkit import (
    ToolKitBase,
    ToolType,
    is_discoverable_tool,
    is_tool,
)
from tau2.evaluator.evaluator_env import EnvironmentEvaluator, _run_env_assertions
from tau2.hyper._inner import (
    _materialize_reference_setup,
    _resolve_inner_max_workers,
)


class SpeedDB(DB):
    """Tiny DB used to test assertion semantics."""

    speed_mbps: float = 0.0
    speed_desc: str = "failed"


class ExactSpeedTools(ToolKitBase):
    """Developer-style toolkit with brittle exact-match assertion semantics."""

    @is_tool(ToolType.WRITE)
    def set_speed(self, speed_mbps: float, speed_desc: str) -> dict:
        self.db.speed_mbps = speed_mbps
        self.db.speed_desc = speed_desc
        return {"speed_mbps": speed_mbps, "speed_desc": speed_desc}

    def assert_internet_speed(
        self, expected_speed: float, expected_desc: str | None = None
    ) -> bool:
        desc_ok = expected_desc is None or self.db.speed_desc == expected_desc
        return self.db.speed_mbps == expected_speed and desc_ok


class ThresholdSpeedTools(ToolKitBase):
    """Reference-style toolkit with threshold assertion semantics."""

    @is_tool(ToolType.WRITE)
    def set_speed(self, speed_mbps: float, speed_desc: str) -> str:
        self.db.speed_mbps = speed_mbps
        self.db.speed_desc = speed_desc
        return f"speed is {speed_mbps} Mbps ({speed_desc})"

    def assert_internet_speed(
        self, expected_speed: float, expected_desc: str | None = None
    ) -> bool:
        desc_ok = expected_desc is None or self.db.speed_desc == expected_desc
        return self.db.speed_mbps >= expected_speed and desc_ok


class GeneratedUserSpeedTools(ToolKitBase):
    """Generated-style user toolkit with a different public tool name."""

    @is_tool(ToolType.WRITE)
    def record_speed_result(self, speed_mbps: float, speed_desc: str) -> str:
        self.db.speed_mbps = speed_mbps
        self.db.speed_desc = speed_desc
        return "speed recorded"


class EmptyDB(DB):
    """Tiny DB for dispatcher edge-case tests."""


class ToolNameArgumentDB(DB):
    """DB with a field changed by a tool argument named ``tool_name``."""

    tool_name_value: str | None = None


class ToolNameArgumentTools(ToolKitBase):
    """Toolkit with a real tool argument named ``tool_name``."""

    @is_tool(ToolType.WRITE)
    def echo_tool_name(self, tool_name: str) -> dict:
        if hasattr(self.db, "tool_name_value"):
            self.db.tool_name_value = tool_name
        return {"tool_name": tool_name}


class AccountDB(DB):
    """Assistant-side DB used to verify separate DB initialization."""

    account_status: str = "active"


class PhoneDB(DB):
    """User-side DB used to verify separate DB initialization."""

    phone_status: str = "ready"


class AccountTools(ToolKitBase):
    """Assistant-side toolkit."""


class PhoneTools(ToolKitBase):
    """User-side toolkit."""


class GeneratedBill(BaseModel):
    """Generated DB record with an internal helper field."""

    bill_id: str
    status: str
    payment_request_sent: bool = False


class ReferenceBill(BaseModel):
    """Reference DB record without generated-only helper fields."""

    bill_id: str
    status: str


class GeneratedBillingDB(DB):
    """Generated assistant DB with a helper field on nested records."""

    bills: list[GeneratedBill]


class ReferenceBillingDB(DB):
    """Reference assistant DB with only public state."""

    bills: list[ReferenceBill]


class GeneratedOptionalTableDB(DB):
    """Generated DB that leaves an unused reference table as None."""

    task_config: dict | None = None
    status: str = "pending"


class ReferenceDefaultTableDB(DB):
    """Reference DB whose table defaults to an empty table shape."""

    task_config: dict = Field(default_factory=lambda: {"data": {}, "notes": ""})
    status: str = "pending"


class GeneratedRawAccount(BaseModel):
    """Generated typed row with aliases and optional generated-only fields."""

    model_config = ConfigDict(populate_by_name=True)

    account_id: str
    class_: str = Field(alias="class")
    parent_account_id: str | None = None
    generated_only: str | None = None


class GeneratedRawDispute(BaseModel):
    """Generated row that should preserve reference-visible explicit nulls."""

    dispute_id: str
    partial_refund_amount: float | None = None
    generated_only: str | None = None


class GeneratedRawAccountsTable(BaseModel):
    data: dict[str, GeneratedRawAccount] = Field(default_factory=dict)
    notes: str = ""


class GeneratedRawDisputesTable(BaseModel):
    data: dict[str, GeneratedRawDispute] = Field(default_factory=dict)
    notes: str = ""


class GeneratedRawTableDB(DB):
    accounts: GeneratedRawAccountsTable = Field(
        default_factory=GeneratedRawAccountsTable
    )
    transaction_disputes: GeneratedRawDisputesTable = Field(
        default_factory=GeneratedRawDisputesTable
    )


class ReferenceRawTable(BaseModel):
    data: dict[str, dict[str, Any]] = Field(default_factory=dict)
    notes: str = ""


class ReferenceRawTableDB(DB):
    accounts: ReferenceRawTable = Field(default_factory=ReferenceRawTable)
    transaction_disputes: ReferenceRawTable = Field(default_factory=ReferenceRawTable)


class GeneratedAliasedAccount(BaseModel):
    """Generated row with a field that uses a public JSON alias."""

    model_config = ConfigDict(populate_by_name=True)

    account_id: str
    account_class: str = Field(alias="accountClass")
    generated_only: str | None = None


class ReferenceAliasedAccount(BaseModel):
    """Reference row whose public state uses the same alias."""

    model_config = ConfigDict(populate_by_name=True)

    account_id: str
    account_class: str = Field(alias="accountClass")


class GeneratedAliasedAccountsTable(BaseModel):
    data: dict[str, GeneratedAliasedAccount] = Field(default_factory=dict)
    notes: str = ""


class ReferenceAliasedAccountsTable(BaseModel):
    data: dict[str, ReferenceAliasedAccount] = Field(default_factory=dict)
    notes: str = ""


class GeneratedAliasedTableDB(DB):
    accounts: GeneratedAliasedAccountsTable = Field(
        default_factory=GeneratedAliasedAccountsTable
    )


class ReferenceAliasedTableDB(DB):
    accounts: ReferenceAliasedAccountsTable = Field(
        default_factory=ReferenceAliasedAccountsTable
    )


class StatusTools(ToolKitBase):
    """Tiny toolkit used for DB hash projection tests."""

    @is_tool(ToolType.WRITE)
    def mark_done(self) -> str:
        self.db.status = "done"
        return "done"


class RenamedStatusTools(ToolKitBase):
    """Generated-style toolkit that reaches the same state with a different name."""

    @is_tool(ToolType.WRITE)
    def complete_request(self) -> str:
        self.db.status = "done"
        return "done"


class BillingTools(ToolKitBase):
    """Tiny billing toolkit used by evaluator projection tests."""

    def assert_bill_paid(self, bill_id: str) -> bool:
        bill = next(b for b in self.db.bills if b.bill_id == bill_id)
        return bill.status == "Paid"


def generate_agent_discoverable_tool_id(tool_name: str) -> str:
    """Deterministic ID used by discoverable-audit projection fixtures."""

    return f"agent_{tool_name}"


class DiscoverableTable(BaseModel):
    """Tiny DB table envelope used by evaluator projection tests."""

    data: dict = Field(default_factory=dict)
    notes: str = ""


class DiscoverableDB(DB):
    """DB with an audit table that reference evaluation ignores."""

    agent_discoverable_tools: DiscoverableTable = Field(
        default_factory=DiscoverableTable
    )
    status: str = "pending"


class ReferenceSuffixedReadTools(ToolKitBase):
    """Reference toolkit with a suffixed read helper from the banking KB."""

    @is_discoverable_tool(ToolType.READ)
    def get_all_user_accounts_by_user_id_3847(self, user_id: str) -> str:
        return f"accounts for {user_id}"


def test_initialization_data_preserves_separate_agent_and_user_dbs():
    environment = Environment(
        domain_name="tiny",
        policy="",
        tools=AccountTools(AccountDB()),
        user_tools=PhoneTools(PhoneDB()),
    )

    environment.set_state(
        initialization_data=InitializationData(
            agent_data={"account_status": "suspended"},
            user_data={"phone_status": "locked_pin"},
        ),
        initialization_actions=None,
        message_history=[],
    )

    assert environment.tools.db.account_status == "suspended"
    assert environment.user_tools.db.phone_status == "locked_pin"
    assert isinstance(environment.tools.db, AccountDB)
    assert isinstance(environment.user_tools.db, PhoneDB)


def test_inner_max_workers_can_be_limited_by_env(monkeypatch):
    monkeypatch.setenv("TAU2_HYPER_INNER_MAX_WORKERS", "4")

    assert _resolve_inner_max_workers(10) == 4
    assert _resolve_inner_max_workers(2) == 2
    assert _resolve_inner_max_workers(10, requested_max_workers=3) == 3

    monkeypatch.setenv("TAU2_HYPER_INNER_MAX_WORKERS", "not-an-int")

    assert _resolve_inner_max_workers(10) == 10


def test_reference_setup_materializes_hidden_init_actions():
    task = next(
        task
        for task in get_tasks_small()
        if task.id == "[service_issue]lock_sim_card_pin[PERSONA:Hard]"
    )

    materialized = _materialize_reference_setup(
        task=task,
        reference_environment_constructor=get_environment,
        solo_mode=False,
        env_kwargs={},
    )

    assert task.initial_state.initialization_actions is not None
    assert materialized.initial_state.initialization_actions is None
    assert materialized.initial_state.initialization_data is not None

    user_data = materialized.initial_state.initialization_data.user_data
    assert user_data["device"]["sim_card_status"] == "locked_pin"
    assert user_data["device"]["network_connection_status"] == "no_service"


def test_sealed_environment_without_mock_reports_no_client_api_mock(tmp_path):
    from tau2.hyper.sandbox.sealed_runner import (
        SealedCandidateEnvironment,
        SealedRunnerConfig,
    )

    sealed_environment = SealedCandidateEnvironment(
        SealedRunnerConfig(kit_path=tmp_path, domain="tiny", client_api_mode="rest"),
        metadata={"domain": "tiny", "policy": "", "tools": {}},
        runner=None,
    )
    assert not sealed_environment.uses_client_api_mock


def test_evaluator_replays_golden_actions_with_tool_name_argument():
    task = Task(
        id="golden_action_tool_name_arg",
        user_scenario={"instructions": "Echo the tool name."},
        evaluation_criteria=EvaluationCriteria(
            actions=[
                Action(
                    action_id="echo_1",
                    name="echo_tool_name",
                    arguments={"tool_name": "freeze_debit_card_3892"},
                )
            ],
            reward_basis=[RewardType.DB],
        ),
    )
    full_trajectory = [
        AssistantMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="echo_1",
                    name="echo_tool_name",
                    arguments={"tool_name": "freeze_debit_card_3892"},
                )
            ],
        ),
        ToolMessage(
            id="echo_1",
            role="tool",
            content='{"tool_name": "freeze_debit_card_3892"}',
        ),
    ]

    def constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=ToolNameArgumentTools(ToolNameArgumentDB()),
        )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=constructor,
        task=task,
        full_trajectory=full_trajectory,
        gold_environment_constructor=constructor,
    )

    assert reward.reward == 1.0
    assert reward.db_check.db_match


def test_env_assertions_can_use_reference_semantics():
    assertion = EnvAssertion(
        env_type="assistant",
        func_name="assert_internet_speed",
        arguments={"expected_speed": 200, "expected_desc": "excellent"},
    )
    predicted_environment = Environment(
        domain_name="tiny",
        policy="",
        tools=ExactSpeedTools(SpeedDB(speed_mbps=300.0, speed_desc="excellent")),
    )

    assert not predicted_environment.run_env_assertion(
        assertion, raise_assertion_error=False
    )

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=ThresholdSpeedTools(SpeedDB()),
        )

    checks, reward = _run_env_assertions(
        predicted_environment=predicted_environment,
        env_assertions=[assertion],
        environment_constructor=reference_constructor,
        initialization_data=InitializationData(
            agent_data={"speed_mbps": 300.0, "speed_desc": "excellent"}
        ),
        initialization_actions=None,
        message_history=[],
        solo_mode=False,
        env_kwargs={},
    )

    assert reward == 1.0
    assert checks[0].met


def test_reference_assertion_projection_uses_predicted_final_state():
    assertion = EnvAssertion(
        env_type="assistant",
        func_name="assert_internet_speed",
        arguments={"expected_speed": 200, "expected_desc": "excellent"},
    )
    predicted_environment = Environment(
        domain_name="tiny",
        policy="",
        tools=ExactSpeedTools(SpeedDB(speed_mbps=300.0, speed_desc="excellent")),
    )
    message_history = [
        AssistantMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="set_speed_1",
                    name="set_speed",
                    arguments={"speed_mbps": 300.0, "speed_desc": "excellent"},
                )
            ],
        ),
        ToolMessage(
            id="set_speed_1",
            role="tool",
            content='{"speed_mbps": 300.0, "speed_desc": "excellent"}',
        ),
    ]

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=ThresholdSpeedTools(SpeedDB()),
        )

    checks, reward = _run_env_assertions(
        predicted_environment=predicted_environment,
        env_assertions=[assertion],
        environment_constructor=reference_constructor,
        initialization_data=None,
        initialization_actions=None,
        message_history=message_history,
        solo_mode=False,
        env_kwargs={},
    )

    assert reward == 1.0
    assert checks[0].met


def test_construction_env_assertion_ignores_generated_user_tool_name():
    assertion = EnvAssertion(
        env_type="user",
        func_name="assert_internet_speed",
        arguments={"expected_speed": 200, "expected_desc": "excellent"},
    )
    task = Task(
        id="renamed_user_tool_assertion",
        user_scenario={"instructions": "Run a speed test."},
        evaluation_criteria=EvaluationCriteria(
            env_assertions=[assertion],
            reward_basis=[RewardType.ENV_ASSERTION],
        ),
    )
    full_trajectory = [
        UserMessage(
            role="user",
            tool_calls=[
                ToolCall(
                    id="speed_1",
                    name="record_speed_result",
                    arguments={
                        "speed_mbps": 300.0,
                        "speed_desc": "excellent",
                    },
                    requestor="user",
                )
            ],
        ),
        ToolMessage(
            id="speed_1",
            role="tool",
            content="speed recorded",
            requestor="user",
        ),
    ]

    def generated_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            user_tools=GeneratedUserSpeedTools(SpeedDB()),
        )

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            user_tools=ThresholdSpeedTools(SpeedDB()),
        )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=generated_constructor,
        task=task,
        full_trajectory=full_trajectory,
        gold_environment_constructor=reference_constructor,
    )

    assert reward.reward == 1.0
    assert reward.env_assertions[0].met


def test_construction_projection_ignores_generated_extra_db_fields():
    assertion = EnvAssertion(
        env_type="assistant",
        func_name="assert_bill_paid",
        arguments={"bill_id": "B1"},
    )
    task = Task(
        id="generated_extra_db_fields",
        user_scenario={"instructions": "Check billing state."},
        evaluation_criteria=EvaluationCriteria(
            env_assertions=[assertion],
            reward_basis=[RewardType.DB, RewardType.ENV_ASSERTION],
        ),
    )

    def generated_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=BillingTools(
                GeneratedBillingDB(
                    bills=[
                        GeneratedBill(
                            bill_id="B1",
                            status="Paid",
                            payment_request_sent=True,
                        )
                    ]
                )
            ),
        )

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=BillingTools(
                ReferenceBillingDB(bills=[ReferenceBill(bill_id="B1", status="Paid")])
            ),
        )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=generated_constructor,
        task=task,
        full_trajectory=[],
        gold_environment_constructor=reference_constructor,
    )

    assert reward.reward == 1.0
    assert reward.db_check.db_match
    assert reward.env_assertions[0].met


def test_construction_projection_uses_reference_default_for_generated_none_table():
    task = Task(
        id="generated_none_default_table",
        user_scenario={"instructions": "Mark the request done."},
        evaluation_criteria=EvaluationCriteria(
            actions=[
                Action(
                    action_id="mark_done_1",
                    name="mark_done",
                    arguments={},
                )
            ],
            reward_basis=[RewardType.DB],
        ),
    )
    full_trajectory = [
        AssistantMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="mark_done_1",
                    name="mark_done",
                    arguments={},
                )
            ],
        ),
        ToolMessage(
            id="mark_done_1",
            role="tool",
            content="done",
        ),
    ]

    def generated_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(GeneratedOptionalTableDB()),
        )

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(ReferenceDefaultTableDB()),
        )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=generated_constructor,
        task=task,
        full_trajectory=full_trajectory,
        gold_environment_constructor=reference_constructor,
    )

    assert reward.reward == 1.0
    assert reward.db_check.db_match


def test_construction_db_compare_ignores_agent_discoverable_audit_logs():
    task = Task(
        id="ignore_agent_discoverable_audit",
        user_scenario={"instructions": "No operation is needed."},
        evaluation_criteria=EvaluationCriteria(reward_basis=[RewardType.DB]),
    )

    def generated_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(DiscoverableDB()),
        )

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(
                DiscoverableDB(
                    agent_discoverable_tools=DiscoverableTable(
                        data={
                            generate_agent_discoverable_tool_id(
                                "get_all_user_accounts_by_user_id_3847"
                            ): {
                                "tool_name": ("get_all_user_accounts_by_user_id_3847"),
                                "status": "CALLED",
                            }
                        }
                    )
                )
            ),
        )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=generated_constructor,
        task=task,
        full_trajectory=[],
        gold_environment_constructor=reference_constructor,
    )

    assert reward.reward == 1.0
    assert reward.db_check.db_match


def test_construction_db_compare_allows_renamed_business_tool():
    task = Task(
        id="renamed_business_tool",
        user_scenario={"instructions": "Mark the request done."},
        evaluation_criteria=EvaluationCriteria(
            actions=[
                Action(
                    action_id="mark_done_1",
                    name="mark_done",
                    arguments={},
                )
            ],
            reward_basis=[RewardType.DB],
        ),
    )
    full_trajectory = [
        AssistantMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="complete_1",
                    name="complete_request",
                    arguments={},
                )
            ],
        ),
        ToolMessage(
            id="complete_1",
            role="tool",
            content="done",
        ),
    ]

    def generated_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=RenamedStatusTools(DiscoverableDB()),
        )

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(DiscoverableDB()),
        )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=generated_constructor,
        task=task,
        full_trajectory=full_trajectory,
        gold_environment_constructor=reference_constructor,
    )

    assert reward.reward == 1.0
    assert reward.db_check.db_match


def test_construction_db_compare_ignores_reference_suffixed_read_audit():
    suffixed_tool_name = "get_all_user_accounts_by_user_id_3847"
    task = Task(
        id="suffixed_read_audit",
        user_scenario={"instructions": "Look up the customer accounts."},
        evaluation_criteria=EvaluationCriteria(
            actions=[
                Action(
                    action_id="lookup_accounts_1",
                    name="call_discoverable_agent_tool",
                    arguments={
                        "agent_tool_name": suffixed_tool_name,
                        "arguments": '{"user_id": "user_123"}',
                    },
                )
            ],
            reward_basis=[RewardType.DB],
        ),
    )

    def generated_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(DiscoverableDB(status="done")),
        )

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=ReferenceSuffixedReadTools(DiscoverableDB(status="done")),
        )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=generated_constructor,
        task=task,
        full_trajectory=[],
        gold_environment_constructor=reference_constructor,
    )

    assert reward.reward == 1.0
    assert reward.db_check.db_match


def test_construction_db_compare_still_fails_missing_business_state():
    task = Task(
        id="missing_business_state",
        user_scenario={"instructions": "Mark the request done."},
        evaluation_criteria=EvaluationCriteria(
            actions=[
                Action(
                    action_id="mark_done_1",
                    name="mark_done",
                    arguments={},
                )
            ],
            reward_basis=[RewardType.DB],
        ),
    )

    def generated_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(DiscoverableDB()),
        )

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(DiscoverableDB()),
        )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=generated_constructor,
        task=task,
        full_trajectory=[],
        gold_environment_constructor=reference_constructor,
    )

    assert reward.reward == 0.0
    assert not reward.db_check.db_match


def test_construction_projection_trims_raw_table_row_noise():
    task = Task(
        id="raw_table_projection",
        user_scenario={"instructions": "No operation is needed."},
        evaluation_criteria=EvaluationCriteria(reward_basis=[RewardType.DB]),
    )

    def generated_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(
                GeneratedRawTableDB(
                    accounts=GeneratedRawAccountsTable(
                        data={
                            "A1": GeneratedRawAccount(
                                account_id="A1",
                                class_="checking",
                            )
                        }
                    ),
                    transaction_disputes=GeneratedRawDisputesTable(
                        data={
                            "D1": GeneratedRawDispute(
                                dispute_id="D1",
                                partial_refund_amount=None,
                            )
                        }
                    ),
                )
            ),
        )

    def reference_constructor(**_kwargs):
        return Environment(
            domain_name="tiny",
            policy="",
            tools=StatusTools(
                ReferenceRawTableDB(
                    accounts=ReferenceRawTable(
                        data={"A1": {"account_id": "A1", "class": "checking"}}
                    ),
                    transaction_disputes=ReferenceRawTable(
                        data={
                            "D1": {
                                "dispute_id": "D1",
                                "partial_refund_amount": None,
                            }
                        }
                    ),
                )
            ),
        )

    reward = EnvironmentEvaluator.calculate_reward(
        environment_constructor=generated_constructor,
        task=task,
        full_trajectory=[],
        gold_environment_constructor=reference_constructor,
    )

    assert reward.reward == 1.0
    assert reward.db_check.db_match
