import unittest

from backend.app.main import accuracy_breakdown, accuracy_summary, decision, health


class ApiTests(unittest.TestCase):
    def test_health(self):
        response = health()
        self.assertEqual(response["status"], "ok")
        self.assertTrue(response["dataAvailable"])

    def test_decision_date_filter(self):
        response = decision(from_date=None, to_date=None)
        self.assertEqual(response["count"], 744)

    def test_invalid_date_range(self):
        from datetime import date
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            decision(from_date=date(2026, 1, 2), to_date=date(2026, 1, 1))

    def test_accuracy_summary(self):
        response = accuracy_summary()
        self.assertEqual(response["metrics"]["count"], 744)

    def test_accuracy_timeseries_and_breakdown(self):
        from backend.app.main import accuracy_timeseries
        timeseries = accuracy_timeseries(from_date=None, to_date=None)
        breakdown = accuracy_breakdown()
        self.assertEqual(timeseries["count"], 744)
        self.assertEqual(len(breakdown["byDeliveryHourUtc"]), 24)


if __name__ == "__main__":
    unittest.main()
