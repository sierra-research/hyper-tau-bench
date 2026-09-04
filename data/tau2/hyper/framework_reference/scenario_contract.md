# Customer Scenario Contract

This document describes the JSON files you can write for customer
simulations. A scenario is not a unit test. It is a description of a customer
arriving with a situation, goals, and any facts they know. The simulator uses
that scenario to converse with your agent.

Run a scenario by calling the `run_local_test` tool from the construction
environment:

```text
run_local_test(task_path="workspace/my_customer_scenario.json")
```

This runs only the scenario file or directory you provide against your
submitted assistant toolkit. For Client API tasks, local tests use a sandbox
service implementing `client_api/openapi.yaml`. Only the documented REST
interface and its responses are part of the Developer contract; local-test
behavior does not expand or override that contract. Held-out scenarios are not
loaded.

Developer-authored scenarios are local behavioral probes. They do not become
the final evaluation suite or define its request distribution, and passing them
does not by itself establish overall agent quality. Final quality is measured
across a broader set of unseen evaluation cases.

## Minimal Scenario

```json
{
  "id": "my_customer_scenario_001",
  "user_scenario": {
    "persona": "A concise customer who answers follow-up questions directly.",
    "instructions": "I am calling because I need help with <situation>. I know <facts the customer knows>. I want the agent to <customer goal>."
  },
  "evaluation_criteria": {
    "nl_assertions": [
      "The agent resolved the customer's request or clearly explained why it could not be resolved.",
      "The agent followed the domain policy in the provided materials."
    ],
    "reward_basis": ["NL_ASSERTION"]
  }
}
```

Set `reward_basis` explicitly. If you omit it, the backend default is
`["DB", "COMMUNICATE"]`, so natural-language assertions will be evaluated but
will not affect the reported reward.

## Backend Lifecycle

When `run_local_test` runs a scenario, the backend does the following:

1. Loads the JSON file into the `Task` data model.
2. Loads `workspace/tools.py`, `workspace/agent.py`, and any other applicable
   workspace files present in the kit.
3. Installs the available actions, generic kit-resource access, constrained model gateway,
   and runtime configuration, then calls `create_agent()`. The factory can read
   those facilities with `get_agent_context()`.
4. Creates a simulated customer using the standard local scenario runtime.
5. Routes customer-side tool calls through the provided customer-side runtime
   when the domain includes one.
6. Converts `user_scenario` to text with `str(task.user_scenario)` and passes
   that text as the simulated customer's private instructions.
7. If the scenario includes `user_tools`, filters the available customer-side
   tools to that list. If `user_tools` is omitted, the default customer-side
   tools for the domain are available when the domain provides them.
8. Runs a turn-by-turn conversation among customer, agent, and environment.
9. Evaluates the resulting transcript and final environment state according to
   `evaluation_criteria.reward_basis`.
10. Writes a timestamped artifact under `simulations/` containing the transcript,
    tool calls, reward details, and serialized result data available to the
    construction harness.

The simulation path lets you run your own scenarios against the same
customer/user runtime shape used after submission, without requiring you to
implement customer-side phone or device tools yourself.

For REST kits, each scenario chooses exactly one Client API mode. If the
`client_api` field is omitted, the mode is `seeded`: the scenario starts with a
fresh copy of the synthetic records listed in
`client_api/development_seed.json`. Those public identifiers are intentionally
stable for local testing and are not part of final evaluation. The records use
the same identifier conventions and resource shapes as the domain's ordinary
data. Some domains also list named `fixtures` that put the local
customer/device runtime into a documented state.

A `mock` mode scenario has the following form:

```json
{
  "id": "declining_service_001",
  "client_api": {
    "mode": "mock",
    "module": "workspace/mock_client_api.py",
    "config": {"account_id": "acct_test", "failures_before_success": 1}
  },
  "user_scenario": {
    "instructions": "I need help with account acct_test."
  },
  "evaluation_criteria": {
    "nl_assertions": ["The agent handled the changing service response."],
    "reward_basis": ["NL_ASSERTION"]
  }
}
```

