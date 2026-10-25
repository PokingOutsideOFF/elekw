"""FastAPI application for the UK wind forecast prototype."""

import json
import os
import sqlite3
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = PROJECT_ROOT / "data" / "snapshot.sqlite"

app = FastAPI(title="UK Wind Forecast API", version="0.1.0")
configured_origins = os.getenv("CORS_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        *[origin.strip() for origin in configured_origins if origin.strip()],
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_connection() -> sqlite3.Connection:
    """Open the read-only SQLite snapshot with dictionary-like rows."""

    if not SNAPSHOT_PATH.exists():
        raise HTTPException(status_code=503, detail="SQLite data snapshot is unavailable")
    connection = sqlite3.connect(f"file:{SNAPSHOT_PATH}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def requested_date_filter(
    from_date: date | None,
    to_date: date | None,
) -> tuple[date | None, date | None]:
    """Validate an optional inclusive ISO date range for API filtering."""

    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be on or before to_date")
    return from_date, to_date


def query_delivery_rows(
    table: str,
    select_clause: str,
    from_date: date | None,
    to_date: date | None,
) -> list[dict]:
    """Query a snapshot table with an inclusive UTC delivery-date filter."""

    conditions = []
    values: list[str] = []
    if from_date:
        conditions.append("substr(delivery_time, 1, 10) >= ?")
        values.append(from_date.isoformat())
    if to_date:
        conditions.append("substr(delivery_time, 1, 10) <= ?")
        values.append(to_date.isoformat())
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT {select_clause} FROM {table}{where} ORDER BY delivery_time",
            values,
        ).fetchall()
    return [dict(row) for row in rows]


def load_artifact(name: str) -> object:
    """Load a precomputed JSON artifact stored inside the SQLite snapshot."""

    with get_connection() as connection:
        row = connection.execute("SELECT payload_json FROM artifacts WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise HTTPException(status_code=503, detail=f"Snapshot artifact is unavailable: {name}")
    return json.loads(row["payload_json"])


@app.get("/health")
def health() -> dict:
    """Return a lightweight service and data-availability health response."""

    return {
        "status": "ok",
        "dataAvailable": SNAPSHOT_PATH.exists(),
    }


@app.get("/api/decision")
def decision(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
) -> dict:
    """Return selected day-ahead forecasts for an optional delivery-date range."""

    from_date, to_date = requested_date_filter(from_date, to_date)
    rows = query_delivery_rows(
        "decision_forecasts",
        "delivery_time AS deliveryTime, decision_cutoff AS decisionCutoff, "
        "selected_publish_time AS selectedPublishTime, forecast_mw AS forecastMW, "
        "forecast_horizon_hours AS forecastHorizonHours, selection_status AS selectionStatus",
        from_date,
        to_date,
    )
    return {"count": len(rows), "data": rows}


@app.get("/api/accuracy/summary")
def accuracy_summary() -> dict:
    """Return headline accuracy metrics and coverage information."""

    return load_artifact("accuracy_summary")


@app.get("/api/accuracy/timeseries")
def accuracy_timeseries(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
) -> dict:
    """Return matched forecast/actual observations for an optional date range."""

    from_date, to_date = requested_date_filter(from_date, to_date)
    rows = query_delivery_rows(
        "joined_accuracy",
        "delivery_time AS deliveryTime, forecast_mw AS forecastMW, actual_mw AS actualMW, "
        "selected_publish_time AS selectedPublishTime, decision_cutoff AS decisionCutoff, "
        "forecast_horizon_hours AS forecastHorizonHours, error_mw AS errorMW, "
        "absolute_error_mw AS absoluteErrorMW",
        from_date,
        to_date,
    )
    return {"count": len(rows), "data": rows}


@app.get("/api/accuracy/breakdown")
def accuracy_breakdown() -> dict:
    """Return metrics grouped by UTC delivery hour."""

    return load_artifact("accuracy_breakdown")
