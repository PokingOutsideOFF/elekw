"""Calculate forecast accuracy from selected forecasts and half-hourly actuals."""

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROCESSED_DIR = Path("data/processed")
DELIVERY_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
DELIVERY_END = datetime(2026, 2, 1, tzinfo=timezone.utc)


def parse_timestamp(value: str) -> datetime:
    """Parse a timezone-aware ISO-8601 timestamp and normalize it to UTC."""

    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError(f"Timestamp must be timezone-aware: {value}")
    return timestamp.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    """Serialize a timestamp consistently as UTC ISO-8601 text."""

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def hourly_actuals(actual_rows: list[dict]) -> tuple[dict[str, float], dict]:
    """Aggregate two half-hour actual MW observations into hourly means.

    This explicit mean assumes FUELHH generation is average MW for each equal
    half-hour interval. The assumption is recorded in the output metadata.
    """

    grouped: dict[str, list[float]] = defaultdict(list)
    for row in actual_rows:
        delivery_time = parse_timestamp(row["deliveryTime"])
        hour = delivery_time.replace(minute=0, second=0, microsecond=0)
        grouped[format_timestamp(hour)].append(float(row["generationMW"]))

    hourly = {
        delivery_time: sum(values) / len(values)
        for delivery_time, values in grouped.items()
        if len(values) == 2
    }
    incomplete = {
        delivery_time: len(values)
        for delivery_time, values in grouped.items()
        if len(values) != 2
    }
    return hourly, {
        "source_half_hour_rows": len(actual_rows),
        "hourly_actual_rows": len(hourly),
        "incomplete_hours": incomplete,
        "aggregation": "mean of two equal half-hour generation values",
    }


def build_accuracy_timeseries(
    actual_rows: list[dict], selected_rows: list[dict]
) -> tuple[list[dict], dict]:
    """Join selected forecasts to matching hourly actuals and calculate errors."""

    actuals, actual_summary = hourly_actuals(actual_rows)
    timeseries = []
    missing_actuals = []
    missing_forecasts = []
    for selected in selected_rows:
        delivery_time = selected["deliveryTime"]
        if selected.get("selectionStatus") != "selected":
            missing_forecasts.append(delivery_time)
            continue
        if delivery_time not in actuals:
            missing_actuals.append(delivery_time)
            continue
        forecast = float(selected["forecastMW"])
        actual = actuals[delivery_time]
        error = forecast - actual
        timeseries.append(
            {
                "deliveryTime": delivery_time,
                "forecastMW": forecast,
                "actualMW": actual,
                "selectedPublishTime": selected["selectedPublishTime"],
                "decisionCutoff": selected["decisionCutoff"],
                "forecastHorizonHours": selected["forecastHorizonHours"],
                "errorMW": error,
                "absoluteErrorMW": abs(error),
            }
        )
    timeseries.sort(key=lambda row: row["deliveryTime"])
    return timeseries, {
        "actuals": actual_summary,
        "selected_forecast_rows": len(selected_rows),
        "matched_rows": len(timeseries),
        "missing_actuals": missing_actuals,
        "missing_forecasts": missing_forecasts,
    }


def percentile(values: list[float], quantile: float) -> float | None:
    """Return a linearly interpolated percentile, or null for no values."""

    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def calculate_metrics(rows: list[dict]) -> dict:
    """Calculate headline error metrics for matched forecast/actual rows."""

    errors = [float(row["errorMW"]) for row in rows]
    absolute_errors = [abs(error) for error in errors]
    count = len(errors)
    return {
        "count": count,
        "maeMW": sum(absolute_errors) / count if count else None,
        "rmseMW": math.sqrt(sum(error * error for error in errors) / count) if count else None,
        "biasMW": sum(errors) / count if count else None,
        "absoluteErrorP50MW": percentile(absolute_errors, 0.50),
        "absoluteErrorP90MW": percentile(absolute_errors, 0.90),
        "absoluteErrorP95MW": percentile(absolute_errors, 0.95),
        "normalizedMae": None,
        "normalizedMaeNote": "Not calculated until a denominator is defined.",
    }


def breakdown_by_hour(rows: list[dict]) -> list[dict]:
    """Calculate metrics grouped by UTC delivery hour."""

    groups: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        groups[parse_timestamp(row["deliveryTime"]).hour].append(row)
    return [
        {"deliveryHourUtc": hour, **calculate_metrics(groups[hour])}
        for hour in sorted(groups)
    ]


def main() -> None:
    """Load prepared data and write accuracy timeseries, summary, and breakdown."""

    actuals = json.loads((PROCESSED_DIR / "fuelhh_actuals_2026-01.json").read_text(encoding="utf-8"))
    selected = json.loads((PROCESSED_DIR / "day_ahead_forecasts_2026-01.json").read_text(encoding="utf-8"))
    timeseries, join_summary = build_accuracy_timeseries(actuals, selected)
    summary = {
        "analysis_delivery_period_utc": {
            "from": format_timestamp(DELIVERY_START),
            "to_exclusive": format_timestamp(DELIVERY_END),
        },
        "errorConvention": "forecastMW - actualMW",
        "metrics": calculate_metrics(timeseries),
        "join": join_summary,
    }
    breakdown = {"byDeliveryHourUtc": breakdown_by_hour(timeseries)}
    (PROCESSED_DIR / "accuracy_timeseries_2026-01.json").write_text(json.dumps(timeseries, indent=2), encoding="utf-8")
    (PROCESSED_DIR / "accuracy_summary_2026-01.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (PROCESSED_DIR / "accuracy_breakdown_2026-01.json").write_text(json.dumps(breakdown, indent=2), encoding="utf-8")
    print("Matched rows:", len(timeseries))
    print("Metrics:", json.dumps(summary["metrics"], indent=2))
    print("Saved accuracy outputs under data/processed/")


if __name__ == "__main__":
    main()