The module runs only inside the sealed candidate sandbox and must define
`create_mock_client_api(config)`. The factory is called once for each fresh
scenario instance. It returns either a callable or an object with
`request(payload)`, where `payload` contains only the public `method`, `path`,
`query`, `body`, and `headers`. Return the ordinary Client API response
envelope: `status_code`, `body`, and optional `headers` and
`elapsed_seconds`.

```python
class MockClientAPI:
    def __init__(self, config):
        self.calls = 0
        self.failures_before_success = config["failures_before_success"]

    def request(self, request):
        self.calls += 1
        if request["path"] == "/v1/example":
            status = 503 if self.calls <= self.failures_before_success else 200
            return {"status_code": status, "body": {"call": self.calls}}
        return {
            "status_code": 404,
            "body": {"error": {"message": "Not mocked"}},
        }

    def verify(self):
        assert self.calls >= 2, "expected the example operation to be retried"


def create_mock_client_api(config):
    return MockClientAPI(config)
```

State belongs to that returned object, so identical requests may produce
different responses over time. An optional `verify()` hook runs after the
conversation; raise an exception or assertion to fail the local scenario. The
timestamped simulation artifact records every mock request and response, plus
the verification result. Callback exceptions are reported as local test
failures.

Mock code has the same offline, read-only-workspace, time, request-count, JSON
envelope, and payload-size boundaries as the rest of the candidate runtime. It
cannot call or inspect the real Client environment. The harness deliberately
does not validate mocked operation shapes against `client_api/openapi.yaml`;
the Developer owns whether a mock represents a possible Client response.

`seeded` and `mock` are mutually exclusive. Mock scenarios cannot select a
`development_fixture` or use `DB` grading because there is no real Client DB to
compare. Set `reward_basis` explicitly to transcript, response, action, or
environment assertions. Customer-side simulator tools remain host-provided
when the domain has them, but their private runtime is not shared with the mock
callback; describe any mocked Client state needed by the customer in the
scenario instructions.

Mock-backed local tests run on the current construction runtime image. This
does not change the versioned image selected by the task for submitted or
held-out evaluation conversations.

## Customer Instructions

`user_scenario` is the information given to the simulated customer, not to your
agent. The agent only sees what the customer says during the conversation.

`user_scenario.persona`: Optional. The customer's general communication style
or background. Keep this separate from the task-specific situation.

`user_scenario.instructions`: The customer's situation, what they know, and
what they are trying to accomplish. This can be a plain string, or a structured
object with these fields:

```json
{
  "domain": "example_support",
  "reason_for_call": "Why the customer contacted support.",
  "known_info": "Facts the customer knows and may provide.",
  "unknown_info": "Facts the customer does not know and should not invent.",
  "task_instructions": "What the customer is trying to accomplish."
}
```

The structured form is rendered into labeled text sections. `known_info` should
contain facts the customer can reveal. `unknown_info` should contain facts the
customer should not invent; if the agent asks, the customer should say they do
not know or ask how to find it.

## Reward Basis

`evaluation_criteria.reward_basis` controls which checks affect the numeric
reward. Available values are:

| Value | What It Checks | Typical Local Use |
|-------|----------------|-------------------|
| `NL_ASSERTION` | Uses an LLM judge to decide whether the transcript satisfies each string in `evaluation_criteria.nl_assertions`. | Best default for customer simulations because it checks behavior without requiring exact tool names. |
| `RESPONSE_ASSERTION` | Checks deterministic assistant response phrasing constraints in `evaluation_criteria.response_assertions`. | Useful for exact style constraints such as forbidden words or maximum phrase counts. |
| `COMMUNICATE` | Checks whether each string in `evaluation_criteria.communicate_info` appears in an assistant text response. | Useful for simple exact communication checks; it is substring-based and less flexible than `NL_ASSERTION`. |
| `ACTION` | Checks whether tool calls in the transcript match `evaluation_criteria.actions` by name and selected arguments. | Useful when you intentionally want to require a specific tool interface. It can overconstrain alternative implementations. |
| `DB` | Compares the final environment state against the state expected from `evaluation_criteria.actions`. | Useful for exact state-change checks when you can specify the expected state through actions. If no actions or environment assertions are provided, there is no meaningful state check. |
| `ENV_ASSERTION` | Calls functions listed in `evaluation_criteria.env_assertions` against the environment and compares their boolean result with `assert_value`. | Useful only when the relevant assertion helper exists in the environment. |

