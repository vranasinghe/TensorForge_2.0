"""Routing rules from the master guide; official schema verification pending.

These are deterministic rules, not a classifier or a replacement API schema.
"""

from types import MappingProxyType

TEAM_BY_CATEGORY = MappingProxyType({
    "payment_refund": "Payments & Refunds",
    "ride_trip_issue": "Ride Operations",
    "lost_item": "Lost & Found",
    "order_missing_wrong": "Food Operations",
    "delivery_delay": "Delivery Operations",
    "food_quality": "Restaurant Quality",
    "account_promo": "Account Services",
    "safety_conduct": "Trust & Safety",
    "app_technical": "Tech Support",
    "general_inquiry": "Front-line Support",
    "spam_irrelevant": "Auto-close / Spam Filter",
})


def route_category(category: str) -> str:
    """Return the fixed team for a known category; reject unknown categories."""
    try:
        return TEAM_BY_CATEGORY[category]
    except (KeyError, TypeError) as exc:
        raise ValueError("Unknown primary category") from exc
