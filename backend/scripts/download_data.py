"""Download the raw January 2026 wind analysis data from Elexon BMRS."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
DATA_DIR = Path("data/raw")

DELIVERY_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
DELIVERY_END = datetime(2026, 2, 1, tzinfo=timezone.utc)

# WINDFOR publication history starts well before the January delivery period
# so that the forecast available at an assumed previous-day cutoff is present.
WINDFOR_PUBLISH_START = datetime(2025, 12, 1, tzinfo=timezone.utc)
WINDFOR_PUBLISH_END = DELIVERY_END

# FUELHH is filtered by publishTime, which is approximately one interval after
# startTime. These bounds include every January delivery interval and the
# publication boundary needed for the final 23:30 delivery.
FUELHH_PUBLISH_START = DELIVERY_START
FUELHH_PUBLISH_END = DELIVERY_END


def as_api_time(value: datetime) -> str:
    """Format a timezone-aware timestamp as the UTC API time string."""

    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_rows(payload: object) -> list[dict]:
    """Extract row objects from a list response or a ``data`` envelope."""

    if isinstance(payload, dict):
        rows = payload.get("data", [])
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError(f"Unexpected response type: {type(payload)}")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("Response data is not a list of objects")
    return rows


def fetch_publication_days(
    dataset: str,
    publish_start: datetime,
    publish_end: datetime,
) -> tuple[list[dict], list[dict]]:
    """Fetch daily publication windows and return rows plus request failures.

    Daily windows keep responses bounded and make failed time ranges explicit.
    Adjacent windows may overlap because the API bounds can be inclusive; the
    caller removes duplicate rows after all requests complete.
    """

    rows: list[dict] = []
    failures: list[dict] = []
    current = publish_start

    while current <= publish_end:
        window_end = min(current + timedelta(days=1), publish_end)
        params = {
            "publishDateTimeFrom": as_api_time(current),
            "publishDateTimeTo": as_api_time(window_end),
        }
        if dataset == "FUELHH":
            params["fuelType"] = "WIND"

        url = f"{BASE_URL}/datasets/{dataset}/stream"
        print(f"Fetching {dataset}: {params['publishDateTimeFrom']} to {params['publishDateTimeTo']}")
        try:
            response = requests.get(url, params=params, timeout=60)
            print(f"  HTTP {response.status_code}; URL: {response.url}")
            response.raise_for_status()
            day_rows = extract_rows(response.json())
            print(f"  rows: {len(day_rows)}")
            rows.extend(day_rows)
        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            failure = {"dataset": dataset, **params, "error": str(exc)}
            failures.append(failure)
            print(f"  FAILED: {exc}")

        current = window_end
        if current == publish_end:
            break

    return rows, failures


def row_key(row: dict) -> tuple:
    """Build a stable full-row key for deduplicating boundary overlaps."""

    return tuple(row.get(field) for field in sorted(row))


def unique_rows(rows: list[dict]) -> list[dict]:
    """Remove duplicate full rows while preserving source order."""

    seen: set[tuple] = set()
    result: list[dict] = []
    for row in rows:
        key = row_key(row)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def parse_api_time(value: str) -> datetime:
    """Parse an Elexon ISO-8601 timestamp into an aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def in_delivery_period(row: dict) -> bool:
    """Return whether a row's delivery target falls in January 2026."""
    start_time = row.get("startTime")
    if not start_time:
        return False
    delivery_time = parse_api_time(start_time)
    return DELIVERY_START <= delivery_time < DELIVERY_END


def main() -> None:
    """Download, filter, and save January raw data plus a coverage manifest."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    fuel_rows, fuel_failures = fetch_publication_days(
        "FUELHH", FUELHH_PUBLISH_START, FUELHH_PUBLISH_END
    )
    wind_rows, wind_failures = fetch_publication_days(
        "WINDFOR", WINDFOR_PUBLISH_START, WINDFOR_PUBLISH_END
    )

    fuel_rows = [row for row in unique_rows(fuel_rows) if in_delivery_period(row)]
    wind_rows = [row for row in unique_rows(wind_rows) if in_delivery_period(row)]

    outputs = {
        "fuelhh_2026-01.json": fuel_rows,
        "windfor_2026-01.json": wind_rows,
    }
    for filename, rows in outputs.items():
        output_path = DATA_DIR / filename
        output_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"Saved {len(rows)} rows to {output_path}")

    manifest = {
        "analysis_delivery_period_utc": {
            "from": as_api_time(DELIVERY_START),
            "to_exclusive": as_api_time(DELIVERY_END),
        },
        "requests": {
            "FUELHH": {
                "publish_from": as_api_time(FUELHH_PUBLISH_START),
                "publish_to": as_api_time(FUELHH_PUBLISH_END),
                "fuelType": "WIND",
            },
            "WINDFOR": {
                "publish_from": as_api_time(WINDFOR_PUBLISH_START),
                "publish_to": as_api_time(WINDFOR_PUBLISH_END),
            },
        },
        "row_counts": {filename: len(rows) for filename, rows in outputs.items()},
        "failures": fuel_failures + wind_failures,
        "notes": [
            "Requests are split into one-day publish-time windows.",
            "Rows are deduplicated because API time bounds may be inclusive.",
            "WINDFOR publication history begins 2025-12-01 to support cutoff analysis.",
            "The proposed previous-day 09:00 UK cutoff remains an unverified assumption.",
        ],
    }
    manifest_path = DATA_DIR / "january_2026_download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved manifest to {manifest_path}")


if __name__ == "__main__":
    main()