Multiple reward bases are multiplied together. If any included check receives
0, the overall reward becomes 0.

## Evaluation Criteria Fields

`nl_assertions`: Natural-language statements about what should be true of the
conversation. These are only part of the reward if `reward_basis` includes
`"NL_ASSERTION"`.

`response_assertions`: Deterministic assertions over assistant customer-facing
messages. These are only part of the reward if `reward_basis` includes
`"RESPONSE_ASSERTION"`.

`communicate_info`: Exact strings or facts that should appear in an assistant
message. These are only part of the reward if `reward_basis` includes
`"COMMUNICATE"`.

`actions`: Expected assistant or customer tool calls. Each action has:

```json
{
  "action_id": "unique_action_name",
  "requestor": "assistant",
  "name": "tool_name",
  "arguments": {"arg_name": "arg_value"},
  "compare_args": ["arg_name"]
}
```

`requestor` can be `"assistant"` or `"user"`. `compare_args` controls which
arguments are compared. If `compare_args` is omitted, all provided arguments are
checked.

`env_assertions`: Environment function checks. Each assertion has:

```json
{
  "env_type": "assistant",
  "func_name": "assertion_or_tool_function_name",
  "arguments": {},
  "assert_value": true,
  "message": "Optional failure message."
}
```

`env_type` can be `"assistant"` or `"user"`. Use this only when the target
function exists in the relevant environment.

## Optional Scenario Fields

`description`: Optional notes for yourself about the scenario's purpose,
relevant policies, or unusual edge cases. If present, it must be a JSON object;
use fields like `purpose` and `notes`. For example:

```json
{
  "purpose": "Exercise a repeat caller asking about a pending request.",
  "notes": "REQ-2041 is created and left pending during setup."
}
```

`initial_state`: Optional setup for the conversation or message history. Most
local scenarios do not need this. In a REST kit it can include:

```json
{
  "development_fixture": ["service_paused", "alerts_muted"],
  "initialization_actions": [
    {
      "env_type": "assistant",
      "func_name": "tool_or_setup_function",
      "arguments": {}
    }
  ],
  "message_history": []
}
```

In REST mode, Developer-authored scenarios cannot use `initialization_data`:
it would describe private Client storage rather than the public API. They also
cannot use user initialization actions. Assistant `initialization_actions` are
allowed, but their names resolve only against the Developer's own assistant tools
in `workspace/tools.py`. They run after the fresh Client API context is
installed, so a wrapper tool can prepare a case by making ordinary documented
REST calls. They do not resolve against private Client functions.

In seeded mode, `development_fixture` may be a fixture ID published for the
domain in `client_api/development_seed.json`, or a list of those IDs, such as
`"service_paused"` or `["service_paused", "autopay_off", "alerts_muted"]`. It
is a local-test-only selector for documented host-owned states; it is not a
database payload or a private function call. A list is applied in order, so a
later fixture wins where two touch the same setting; list each fixture at most
once. Unknown fixture IDs are rejected. Omit the field when the domain has no
listed fixtures or when the baseline connected state is appropriate.

`message_history` preloads an existing conversation. Legacy non-REST kits keep
their existing database-backed initialization behavior.

`user_tools`: Optional list of customer-side tool names available to the user
simulator for this scenario. Omit this field to allow the customer-side runtime
to choose its default tools. Use an empty list only when you want a
purely text-only simulated customer.

`required_documents`: Optional list of document titles expected to matter in
knowledge-heavy domains. This is metadata for analysis and debugging; it does
not automatically retrieve documents for the agent.
