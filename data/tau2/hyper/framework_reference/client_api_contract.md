# Client API Contract

Implement tools as a `ClientAPIToolKitBase` subclass in
`workspace/tools.py`. The runtime constructs the toolkit with a `ClientAPI`,
available as `self.client_api`. Methods decorated with `@is_tool` are advertised
to the customer-service agent and may make one or more Client API requests.

```python
from urllib.parse import quote

from tau2.environment.toolkit import ToolType, is_tool
from tau2.hyper.client_api import ClientAPIToolKitBase


class Tools(ClientAPIToolKitBase):
    @is_tool(ToolType.READ)
    def get_order(self, order_id: str) -> dict:
        """Get an order by its customer-facing identifier."""
        response = self.client_api.request(
            "GET",
            f"/v1/orders/{quote(order_id, safe='')}",
        )
        response.raise_for_status()
        return response.body
```

The REST interface is defined by `client_api/openapi.yaml`. A response has
`status_code`, `body`, `headers`, and `elapsed_seconds`. Inspect status and body
explicitly; `raise_for_status()` is available when a non-2xx response should
become a tool error.

## Conversation context

`self.client_api.context` contains trusted, read-only context for the active
conversation. It currently exposes only `conversation_id`. Use this value for
operations whose OpenAPI path contains `{conversation_id}`; URL encode it like
any other path identifier. Do not ask the customer or model to supply it.

For example, a live-transfer tool addresses the Client conversation resource:

```python
class Tools(ClientAPIToolKitBase):
    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> dict:
        conversation_id = quote(
            self.client_api.context.conversation_id,
            safe="",
        )
        response = self.client_api.request(
            "POST",
            f"/v1/conversations/{conversation_id}/transfers",
            body={"summary": summary},
        )
        response.raise_for_status()
        return response.body
```

The Client associates the authenticated conversation transcript and routing
context with the transfer. The agent supplies only the issue summary. A
successful response means the live transfer was accepted; it is not safe to
retry automatically, and later Client operations for that conversation are
rejected.

The OpenAPI document is normative for payload shape. In particular:

- Resource identifiers in paths must be URL encoded. This is especially
  important for identifiers containing reserved characters — a leading `#`
  encodes as `%23`.
- `enum` values are exhaustive. Do not invent or normalize additional values.
- A field accepts JSON `null` only when its schema includes a `null` branch.
- Every operation documents whether it mutates state, whether repeated calls
  are safe, whether automatic retries are allowed, its consistency behavior,
  and whether it paginates through `x-api-*` fields.
- Error responses use the shared `APIError` envelope. A `400` means the
  request does not match the documented path, query, or body schema; a `404`
  means a referenced resource was not found; a `409` means the resource's
  current state prevents the operation; and a `422` means a structurally valid
  request violates a business constraint. Status codes and error codes are the
  public contract; messages are stable summaries that omit private business
  rules and implementation details.

Read operations are safe to repeat and may be retried automatically. A write
operation's idempotency is not guaranteed, so never retry one automatically
after a timeout or transport ambiguity. Successful writes are strongly
consistent: a later read in the same conversation observes the completed
change.
Operations marked with `x-api-pagination: none` return their complete result;
do not send undocumented page parameters.

Each operation also publishes `x-api-request-body-max-bytes` and
`x-api-response-body-max-bytes`. Sizes are measured after compact JSON
serialization as UTF-8. The contract permits requests through 1,048,576 bytes
(query parameters and body combined) and response bodies through 4,194,304
bytes. A larger request returns `413 request_too_large`; an operation whose
result cannot fit returns `502 response_too_large`. Treat either response like
any other documented error rather than trimming, splitting, or retrying the
write.

The contract intentionally separates the two interfaces:

- Agent-facing tool names, parameters, return types, and descriptions are
  authored in `workspace/tools.py`.
- Client-facing HTTP methods, paths, request schemas, response schemas, and
  errors are authored in `client_api/openapi.yaml`.

The mapping need not be one-to-one. One agent tool may compose several client
requests, and several agent tools may share one client operation.
Developer-local deterministic utilities do not represent Client resources and
may be implemented without making a Client API request.

Toolkit instances may keep in-memory session state across calls within one
conversation. During grading, a conversation's recorded tool calls are
re-executed in order against a fresh toolkit instance and a fresh backend, so
each tool must behave as a deterministic function of the backend state, its
arguments, and the calls that preceded it in the same conversation. Behavior
that depends on anything else — wall-clock time, randomness, or state carried
over from outside the conversation — may diverge on re-execution and fail the
conversation.

## Local scenario backends

`run_local_test` supports two mutually exclusive backends per Developer-authored
scenario: a fresh deterministic development seed, or a Developer-authored
Python mock that runs inside the sealed candidate sandbox. The backend changes
only local testing. Submitted and held-out evaluation conversations always use
the real Client API runtime.

See `framework/scenario_contract.md` for the `client_api` scenario field, mock
factory contract, lifecycle, trace, verification hook, and grading limits.
