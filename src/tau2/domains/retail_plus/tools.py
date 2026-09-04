"""Toolkit for the retail_plus domain: retail with de-memorized values.

Canonical retail bakes policy content into several tool docstrings: the
cancel_pending_order docstring carries the "5-7 business days" refund window,
the gift-card-immediate rule, and the accepted-reason list; the
modify_pending_order_items docstring teaches the item-change one-shot lock;
and the exchange_delivered_order_items docstring teaches the shared
single-pass rule for delivered orders. retail_plus overrides those
docstrings to strip policy content from the tool schema entirely: the schema
is read by downstream test agents at runtime, so any policy value stated here
is env-revealed and can never discriminate between policies that do and don't
contain it. The retail_plus values live in
the policy corpus and delta_spec.yaml, not in tool schemas. Everything else
(prices, balances, ids) lives in the retail_plus db.
"""

from typing import List

from tau2.domains.retail.data_model import Order
from tau2.domains.retail.tools import RetailTools
from tau2.environment.toolkit import ToolType, is_tool


class RetailPlusTools(RetailTools):
    """Retail tools with policy content stripped from the tool schema."""

    @is_tool(ToolType.WRITE)
    def cancel_pending_order(self, order_id: str, reason: str) -> Order:
        """Cancel a pending order. If the order is already processed or delivered,
        it cannot be cancelled. The agent needs to explain the cancellation detail
        and ask for explicit user confirmation (yes/no) to proceed. If the user confirms,
        the order status will be changed to 'cancelled' and the payment will be refunded.
        The function returns the order details after the cancellation.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
            reason: The reason the customer gives for the cancellation.

        Returns:
            Order: The order details after the cancellation.
        """
        return super().cancel_pending_order(order_id, reason)

    @is_tool(ToolType.WRITE)
    def modify_pending_order_items(
        self,
        order_id: str,
        item_ids: List[str],
        new_item_ids: List[str],
        payment_method_id: str,
    ) -> Order:
        """Modify items in a pending order to new items of the same product type. The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
            item_ids: The item ids to be modified, each such as '1008292230'. There could be duplicate items in the list.
            new_item_ids: The item ids to be modified for, each such as '1008292230'. There could be duplicate items in the list. Each new item id should match the item id in the same position and be of the same product.
            payment_method_id: The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details.

        Returns:
            Order: The order details after the modification.

        Raises:
            ValueError: If the order is not pending.
            ValueError: If the items to be modified do not exist.
            ValueError: If the new items do not exist or do not match the old items.
            ValueError: If the number of items to be modified does not match.
        """
        return super().modify_pending_order_items(
            order_id, item_ids, new_item_ids, payment_method_id
        )

    @is_tool(ToolType.WRITE)
    def exchange_delivered_order_items(
        self,
        order_id: str,
        item_ids: List[str],
        new_item_ids: List[str],
        payment_method_id: str,
    ) -> Order:
        """Exchange items in a delivered order to new items of the same product type.
        The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
            item_ids: The item ids to be exchanged, each such as '1008292230'. There could be duplicate items in the list.
            new_item_ids: The item ids to be exchanged for, each such as '1008292230'.
                         There could be duplicate items in the list. Each new item id should match the item id
                         in the same position and be of the same product.
            payment_method_id: The payment method id to pay or receive refund for the item price difference,
                             such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up
                             from the user or order details.

        Returns:
            Order: The order details after the exchange.

        Raises:
            ValueError: If the order is not delivered.
            ValueError: If the items to be exchanged do not exist.
            ValueError: If the new items do not exist or do not match the old items.
            ValueError: If the number of items to be exchanged does not match.
        """
        return super().exchange_delivered_order_items(
            order_id, item_ids, new_item_ids, payment_method_id
        )
