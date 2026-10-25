import unittest

from backend.scripts.calculate_accuracy import calculate_metrics, hourly_actuals


class AccuracyTests(unittest.TestCase):
    def test_metrics_on_known_errors(self):
        rows = [
            {"errorMW": 10},
            {"errorMW": -10},
            {"errorMW": 20},
        ]
        metrics = calculate_metrics(rows)
        self.assertEqual(metrics["count"], 3)
        self.assertAlmostEqual(metrics["maeMW"], 40 / 3)
        self.assertAlmostEqual(metrics["rmseMW"], (200) ** 0.5)
        self.assertAlmostEqual(metrics["biasMW"], 20 / 3)

    def test_hourly_actuals_requires_two_half_hour_rows(self):
        rows = [
            {"deliveryTime": "2026-01-01T00:00:00Z", "generationMW": 100},
            {"deliveryTime": "2026-01-01T00:30:00Z", "generationMW": 140},
            {"deliveryTime": "2026-01-01T01:00:00Z", "generationMW": 200},
        ]
        hourly, summary = hourly_actuals(rows)
        self.assertEqual(hourly["2026-01-01T00:00:00Z"], 120)
        self.assertNotIn("2026-01-01T01:00:00Z", hourly)
        self.assertEqual(summary["incomplete_hours"], {"2026-01-01T01:00:00Z": 1})


if __name__ == "__main__":
    unittest.main()
