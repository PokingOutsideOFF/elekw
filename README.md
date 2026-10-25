 # UK Wind Forecast Decision Support

A React + FastAPI pilot for a UK energy utility buying electricity in the day-ahead market. It uses national wind generation data from Elexon BMRS to show the forecast available at the purchasing cutoff and quantify forecast accuracy.

## Requirements covered

- Elexon `FUELHH` actuals filtered to `fuelType=WIND`.
- Elexon `WINDFOR` forecasts using delivery time, publication time, and generation.
- January 2026 delivery scope.
- Latest forecast available at or before 09:00 UK time on the previous local calendar day.
- Forecast, actual, signed error, and forecast horizon in the day-ahead view.
- MAE, RMSE, bias, P90 error, hover chart, horizon filtering, UTC-hour/horizon breakdowns, CSV export, pagination, and plain-language metric explanations.
- React frontend, Python/FastAPI backend, automated tests, Docker, and a deployable SQLite snapshot.

## Data methodology

Actuals arrive every 30 minutes. Because the WINDFOR sample is hourly, the two half-hour actual values are averaged for each hourly comparison. Error is `forecast - actual`. The selection logic excludes forecast publications after the stated decision cutoff to avoid hindsight bias.

The committed `data/snapshot.sqlite` is a bounded, read-only application snapshot, so the application runs without API credentials or live API calls. Raw and intermediate JSON files are ignored by Git. The pipeline in `backend/scripts/` can regenerate the snapshot.

## Repository structure

```text
backend/app/main.py       FastAPI endpoints and SQLite queries
backend/scripts/           Download, prepare, select, score, and snapshot pipeline
backend/tests/             Unit and API tests
data/snapshot.sqlite       Bounded application data snapshot
frontend/src/              React, Tailwind, Lucide, and shadcn-style UI
backend/Dockerfile         FastAPI production image
frontend/Dockerfile        React/Nginx production image
frontend/nginx.conf        SPA fallback and backend proxy
docker-compose.yml         Two-service review environment
vercel.json                Frontend Vercel configuration
```

## Run locally

Backend, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn backend.app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The API is at `http://127.0.0.1:8000`, with Swagger at `/docs`.

## Tests and build

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m pytest backend/tests
cd frontend
npm run build
```

## Docker review environment

```powershell
docker compose up --build
```

Open `http://localhost:8080`. The frontend container serves the production React build and proxies `/api` to the FastAPI container. Stop it with `docker compose down`.

## Regenerate data

```powershell
python backend/scripts/download_data.py
python backend/scripts/prepare_data.py
python backend/scripts/select_forecasts.py
python backend/scripts/calculate_accuracy.py
python backend/scripts/build_snapshot.py
```

The downloader requires network access to Elexon. Generated raw and processed JSON files are deliberately excluded from Git; the SQLite snapshot is the deployable artifact.

## Public links

- Frontend application: https://elekw.vercel.app/
- Backend API: https://uk-wind-forecast-api-6bfd.onrender.com

## AI tools

AI-assisted development using Codex was done for API exploration, code scaffolding, UI iteration, documentation, and test/debug assistance. Generated code was reviewed, adapted, and verified with tests and build checks.

## Limitations

This is a decision-support pilot, not a complete procurement optimiser. It excludes demand, prices, imbalance costs, plant constraints, and other generation types. WINDFOR is hourly in the supplied sample; FUELHH actuals are averaged to hourly values for comparison. A production system should add scheduled ingestion, managed storage, authentication, observability, and a configurable decision rule.
