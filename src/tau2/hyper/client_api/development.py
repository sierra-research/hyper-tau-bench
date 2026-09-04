"""Deterministic public records for Client API Developer local tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tau2.environment.environment import Environment

_MANIFESTS: dict[str, dict[str, Any]] = {
    "retail_plus": {
        "version": 2,
        "cases": [
            {
                "id": "pending_order",
                "description": "Pending multi-item order with three payment methods.",
                "customer_id": "developer_pending_9001",
                "email": "pending.customer@example.test",
                "order_id": "#W9000001",
                "payment_method_ids": {
                    "credit_card": "credit_card_9000001",
                    "paypal": "paypal_9000002",
                    "gift_card": "gift_card_9000003",
                },
            },
            {
                "id": "delivered_order",
                "description": "Delivered multi-item order for returns and exchanges.",
                "customer_id": "developer_delivered_9002",
                "email": "delivered.customer@example.test",
                "order_id": "#W9000002",
                "payment_method_ids": {
                    "credit_card": "credit_card_9000011",
                    "paypal": "paypal_9000012",
                    "gift_card": "gift_card_9000013",
                },
            },
        ],
    },
    "airline_plus": {
        "version": 2,
        "booking_search": {
            "origin": "ORD",
            "destination": "PHL",
            "departure_date": "2024-05-26",
            "stops": 0,
            "cabin": "economy",
        },
        "cases": [
            {
                "id": "economy_reservation",
                "description": "Uninsured one-way economy reservation.",
                "customer_id": "developer_traveler_9001",
                "email": "economy.traveler@example.test",
                "reservation_id": "DV9E01",
                "credit_card_id": "credit_card_9000001",
                "gift_card_id": "gift_card_9000002",
                "certificate_id": "certificate_9000003",
            },
            {
                "id": "basic_economy_reservation",
                "description": "Uninsured one-way basic-economy reservation.",
                "customer_id": "developer_traveler_9002",
                "email": "basic.traveler@example.test",
                "reservation_id": "DV9B02",
                "credit_card_id": "credit_card_9000011",
                "gift_card_id": "gift_card_9000012",
                "certificate_id": "certificate_9000013",
            },
            {
                "id": "insured_round_trip",
                "description": "Insured round-trip economy reservation for a gold member.",
                "customer_id": "developer_traveler_9003",
                "email": "insured.traveler@example.test",
                "reservation_id": "DV9R03",
                "credit_card_id": "credit_card_9000021",
                "gift_card_id": "gift_card_9000022",
                "certificate_id": "certificate_9000023",
            },
        ],
    },
    "telecom": {
        "version": 3,
        "cases": [
            {
                "id": "service_account",
                "description": "Account with active and suspended lines plus paid, issued, and overdue bills.",
                "customer_id": "C9001",
                "phone_number": "415-555-9001",
                "active_line_id": "L9001",
                "suspended_line_id": "L9002",
                "active_device_id": "D9001",
                "suspended_device_id": "D9002",
                "paid_bill_id": "B9001",
                "issued_bill_id": "B9002",
                "overdue_bill_id": "B9003",
            }
        ],
        "fixtures": [
            {"id": "connected", "description": "Healthy connected phone."},
            {"id": "airplane_mode", "description": "Airplane mode is on."},
            {"id": "mobile_data_off", "description": "Mobile data is off."},
            {
                "id": "roaming_abroad",
                "description": "Customer is abroad with roaming disabled.",
            },
            {
                "id": "data_limit_reached",
                "description": "The active line has reached its data limit.",
            },
            {
                "id": "slow_network_mode",
                "description": "Phone is restricted to a slow network mode.",
            },
            {
                "id": "broken_apn",
                "description": "Internet APN configuration is invalid.",
            },
            {"id": "broken_mms", "description": "MMS configuration is invalid."},
            {"id": "missing_sim", "description": "The SIM is not seated."},
            {"id": "data_saver", "description": "Data Saver is enabled."},
            {"id": "slow_vpn", "description": "A poorly performing VPN is connected."},
            {
                "id": "missing_app_permission",
                "description": "The messaging app lacks SMS permission.",
            },
            {
                "id": "missing_app_storage_permission",
                "description": "The messaging app lacks storage permission.",
            },
            {
                "id": "sim_pin_locked",
                "description": "The SIM card is locked with a PIN.",
            },
            {
                "id": "wifi_calling_on",
                "description": "Wi-Fi Calling is on with MMS over Wi-Fi.",
            },
            {
                "id": "abroad",
                "description": "Customer is abroad; device toggles are unchanged.",
            },
            {
                "id": "roaming_on",
                "description": "The device Data Roaming toggle is on.",
            },
            {
                "id": "roaming_off",
                "description": "The device Data Roaming toggle is off (the default).",
            },
            {
                "id": "line_roaming_enabled",
                "description": "The active line allows international roaming.",
            },
            {
                "id": "line_roaming_disabled",
                "description": (
                    "The active line disallows international roaming (the default)."
                ),
            },
            {
                "id": "overdue_bill_suspension",
                "description": (
                    "The active line is suspended over the existing overdue bill."
                ),
            },
            {
                "id": "contract_end_suspension",
                "description": (
                    "The active line is suspended over the existing overdue bill "
                    "and its contract has ended."
                ),
            },
        ],
    },
    "banking_knowledge": {
        "version": 2,
        "cases": [
            {
                "id": "servicing_customer",
                "description": "Customer with checking and savings accounts, active and pending debit cards, credit cards, and transaction history.",
                "customer_id": "d900000001",
                "email": "servicing.customer@example.test",
                "checking_account_id": "chk_d900000001",
                "savings_account_id": "sav_d900000001",
                "active_debit_card_id": "dbc_d900000001",
                "pending_debit_card_id": "dbc_d900000002",
                "credit_card_account_ids": [
                    "cc_d900000001_plat",
                    "cc_d900000001_gold",
                ],
                "credit_card_transaction_id": "txn_d90000000101",
                "bank_transaction_id": "btxn_d90000000101",
                "payment_history_id": "pay_d900000001_plat_202510",
                "referral_id": "d900000001000001",
            },
            {
                "id": "application_customer",
                "description": "Customer without existing products for application and referral flows.",
                "customer_id": "d900000002",
                "email": "application.customer@example.test",
            },
        ],
    },
}


def development_seed_manifest(domain: str) -> dict[str, Any]:
    """Return the public local-test record selectors for a maintained domain."""
    try:
        return deepcopy(_MANIFESTS[domain])
    except KeyError as error:
        raise ValueError(
            f"No development seed is defined for domain {domain!r}"
        ) from error


def _apply_retail_seed(environment: Environment) -> None:
    from tau2.domains.retail.data_model import (
        CreditCard,
        GiftCard,
        OrderPayment,
        Paypal,
    )

    db = environment.tools.db
    manifest = development_seed_manifest("retail_plus")
    for status, case in zip(("pending", "delivered"), manifest["cases"]):
        source_order = next(
            order
            for _, order in sorted(db.orders.items())
            if order.status == status and len(order.items) >= 2
        )
        source_user = db.users[source_order.user_id]
        payment_ids = case["payment_method_ids"]
        payment_methods = {
            payment_ids["credit_card"]: CreditCard(
                source="credit_card",
                id=payment_ids["credit_card"],
                brand="visa",
                last_four="9001" if status == "pending" else "9002",
            ),
            payment_ids["paypal"]: Paypal(
                source="paypal",
                id=payment_ids["paypal"],
            ),
            payment_ids["gift_card"]: GiftCard(
                source="gift_card",
                id=payment_ids["gift_card"],
                balance=500.0,
            ),
        }
        user = source_user.model_copy(
            deep=True,
            update={
                "user_id": case["customer_id"],
                "name": source_user.name.model_copy(
                    update={"first_name": "Developer", "last_name": "Customer"}
                ),
                "address": source_user.address.model_copy(
                    update={
                        "address1": "1 Development Way",
                        "address2": "",
                        "city": "Testville",
                        "country": "USA",
                        "state": "CA",
                        "zip": "94000",
                    }
                ),
                "email": case["email"],
                "payment_methods": payment_methods,
                "orders": [case["order_id"]],
            },
        )
        payments = [
            OrderPayment(
                transaction_type="payment",
                amount=sum(item.price for item in source_order.items),
                payment_method_id=payment_ids["credit_card"],
            )
        ]
        fulfillments = [
            fulfillment.model_copy(
                update={
                    "tracking_id": [
                        f"900000000{index:03d}"
                        for index, _ in enumerate(fulfillment.tracking_id, start=1)
                    ]
                }
            )
            for fulfillment in source_order.fulfillments
        ]
        order = source_order.model_copy(
            deep=True,
            update={
                "order_id": case["order_id"],
                "user_id": case["customer_id"],
                "address": user.address.model_copy(deep=True),
                "payment_history": payments,
                "fulfillments": fulfillments,
            },
        )
        db.users[user.user_id] = user
        db.orders[order.order_id] = order


def _apply_airline_seed(environment: Environment) -> None:
    from tau2.domains.airline.data_model import (
        Certificate,
        CreditCard,
        GiftCard,
        Passenger,
        Payment,
    )

    db = environment.tools.db
    cases = development_seed_manifest("airline_plus")["cases"]
    selectors = (
        ("economy", "one_way", "no"),
        ("basic_economy", "one_way", "no"),
        ("economy", "round_trip", "yes"),
    )
    for index, (case, selector) in enumerate(zip(cases, selectors), start=1):
        cabin, flight_type, insurance = selector
        source = next(
            reservation
            for _, reservation in sorted(db.reservations.items())
            if reservation.status is None
            and reservation.cabin == cabin
            and reservation.flight_type == flight_type
            and reservation.insurance == insurance
            and reservation.origin != reservation.destination
        )
        source_user = db.users[source.user_id]
        payment_methods = {
            case["credit_card_id"]: CreditCard(
                source="credit_card",
                id=case["credit_card_id"],
                brand="visa",
                last_four=f"91{index:02d}",
            ),
            case["gift_card_id"]: GiftCard(
                source="gift_card",
                id=case["gift_card_id"],
                amount=1000.0,
            ),
            case["certificate_id"]: Certificate(
                source="certificate",
                id=case["certificate_id"],
                amount=500.0,
            ),
        }
        passenger = Passenger(
            first_name="Developer",
            last_name=f"Traveler{index}",
            dob="1990-01-01",
        )
        alternate_passenger = Passenger(
            first_name="Sample",
            last_name=f"Guest{index}",
            dob="1992-02-02",
        )
        user = source_user.model_copy(
            deep=True,
            update={
                "user_id": case["customer_id"],
                "name": source_user.name.model_copy(
                    update={
                        "first_name": "Developer",
                        "last_name": f"Traveler{index}",
                    }
                ),
                "address": source_user.address.model_copy(
                    update={
                        "address1": f"{index} Development Way",
                        "address2": "",
                        "city": "Testville",
                        "country": "USA",
                        "state": "CA",
                        "zip": f"9400{index}",
                    }
                ),
                "email": case["email"],
                "dob": "1990-01-01",
                "payment_methods": payment_methods,
                "saved_passengers": [passenger, alternate_passenger],
                "membership": "gold"
                if case["id"] == "insured_round_trip"
                else "regular",
                "reservations": [case["reservation_id"]],
            },
        )
        reservation = source.model_copy(
            deep=True,
            update={
                "reservation_id": case["reservation_id"],
                "user_id": case["customer_id"],
                "passengers": [passenger],
                "created_at": "2024-05-15T10:00:00",
                "total_baggages": 0,
                "nonfree_baggages": 0,
                "payment_history": [
                    Payment(
                        payment_id=case["credit_card_id"],
                        amount=sum(segment.price for segment in source.flights),
                    )
                ],
            },
        )
        db.users[user.user_id] = user
        db.reservations[reservation.reservation_id] = reservation


def _apply_telecom_seed(environment: Environment) -> None:
    import datetime

    from tau2.domains.telecom.data_model import (
        AccountStatus,
        Address,
        Bill,
        BillStatus,
        Customer,
        Device,
        DeviceType,
        Line,
        LineItem,
        LineStatus,
    )

    db = environment.tools.db
    case = development_seed_manifest("telecom")["cases"][0]
    plan_id = db.plans[0].plan_id
    db.devices.extend(
        [
            Device(
                device_id=case["active_device_id"],
                device_type=DeviceType.PHONE,
                model="Developer Phone",
                imei="990000000000001",
                is_esim_capable=True,
                activated=True,
            ),
            Device(
                device_id=case["suspended_device_id"],
                device_type=DeviceType.PHONE,
                model="Developer Backup Phone",
                imei="990000000000002",
                is_esim_capable=True,
                activated=True,
            ),
        ]
    )
    db.lines.extend(
        [
            Line(
                line_id=case["active_line_id"],
                phone_number=case["phone_number"],
                status=LineStatus.ACTIVE,
                plan_id=plan_id,
                device_id=case["active_device_id"],
                data_used_gb=2.5,
            ),
            Line(
                line_id=case["suspended_line_id"],
                phone_number="415-555-9002",
                status=LineStatus.SUSPENDED,
                plan_id=plan_id,
                device_id=case["suspended_device_id"],
                suspension_start_date=datetime.date(2025, 10, 1),
            ),
        ]
    )
    line_item = LineItem(
        description="Developer plan charge",
        amount=50.0,
        date=datetime.date(2025, 10, 1),
        item_type="Plan Charge",
    )
    db.bills.extend(
        [
            Bill(
                bill_id=case["paid_bill_id"],
                customer_id=case["customer_id"],
                period_start=datetime.date(2025, 9, 1),
                period_end=datetime.date(2025, 9, 30),
                issue_date=datetime.date(2025, 10, 1),
                total_due=0.0,
                due_date=datetime.date(2025, 10, 15),
                line_items=[line_item],
                status=BillStatus.PAID,
            ),
            Bill(
                bill_id=case["issued_bill_id"],
                customer_id=case["customer_id"],
                period_start=datetime.date(2025, 10, 1),
                period_end=datetime.date(2025, 10, 31),
                issue_date=datetime.date(2025, 11, 1),
                total_due=50.0,
                due_date=datetime.date(2025, 11, 15),
                line_items=[line_item],
                status=BillStatus.ISSUED,
            ),
            Bill(
                bill_id=case["overdue_bill_id"],
                customer_id=case["customer_id"],
                period_start=datetime.date(2025, 8, 1),
                period_end=datetime.date(2025, 8, 31),
                issue_date=datetime.date(2025, 9, 1),
                total_due=50.0,
                due_date=datetime.date(2025, 9, 15),
                line_items=[line_item],
                status=BillStatus.OVERDUE,
            ),
        ]
    )
    db.customers.append(
        Customer(
            customer_id=case["customer_id"],
            full_name="Developer Customer",
            date_of_birth="1990-01-01",
            email="telecom.customer@example.test",
            phone_number=case["phone_number"],
            address=Address(
                street="1 Development Way",
                city="Testville",
                state="CA",
                zip_code="94000",
            ),
            account_status=AccountStatus.ACTIVE,
            line_ids=[case["active_line_id"], case["suspended_line_id"]],
            bill_ids=[
                case["paid_bill_id"],
                case["issued_bill_id"],
                case["overdue_bill_id"],
            ],
        )
    )


def apply_development_fixtures(
    environment: Environment, fixture_ids: str | list[str]
) -> None:
    """Apply documented host-owned fixtures in order without exposing setup internals."""
    if isinstance(fixture_ids, str):
        fixture_ids = [fixture_ids]
    manifest = development_seed_manifest(environment.domain_name)
    known_fixtures = {item["id"] for item in manifest.get("fixtures", [])}
    for fixture_id in fixture_ids:
        if fixture_id not in known_fixtures:
            raise ValueError(
                f"Unknown development fixture {fixture_id!r} for "
                f"domain {environment.domain_name!r}"
            )
    duplicates = sorted(
        {fixture_id for fixture_id in fixture_ids if fixture_ids.count(fixture_id) > 1}
    )
    if duplicates:
        raise ValueError(
            f"Duplicate development fixtures {duplicates!r}; "
            "list each fixture at most once"
        )
    if environment.domain_name != "telecom":
        raise ValueError(
            f"Domain {environment.domain_name!r} has no selectable fixtures"
        )

    from tau2.domains.telecom.user_data_model import TelecomUserDB

    case = manifest["cases"][0]
    user_db = TelecomUserDB()
    user_db.surroundings.name = "Developer Customer"
    user_db.surroundings.phone_number = case["phone_number"]
    environment.user_tools.db = user_db
    for fixture_id in fixture_ids:
        _apply_telecom_fixture(environment, case, fixture_id)
    environment.sync_tools()
    # Recompute the device network state from the fully synced surroundings so
    # Client-side fixtures (e.g. line suspension) manifest on the device the
    # same way the evaluation initializer's network refresh makes them.
    environment.user_tools.simulate_network_search()


def apply_development_fixture(environment: Environment, fixture_id: str) -> None:
    """Apply one documented host-owned fixture without exposing setup internals."""
    apply_development_fixtures(environment, [fixture_id])


def _apply_telecom_fixture(
    environment: Environment, case: dict[str, Any], fixture_id: str
) -> None:
    """Reproduce one published fixture with the evaluation's own setup functions."""
    user_tools = environment.user_tools
    tools = environment.tools
    if fixture_id == "connected":
        return
    if fixture_id == "airplane_mode":
        user_tools.turn_airplane_mode_on()
    elif fixture_id == "mobile_data_off":
        user_tools.turn_data_off()
    elif fixture_id == "roaming_abroad":
        user_tools.set_user_location(abroad=True)
        user_tools.turn_roaming_off()
    elif fixture_id == "data_limit_reached":
        line = tools._get_line_by_id(case["active_line_id"])
        plan = tools._get_plan_by_id(line.plan_id)
        tools.set_data_usage(
            customer_id=case["customer_id"],
            line_id=case["active_line_id"],
            data_used_gb=plan.data_limit_gb,
        )
    elif fixture_id == "slow_network_mode":
        user_tools.set_network_mode_preference(mode="2g_only")
    elif fixture_id == "broken_apn":
        user_tools.break_apn_settings()
    elif fixture_id == "broken_mms":
        user_tools.break_apn_mms_setting()
    elif fixture_id == "missing_sim":
        user_tools.unseat_sim_card()
    elif fixture_id == "data_saver":
        user_tools.turn_data_saver_mode_on()
    elif fixture_id == "slow_vpn":
        user_tools.break_vpn()
    elif fixture_id == "missing_app_permission":
        user_tools.remove_app_permission(app_name="messaging", permission="sms")
    elif fixture_id == "missing_app_storage_permission":
        user_tools.remove_app_permission(app_name="messaging", permission="storage")
    elif fixture_id == "sim_pin_locked":
        user_tools.lock_sim_card(mode="pin")
    elif fixture_id == "wifi_calling_on":
        user_tools.set_wifi_calling(enabled=True, mms_over_wifi=True)
    elif fixture_id == "abroad":
        user_tools.set_user_location(abroad=True)
        user_tools.simulate_network_search()
    elif fixture_id == "roaming_on":
        user_tools.turn_roaming_on()
    elif fixture_id == "roaming_off":
        user_tools.turn_roaming_off()
    elif fixture_id == "line_roaming_enabled":
        tools.enable_roaming(
            customer_id=case["customer_id"], line_id=case["active_line_id"]
        )
    elif fixture_id == "line_roaming_disabled":
        tools.disable_roaming(
            customer_id=case["customer_id"], line_id=case["active_line_id"]
        )
    elif fixture_id in ("overdue_bill_suspension", "contract_end_suspension"):
        import datetime

        from tau2.domains.telecom.data_model import LineStatus
        from tau2.domains.telecom.utils import get_today

        # The development seed already carries an overdue bill, so the fixture
        # suspends the active line against it instead of minting a second
        # overdue bill (which the setup function would reject).
        line = tools._get_line_by_id(case["active_line_id"])
        line.status = LineStatus.SUSPENDED
        line.suspension_start_date = get_today()
        if fixture_id == "contract_end_suspension":
            line.contract_end_date = get_today().replace(day=1) - datetime.timedelta(
                days=1
            )


