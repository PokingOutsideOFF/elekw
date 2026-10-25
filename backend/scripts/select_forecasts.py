"""Select the latest WINDFOR forecast available at a decision cutoff."""

import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


PROCESSED_DIR = Path("data/processed")
OUTPUT_PATH = PROCESSED_DIR / "day_ahead_forecasts_2026-01.json"
DEFAULT_CUTOFF_HOUR = 9
DEFAULT_TIMEZONE = "Europe/London"


def parse_timestamp(value: str) -> datetime:
    """Parse a UTC ISO-8601 string into a timezone-aware datetime."""

    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError(f"Timestamp must be timezone-aware: {value}")
    return timestamp.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    """Serialize a datetime as a UTC ISO-8601 string."""

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def decision_cutoff_for_delivery(
    delivery_time: datetime,
    cutoff_hour: int = DEFAULT_CUTOFF_HOUR,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> datetime:
    """Return the previous local calendar day's configurable cutoff in UTC.

    The delivery timestamp is converted to the requested local timezone before
    subtracting one calendar day, which keeps date-boundary and DST behavior
    correct. The default is 09:00 Europe/London on the previous local day.
    """

    if not 0 <= cutoff_hour <= 23:
        raise ValueError("cutoff_hour must be between 0 and 23")
    local_delivery = delivery_time.astimezone(ZoneInfo(timezone_name))
    previous_local_date = local_delivery.date() - timedelta(days=1)
    local_cutoff = datetime.combine(
        previous_local_date,
        time(hour=cutoff_hour),
        tzinfo=ZoneInfo(timezone_name),
    )
    return local_cutoff.astimezone(timezone.utc)


def select_latest_eligible_forecast(
    delivery_time: datetime,
    forecasts: list[dict],
    cutoff_hour: int = DEFAULT_CUTOFF_HOUR,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> dict:
    """Select the latest forecast for one target published by its cutoff.

    Forecasts published after the cutoff are excluded. If no eligible version
    exists, the returned row is marked ``missing`` with a null forecast value.
    """

    cutoff = decision_cutoff_for_delivery(delivery_time, cutoff_hour, timezone_name)
    eligible = []
    for forecast in forecasts:
        if parse_timestamp(forecast["deliveryTime"]) != delivery_time:
            continue
        publish_time = parse_timestamp(forecast["publishTime"])
        if publish_time <= cutoff:
            eligible.append((publish_time, forecast))

    result = {
        "deliveryTime": format_timestamp(delivery_time),
        "decisionCutoff": format_timestamp(cutoff),
        "selectedPublishTime": None,
        "forecastMW": None,
        "forecastHorizonHours": None,
        "selectionStatus": "missing",
    }
    if eligible:
        selected_publish_time, selected = max(eligible, key=lambda item: item[0])
        result.update(
            {
                "selectedPublishTime": format_timestamp(selected_publish_time),
                "forecastMW": selected["forecastMW"],
                "forecastHorizonHours": round(
                    (delivery_time - selected_publish_time).total_seconds() / 3600,
                    3,
                ),
                "selectionStatus": "selected",
            }
        )
    return result


def select_day_ahead_forecasts(
    forecasts: list[dict],
    cutoff_hour: int = DEFAULT_CUTOFF_HOUR,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> list[dict]:
    """Select one auditable forecast row for every unique delivery target."""

    delivery_times = sorted(
        {parse_timestamp(row["deliveryTime"]) for row in forecasts}
    )
    return [
        select_latest_eligible_forecast(
            delivery_time, forecasts, cutoff_hour, timezone_name
        )
        for delivery_time in delivery_times
    ]


def main() -> None:
    """Load prepared forecast history and save day-ahead selections."""

    source_path = PROCESSED_DIR / "windfor_forecasts_2026-01.json"
    forecasts = json.loads(source_path.read_text(encoding="utf-8"))
    selected = select_day_ahead_forecasts(forecasts)
    OUTPUT_PATH.write_text(json.dumps(selected, indent=2), encoding="utf-8")
    selected_count = sum(row["selectionStatus"] == "selected" for row in selected)
    print(f"Saved {len(selected)} delivery targets to {OUTPUT_PATH}")
    print(f"Selected forecasts: {selected_count}")
    print(f"Missing forecasts: {len(selected) - selected_count}")


if __name__ == "__main__":
    main()
