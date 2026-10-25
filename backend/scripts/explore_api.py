
import json
from pathlib import Path

import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def inspect_dataset(
    dataset: str,
    start: str,
    end: str,
    fuel_type: str | None = None,
) -> None:
    """Fetch a small sample and inspect its response structure."""

    url = f"{BASE_URL}/datasets/{dataset}/stream"

    params = {
        "publishDateTimeFrom": start,
        "publishDateTimeTo": end,
    }
    if fuel_type is not None:
        params["fuelType"] = fuel_type

    print(f"\nFetching {dataset}...")
    response = requests.get(url, params=params, timeout=60)

    print("URL:", response.url)
    print("HTTP status:", response.status_code)
    response.raise_for_status()

    payload = response.json()

    # Inspect the response before assuming it is a list or dictionary.
    if isinstance(payload, dict):
        rows = payload.get("data", [])
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError(f"Unexpected response type: {type(payload)}")

    print("Number of returned records:", len(rows))

    if rows:
        print("Available fields:", list(rows[0].keys()))
        print("First record:")
        print(json.dumps(rows[0], indent=2))

    output_path = DATA_DIR / f"{dataset.lower()}_sample.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("Saved response to:", output_path)


if __name__ == "__main__":
    # A small initial sample to inspect the API.
    inspect_dataset(
        "FUELHH",
        "2026-01-01T00:00:00Z",
        "2026-01-02T00:00:00Z",
        "WIND"
    )

    inspect_dataset(
        "WINDFOR",
        "2025-12-30T00:00:00Z",
        "2025-12-31T00:00:00Z",
    )
