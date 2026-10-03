"""Tools the agent can call. Data is fixed mock data so tests are repeatable."""

import os
from datetime import datetime

# Mock order database.
ORDERS = {
    "48213": {
        "status": "shipped",
        "shipping": "express",
        "estimated_delivery": "2026-10-06",
    },
    "51007": {
        "status": "delivered",
        "purchase_date": "2026-09-01",
        "price_usd": 40.0,
        "item_type": "physical",
    },
}

# Mock exchange rates (units of currency per 1 USD).
RATES = {"KRW": 1380.0, "EUR": 0.92, "JPY": 148.0}


def lookup_order(order_id: str) -> dict:
    """Look up an order by its ID and return its status and details.

    Args:
        order_id: The order number, digits only (for example "48213").
    """
    order = ORDERS.get(order_id.lstrip("#"))
    return order if order else {"error": f"Order {order_id} not found."}


def get_today() -> str:
    """Return today's date in YYYY-MM-DD format."""
    # AGENT_TODAY pins the date so test results don't change day to day.
    return os.getenv("AGENT_TODAY") or datetime.now().astimezone().date().isoformat()


def convert_currency(amount_usd: float, currency: str) -> dict:
    """Convert an amount in US dollars to another currency.

    Args:
        amount_usd: The amount in US dollars.
        currency: Target currency code, for example "KRW".
    """
    rate = RATES.get(currency.upper())
    if rate is None:
        return {"error": f"Unsupported currency: {currency}"}
    return {"amount": round(amount_usd * rate, 2), "currency": currency.upper(), "rate": rate}


TOOLS = [lookup_order, get_today, convert_currency]
