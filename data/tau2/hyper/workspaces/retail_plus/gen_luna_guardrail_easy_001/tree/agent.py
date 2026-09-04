from typing import Any, Dict, List, Optional, Tuple

from tau2.data_model.message import AssistantMessage, MultiToolMessage, UserMessage
from tau2.hyper.agent_context import get_agent_context


SYSTEM_PROMPT = """You are NorthStar retail customer support.
Be warm, concise, and accurate. Use the available tools for customer, order,
payment, delivery, address, return, and exchange facts. Never invent data.

Verify identity with an exact email or complete name and postal code before
discussing profile, order, payment, address, delivery, return, or exchange
information. If verification fails, reveal nothing about the account or order.

A delivered order cannot be cancelled; explain that a return is the route.
Returns and exchanges begin only after an order is marked delivered. Exchanges
change variants of the same product type, not unrelated products.

Before submitting a return or exchange, identify the exact order and complete
item list, explain the outcome, recap payment details, and obtain explicit
confirmation. Do not infer confirmation from “okay,” “uh-huh,” or silence.
Never expose full card numbers. Use only payment type and last four digits.

A gift-card balance must cover an entire exchange increase. Do not split an
exchange difference unless the API explicitly supports it. An order cannot
receive a second submitted return or exchange workflow. Account-address changes
do not rewrite existing orders.

Do not perform a write when the customer is only asking for information,
comparing options, or asking to pause. Explain refusals clearly and politely.
"""


class Guard:
    """Central, auditable preflight policy for model-requested tool calls."""

    READS = {
        "search_customer",
        "get_customer",
        "get_order",
        "list_customer_orders",
        "list_payment_methods",
        "get_order_messages",
    }
    WRITES = {
        "submit_return",
        "submit_exchange",
        "cancel_order",
        "update_customer_address",
        "add_delivery_instructions",
        "transfer_to_human_agents",
    }

    def __init__(self) -> None:
        self.verified_customer: Optional[str] = None
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.confirmed_orders: Dict[str, bool] = {}

    def check(self, name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        if name not in self.READS and name not in self.WRITES:
            return False, "That operation is not available."

        if name in {"get_customer", "list_customer_orders", "list_payment_methods"}:
            customer_id = args.get("customer_id")
            if not self.verified_customer or customer_id != self.verified_customer:
                return False, "Please verify the customer profile first."

        if name in {"get_order", "get_order_messages"}:
            if not self.verified_customer:
                return False, "Please verify the customer profile first."

        if name in {"submit_return", "submit_exchange", "cancel_order"}:
            order_id = str(args.get("order_id", ""))
            order = self.orders.get(order_id)
            if order:
                status = str(order.get("status", "")).lower()
                if name == "cancel_order" and status == "delivered":
                    return False, "A delivered order cannot be cancelled; a return is the available route."
                if name in {"submit_return", "submit_exchange"} and status != "delivered":
                    return False, "This request can begin only after the order is marked delivered."
                if status in {"return requested", "exchange requested"}:
                    return False, "This order already has a submitted workflow."
            if name in {"submit_return", "submit_exchange"}:
                if not args.get("items"):
                    return False, "The exact items must be identified first."
                if not self.confirmed_orders.get(order_id):
                    return False, "Explicit confirmation is required before submission."

        return True, ""

    def observe(self, name: str, args: Dict[str, Any], result: Any) -> None:
        if not isinstance(result, dict) or result.get("ok") is False:
            return
        if name == "search_customer" and result.get("customer_id"):
            self.verified_customer = str(result["customer_id"])
        elif name == "get_order" and args.get("order_id"):
            self.orders[str(args["order_id"])] = result


class RetailAgent:
    def __init__(self, context: Any) -> None:
        self.context = context
        self.guard = Guard()
        self.history: List[Any] = []
        self.closed = False
        self.model = self._choose_model()

    def _choose_model(self) -> str:
        models = getattr(self.context.model_gateway, "models", ())
        names = [getattr(item, "model", str(item)) for item in models]
        for preferred in (
            "gpt-5.6-sol",
            "anthropic/claude-opus-5",
            "google/gemini-3.1-pro-preview",
        ):
            if preferred in names:
                return preferred
        return names[0] if names else "gpt-5.6-sol"

    @staticmethod
    def _name(call: Any) -> str:
        return str(getattr(call, "name", ""))

    @staticmethod
    def _args(call: Any) -> Dict[str, Any]:
        args = getattr(call, "arguments", {})
        return args if isinstance(args, dict) else {}

    def get_init_state(self, message_history: Optional[List[Any]] = None) -> Dict[str, Any]:
        self.history = list(message_history or [])
        self.guard = Guard()
        self.closed = False
        return {"history": self.history, "guard": self.guard}

    def generate_next_message(
        self,
        message: Any,
        state: Dict[str, Any],
    ) -> Tuple[AssistantMessage, Dict[str, Any]]:
        if self.closed:
            return AssistantMessage(
                role="assistant",
                content="This conversation is closed.",
            ), state

        self.history.append(message)
        prompt_messages = [
            UserMessage(role="user", content=SYSTEM_PROMPT),
            *self.history,
        ]
        response = self.context.model_gateway.generate(
            model=self.model,
            messages=prompt_messages,
            actions=self.context.action_interface.available,
            tool_choice="auto",
        )
        calls = list(getattr(response, "tool_calls", ()) or ())
        if calls:
            permitted = []
            refusals = []
            for call in calls:
                allowed, reason = self.guard.check(
                    self._name(call),
                    self._args(call),
                )
                if allowed:
                    permitted.append(call)
                else:
                    refusals.append(reason)
            if refusals and not permitted:
                response = AssistantMessage(
                    role="assistant",
                    content="I can’t complete that yet: " + " ".join(refusals),
                )
            elif refusals:
                response = AssistantMessage(
                    role="assistant",
                    content="I’ll handle the permitted lookup first. "
                    + " ".join(refusals),
                    tool_calls=permitted,
                )

        self.history.append(response)
        state["history"] = self.history
        state["guard"] = self.guard
        return response, state

    def is_stop(self, message: Any) -> bool:
        content = getattr(message, "content", "")
        text = content.lower() if isinstance(content, str) else str(content).lower()
        return any(
            phrase in text
            for phrase in (
                "goodbye",
                "end this conversation",
                "conversation is closed",
            )
        )

    def stop(self) -> None:
        self.closed = True


def create_agent() -> RetailAgent:
    return RetailAgent(get_agent_context())
