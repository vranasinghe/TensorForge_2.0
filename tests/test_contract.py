import unittest

from app.contract import TEAM_BY_CATEGORY, route_category


class RoutingTests(unittest.TestCase):
    def test_fixed_routes(self):
        expected = {
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
        }
        self.assertEqual(dict(TEAM_BY_CATEGORY), expected)
        for category, team in expected.items():
            with self.subTest(category=category):
                self.assertEqual(route_category(category), team)

    def test_unknown_category_rejected(self):
        for value in ("", "unknown", "Payment_Refund", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    route_category(value)

    def test_mapping_cannot_be_mutated(self):
        with self.assertRaises(TypeError):
            TEAM_BY_CATEGORY["payment_refund"] = "Wrong team"


if __name__ == "__main__":
    unittest.main()
