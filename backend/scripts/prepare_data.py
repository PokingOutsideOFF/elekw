"""Validate and normalize the January 2026 Elexon raw data."""

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

DELIVERY_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
DELIVERY_END = datetime(2026, 2, 1, tzinfo=timezone.utc)


def parse_timestamp(value: object, field: str, row_number: int) -> datetime:
    """Parse one source timestamp and require timezone-aware input."""
    if not isinstance(value, str):
        raise ValueError(f"Row {row_number}: {field} is not a string")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError(f"Row {row_number}: {field} is not timezone-aware")
    return timestamp.astimezone(timezone.utc)


def format_timestamp(timestamp: datetime) -> str:
    """Serialize a timestamp consistently as a UTC ISO-8601 string."""
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_generation(value: object, row_number: int) -> int | float:
    """Convert a source generation value to an integer or floating-point number."""
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Row {row_number}: generation is not numeric")
    numeric = float(value)
    if numeric.is_integer():
        return int(numeric)
    return numeric


def load_rows(filename: str) -> list[dict]:
    """Load and validate a raw JSON list of row objects."""
    path = RAW_DIR / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise ValueError(f"{path} must contain a JSON list of objects")
    return payload


def interval_report(timestamps: list[datetime], expected_minutes: int) -> dict:
    """Report timestamp continuity, unexpected intervals, and missing gaps."""
    ordered = sorted(set(timestamps))
    expected = timedelta(minutes=expected_minutes)
    gaps = []
    unexpected_intervals = Counter()
    for previous, current in zip(ordered, ordered[1:]):
        delta = current - previous
        if delta != expected:
            unexpected_intervals[str(delta)] += 1
            if delta > expected:
                missing = int(delta.total_seconds() // expected.total_seconds()) - 1
                gaps.append({"after": format_timestamp(previous), "missing_intervals": missing})
    return {
        "unique_timestamps": len(ordered),
        "expected_interval_minutes": expected_minutes,
        "unexpected_interval_counts": dict(unexpected_intervals),
        "gaps": gaps,
    }


def duplicate_report(rows: list[dict], fields: tuple[str, ...]) -> dict:
    """Summarize duplicate groups for the supplied logical key fields."""
    keys = [tuple(row.get(field) for field in fields) for row in rows]
    counts = Counter(keys)
    duplicate_groups = [count for count in counts.values() if count > 1]
    return {
        "key_fields": list(fields),
        "duplicate_groups": len(duplicate_groups),
        "duplicate_rows_beyond_first": sum(count - 1 for count in duplicate_groups),
    }


def prepare_fuelhh(rows: list[dict]) -> tuple[list[dict], dict]:
    """Validate and normalize half-hourly WIND actual-generation rows."""
    required = {"dataset", "publishTime", "startTime", "settlementDate", "settlementPeriod", "fuelType", "generation"}
    actuals = []
    invalid_rows = []
    for row_number, row in enumerate(rows, start=1):
        missing = sorted(required - row.keys())
        if missing:
            invalid_rows.append({"row": row_number, "reason": f"missing fields: {missing}"})
            continue
        try:
            publish_time = parse_timestamp(row["publishTime"], "publishTime", row_number)
            start_time = parse_timestamp(row["startTime"], "startTime", row_number)
            generation = parse_generation(row["generation"], row_number)
        except (TypeError, ValueError) as exc:
            invalid_rows.append({"row": row_number, "reason": str(exc)})
            continue
        if row["fuelType"] != "WIND":
            invalid_rows.append({"row": row_number, "reason": "fuelType is not WIND"})
            continue
        if not DELIVERY_START <= start_time < DELIVERY_END:
            invalid_rows.append({"row": row_number, "reason": "startTime outside delivery period"})
            continue
        actuals.append(
            {
                "deliveryTime": format_timestamp(start_time),
                "publishTime": format_timestamp(publish_time),
                "settlementDate": row["settlementDate"],
                "settlementPeriod": row["settlementPeriod"],
                "fuelType": "WIND",
                "generationMW": generation,
            }
        )
    actuals.sort(key=lambda row: row["deliveryTime"])
    summary = {
        "source_rows": len(rows),
        "output_rows": len(actuals),
        "invalid_rows": invalid_rows,
        "fuel_types": dict(Counter(row.get("fuelType") for row in rows)),
        "delivery_time": interval_report(
            [parse_timestamp(row["deliveryTime"], "deliveryTime", i) for i, row in enumerate(actuals, 1)],
            30,
        ),
        "duplicates": duplicate_report(rows, ("startTime",)),
        "aggregation": "not performed; actuals remain half-hourly",
    }
    return actuals, summary


def prepare_windfor(rows: list[dict]) -> tuple[list[dict], dict]:
    """Validate and normalize hourly forecast rows without selecting a version."""
    required = {"dataset", "publishTime", "startTime", "generation"}
    forecasts = []
    invalid_rows = []
    for row_number, row in enumerate(rows, start=1):
        missing = sorted(required - row.keys())
        if missing:
            invalid_rows.append({"row": row_number, "reason": f"missing fields: {missing}"})
            continue
        try:
            publish_time = parse_timestamp(row["publishTime"], "publishTime", row_number)
            start_time = parse_timestamp(row["startTime"], "startTime", row_number)
            generation = parse_generation(row["generation"], row_number)
        except (TypeError, ValueError) as exc:
            invalid_rows.append({"row": row_number, "reason": str(exc)})
            continue
        if not DELIVERY_START <= start_time < DELIVERY_END:
            invalid_rows.append({"row": row_number, "reason": "startTime outside delivery period"})
            continue
        forecasts.append(
            {
                "deliveryTime": format_timestamp(start_time),
                "publishTime": format_timestamp(publish_time),
                "forecastMW": generation,
            }
        )
    forecasts.sort(key=lambda row: (row["deliveryTime"], row["publishTime"]))
    summary = {
        "source_rows": len(rows),
        "output_rows": len(forecasts),
        "invalid_rows": invalid_rows,
        "delivery_time": interval_report(
            [
                parse_timestamp(row["deliveryTime"], "deliveryTime", i)
                for i, row in enumerate(forecasts, 1)
            ],
            60,
        ),
        "duplicates": duplicate_report(rows, ("startTime", "publishTime")),
        "publication_versions_per_delivery": dict(
            Counter(row["deliveryTime"] for row in forecasts)
        ),
        "forecast_selection": "not performed; all publication versions are preserved",
    }
    return forecasts, summary


def write_json(filename: str, payload: object) -> None:
    """Write one JSON artifact below the processed-data directory."""
    (PROCESSED_DIR / filename).write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def main() -> None:
    """Prepare both January datasets and write normalized outputs and QA data."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    actuals, actual_summary = prepare_fuelhh(load_rows("fuelhh_2026-01.json"))
    forecasts, forecast_summary = prepare_windfor(load_rows("windfor_2026-01.json"))

    write_json("fuelhh_actuals_2026-01.json", actuals)
    write_json("windfor_forecasts_2026-01.json", forecasts)
    quality_summary = {
        "analysis_delivery_period_utc": {
            "from": format_timestamp(DELIVERY_START),
            "to_exclusive": format_timestamp(DELIVERY_END),
        },
        "fuelhh": actual_summary,
        "windfor": forecast_summary,
    }
    write_json("data_quality_summary_2026-01.json", quality_summary)

    print("Saved data/processed/fuelhh_actuals_2026-01.json:", len(actuals), "rows")
    print("Saved data/processed/windfor_forecasts_2026-01.json:", len(forecasts), "rows")
    print("Saved data/processed/data_quality_summary_2026-01.json")
    print("FUELHH invalid rows:", len(actual_summary["invalid_rows"]))
    print("WINDFOR invalid rows:", len(forecast_summary["invalid_rows"]))
    print("FUELHH delivery intervals:", actual_summary["delivery_time"])
    print("WINDFOR delivery intervals:", forecast_summary["delivery_time"])


if __name__ == "__main__":
    main()
