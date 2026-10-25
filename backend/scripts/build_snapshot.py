"""Build the read-only SQLite snapshot used by the FastAPI application."""

import json
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SNAPSHOT_PATH = PROJECT_ROOT / "data" / "snapshot.sqlite"


def load_json(filename: str) -> object:
    """Load one processed JSON artifact from the project data directory."""

    return json.loads((PROCESSED_DIR / filename).read_text(encoding="utf-8"))


def create_schema(connection: sqlite3.Connection) -> None:
    """Create the normalized snapshot tables and useful query indexes."""

    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE actuals (
            delivery_time TEXT PRIMARY KEY,
            publish_time TEXT NOT NULL,
            settlement_date TEXT NOT NULL,
            settlement_period INTEGER NOT NULL,
            fuel_type TEXT NOT NULL,
            generation_mw REAL NOT NULL
        );

        CREATE TABLE forecasts (
            delivery_time TEXT NOT NULL,
            publish_time TEXT NOT NULL,
            forecast_mw REAL NOT NULL,
            horizon_hours REAL NOT NULL,
            PRIMARY KEY (delivery_time, publish_time)
        );
        CREATE INDEX forecasts_delivery_idx ON forecasts(delivery_time);
        CREATE INDEX forecasts_publish_idx ON forecasts(publish_time);

        CREATE TABLE decision_forecasts (
            delivery_time TEXT PRIMARY KEY,
            decision_cutoff TEXT NOT NULL,
            selected_publish_time TEXT,
            forecast_mw REAL,
            forecast_horizon_hours REAL,
            selection_status TEXT NOT NULL
        );

        CREATE TABLE joined_accuracy (
            delivery_time TEXT PRIMARY KEY,
            forecast_mw REAL NOT NULL,
            actual_mw REAL NOT NULL,
            selected_publish_time TEXT NOT NULL,
            decision_cutoff TEXT NOT NULL,
            forecast_horizon_hours REAL NOT NULL,
            error_mw REAL NOT NULL,
            absolute_error_mw REAL NOT NULL
        );
        CREATE INDEX accuracy_delivery_idx ON joined_accuracy(delivery_time);

        CREATE TABLE artifacts (
            name TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL
        );
        """
    )


def build_snapshot() -> Path:
    """Load processed artifacts and rebuild the complete SQLite snapshot."""

    actuals = load_json("fuelhh_actuals_2026-01.json")
    forecasts = load_json("windfor_forecasts_2026-01.json")
    decision_forecasts = load_json("day_ahead_forecasts_2026-01.json")
    accuracy_rows = load_json("accuracy_timeseries_2026-01.json")
    summary = load_json("accuracy_summary_2026-01.json")
    breakdown = load_json("accuracy_breakdown_2026-01.json")

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SNAPSHOT_PATH.exists():
        SNAPSHOT_PATH.unlink()
    with sqlite3.connect(SNAPSHOT_PATH) as connection:
        create_schema(connection)
        connection.executemany(
            "INSERT INTO actuals VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    row["deliveryTime"], row["publishTime"], row["settlementDate"],
                    row["settlementPeriod"], row["fuelType"], row["generationMW"],
                )
                for row in actuals
            ],
        )
        # Horizon is stored explicitly because it is a key decision-support field.
        connection.executemany(
            "INSERT INTO forecasts VALUES (?, ?, ?, ?)",
            [
                (
                    row["deliveryTime"],
                    row["publishTime"],
                    row["forecastMW"],
                    (parse_timestamp(row["deliveryTime"]) - parse_timestamp(row["publishTime"])).total_seconds() / 3600,
                )
                for row in forecasts
            ],
        )
        connection.executemany(
            "INSERT INTO decision_forecasts VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    row["deliveryTime"], row["decisionCutoff"], row["selectedPublishTime"],
                    row["forecastMW"], row["forecastHorizonHours"], row["selectionStatus"],
                )
                for row in decision_forecasts
            ],
        )
        connection.executemany(
            "INSERT INTO joined_accuracy VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["deliveryTime"], row["forecastMW"], row["actualMW"],
                    row["selectedPublishTime"], row["decisionCutoff"],
                    row["forecastHorizonHours"], row["errorMW"], row["absoluteErrorMW"],
                )
                for row in accuracy_rows
            ],
        )
        connection.executemany(
            "INSERT INTO artifacts VALUES (?, ?)",
            [
                ("accuracy_summary", json.dumps(summary)),
                ("accuracy_breakdown", json.dumps(breakdown)),
            ],
        )
        connection.commit()
    return SNAPSHOT_PATH


def parse_timestamp(value: str):
    """Parse an ISO timestamp while preserving UTC-aware arithmetic."""

    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> None:
    """Build the snapshot and print its table row counts."""

    path = build_snapshot()
    with sqlite3.connect(path) as connection:
        for table in ("actuals", "forecasts", "decision_forecasts", "joined_accuracy"):
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count} rows")
    print(f"Saved SQLite snapshot to {path}")


if __name__ == "__main__":
    main()
