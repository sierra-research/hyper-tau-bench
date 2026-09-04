# Agent Contract

Your `agent.py` file must export a factory function that the evaluator calls
to build the inner-loop agent.

---

## The factory function

```python
from tau2.hyper.agent_context import get_agent_context

def create_agent():
    """
    Returns:
        An agent instance with get_init_state() and generate_next_message()
    """
    context = get_agent_context()
    ...  # Any agent logic goes here.
```

`get_agent_context()` is available while the factory runs and returns four
runtime facilities:

- `action_interface`: the complete action catalog, its metadata, and a helper
  for selecting actions by canonical name. The catalog imposes no grouping or
  ordering.
- `resources`: the kit root, a relative file inventory, and helpers for resolving
  or reading any supplied artifact.
- `model_gateway`: access to the allowed models and their enforced constraints.
- `runtime_config`: runtime metadata such as the domain name.

These inputs are capabilities and resources, not a required arrangement. The
factory decides how, and whether, to use them.

The model gateway is the supported inference path for generated agent code.
Each inference call names a model explicitly. If the allowed list contains
multiple configurations for that model, pass enough constrained arguments to
identify exactly one; the gateway rejects ambiguous, disallowed, or conflicting
requests. Retain the gateway object in the returned agent or its components if
they need inference after `create_agent()` returns.

A constraint whose value is `{"one_of": [...]}` is a choice left open to you
rather than a fixed setting. For example:

```json
{"model": "gpt-5.6-sol", "constraints": {"reasoning_effort": {"one_of": ["high", "medium"]}}}
```

lets a call pass `reasoning_effort="high"` or `"medium"` and rejects anything
else. A pinned constraint is supplied automatically when a call omits it, but a
choice has no default: omitting it is an error, so pass one on every call. You
may vary the choice from call to call.

---

## Agent interface

Your agent must implement two methods:

### `get_init_state(message_history=None) -> state`

Called once at the start of a conversation. Returns an opaque state object
that will be threaded through every turn.

### `generate_next_message(message, state) -> (AssistantMessage, state)`

Called on each turn. Receives either a `UserMessage` (text from the
customer) or a `MultiToolMessage` (results from tool calls the agent made
on the previous turn). Returns the agent's response and updated state.

The `AssistantMessage` can contain:
- **Text content** — a message to the customer
- **Tool calls** — one or more tools to invoke

The agent should either respond with text OR make tool calls, not both
at the same time.

### Optional hooks

The runtime also recognizes three optional methods and supplies framework
defaults when an agent omits them:

- `is_stop(message) -> bool` — whether an assistant message ends the
  conversation. Default: the agent never signals stop; conversations end
  from the customer side or at the turn limit.
- `set_seed(seed: int)` — seed any internal randomness. Default: no-op.
- `stop(message, state)` — end-of-conversation cleanup. Default: no-op.
