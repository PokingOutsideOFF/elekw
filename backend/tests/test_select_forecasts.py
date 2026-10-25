import unittest
from datetime import datetime, timezone

from backend.scripts.select_forecasts import (
    decision_cutoff_for_delivery,
    select_latest_eligible_forecast,
)


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ForecastSelectionTests(unittest.TestCase):
    def test_selects_latest_publication_at_or_before_cutoff(self):
        delivery = utc("2026-01-10T12:00:00Z")
        forecasts = [
            {"deliveryTime": "2026-01-10T12:00:00Z", "publishTime": "2026-01-09T08:00:00Z", "forecastMW": 100},
            {"deliveryTime": "2026-01-10T12:00:00Z", "publishTime": "2026-01-09T09:00:00Z", "forecastMW": 110},
            {"deliveryTime": "2026-01-10T12:00:00Z", "publishTime": "2026-01-09T09:01:00Z", "forecastMW": 999},
        ]
        result = select_latest_eligible_forecast(delivery, forecasts)
        self.assertEqual(result["forecastMW"], 110)
        self.assertEqual(result["selectedPublishTime"], "2026-01-09T09:00:00Z")

    def test_publication_after_cutoff_is_not_selected(self):
        delivery = utc("2026-01-10T12:00:00Z")
        forecasts = [
            {"deliveryTime": "2026-01-10T12:00:00Z", "publishTime": "2026-01-09T09:01:00Z", "forecastMW": 999},
        ]
        result = select_latest_eligible_forecast(delivery, forecasts)
        self.assertEqual(result["selectionStatus"], "missing")
        self.assertIsNone(result["forecastMW"])

    def test_no_eligible_publication_is_marked_missing(self):
        delivery = utc("2026-01-10T12:00:00Z")
        result = select_latest_eligible_forecast(delivery, [])
        self.assertEqual(result["selectionStatus"], "missing")
        self.assertEqual(result["decisionCutoff"], "2026-01-09T09:00:00Z")

    def test_cutoff_uses_previous_local_calendar_day_at_date_boundary(self):
        delivery = utc("2026-01-01T00:00:00Z")
        cutoff = decision_cutoff_for_delivery(delivery)
        self.assertEqual(cutoff, utc("2025-12-31T09:00:00Z"))

    def test_cutoff_handles_british_summer_time(self):
        delivery = utc("2026-07-01T00:00:00Z")
        cutoff = decision_cutoff_for_delivery(delivery)
        self.assertEqual(cutoff, utc("2026-06-30T08:00:00Z"))


if __name__ == "__main__":
    unittest.main()