def _apply_banking_seed(environment: Environment) -> None:
    cases = development_seed_manifest("banking_knowledge")["cases"]
    case = cases[0]
    application_case = cases[1]
    db = environment.tools.db
    db.users.data[case["customer_id"]] = {
        "name": "Developer Customer",
        "user_id": case["customer_id"],
        "address": "1 Development Way, Testville, CA 94000",
        "email": case["email"],
        "phone_number": "415-555-9003",
        "date_of_birth": "01/01/1990",
    }
    db.users.data[application_case["customer_id"]] = {
        "name": "Application Customer",
        "user_id": application_case["customer_id"],
        "address": "2 Development Way, Testville, CA 94002",
        "email": application_case["email"],
        "phone_number": "415-555-9004",
        "date_of_birth": "02/02/1992",
    }
    db.accounts.data[case["checking_account_id"]] = {
        "account_id": case["checking_account_id"],
        "user_id": case["customer_id"],
        "class": "checking",
        "level": "Green Account",
        "date_opened": "01/01/2024",
        "status": "OPEN",
        "current_holdings": "2500.00",
    }
    db.accounts.data[case["savings_account_id"]] = {
        "account_id": case["savings_account_id"],
        "user_id": case["customer_id"],
        "class": "savings",
        "level": "Green Account",
        "date_opened": "01/01/2024",
        "status": "OPEN",
        "current_holdings": "5000.00",
    }
    db.debit_cards.data[case["active_debit_card_id"]] = {
        "card_id": case["active_debit_card_id"],
        "account_id": case["checking_account_id"],
        "user_id": case["customer_id"],
        "cardholder_name": "DEVELOPER CUSTOMER",
        "last_4_digits": "9001",
        "cvv": "123",
        "status": "ACTIVE",
        "issue_date": "01/01/2024",
        "expiration_date": "01/31/2030",
        "issue_reason": "new",
    }
    db.debit_cards.data[case["pending_debit_card_id"]] = {
        "card_id": case["pending_debit_card_id"],
        "account_id": case["checking_account_id"],
        "user_id": case["customer_id"],
        "cardholder_name": "DEVELOPER CUSTOMER",
        "last_4_digits": "9002",
        "cvv": "456",
        "status": "PENDING",
        "issue_date": "11/01/2025",
        "expiration_date": "11/30/2030",
        "issue_reason": "stolen",
    }
    platinum_id, gold_id = case["credit_card_account_ids"]
    db.credit_card_accounts.data[platinum_id] = {
        "account_id": platinum_id,
        "user_id": case["customer_id"],
        "card_type": "Platinum Rewards Card",
        "date_of_account_open": "01/01/2024",
        "current_balance": "$75.00",
        "reward_points": "750 points",
    }
    db.credit_card_accounts.data[gold_id] = {
        "account_id": gold_id,
        "user_id": case["customer_id"],
        "card_type": "Gold Rewards Card",
        "date_of_account_open": "06/01/2024",
        "current_balance": "$125.00",
        "reward_points": "1250 points",
    }
    db.credit_card_transaction_history.data[case["credit_card_transaction_id"]] = {
        "transaction_id": case["credit_card_transaction_id"],
        "user_id": case["customer_id"],
        "credit_card_type": "Platinum Rewards Card",
        "merchant_name": "Developer Market",
        "transaction_amount": "$25.00",
        "transaction_date": "10/15/2025",
        "category": "Groceries",
        "status": "COMPLETED",
        "rewards_earned": "250 points",
    }
    db.bank_account_transaction_history.data[case["bank_transaction_id"]] = {
        "transaction_id": case["bank_transaction_id"],
        "account_id": case["checking_account_id"],
        "date": "11/01/2025",
        "description": "DEVELOPER MARKET TESTVILLE CA",
        "amount": -25.0,
        "type": "card_purchase",
        "status": "posted",
    }
    db.payment_history.data[case["payment_history_id"]] = {
        "payment_id": case["payment_history_id"],
        "credit_card_account_id": platinum_id,
        "user_id": case["customer_id"],
        "payment_date": "10/15/2025",
        "amount": "$75.00",
        "status": "ON_TIME",
    }
    db.referrals.data[case["referral_id"]] = {
        "referral_id": case["referral_id"],
        "referrer_id": case["customer_id"],
        "referred_account_type": "Gold Rewards Card",
        "referral_status": "COMPLETE",
        "date": "10/20/2025",
    }


def apply_development_seed(environment: Environment) -> None:
    """Add fresh synthetic records to one local-test environment."""
    appliers = {
        "retail_plus": _apply_retail_seed,
        "airline_plus": _apply_airline_seed,
        "telecom": _apply_telecom_seed,
        "banking_knowledge": _apply_banking_seed,
    }
    try:
        applier = appliers[environment.domain_name]
    except KeyError as error:
        raise ValueError(
            f"No development seed is defined for domain {environment.domain_name!r}"
        ) from error
    applier(environment)
    environment.sync_tools()
