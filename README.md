# WOMS — Weather Observation Management System

**A full-stack platform for capturing surface weather observations, validating them against WMO meteorological rules, encoding them into FM-12 SYNOP messages, decoding raw SYNOP traffic, and exporting validated records to CSV.**

This repository (`SYNOP-Encoder-`) contains the complete system: a FastAPI backend (`woms_backend`) that owns the SYNOP encoding/decoding/validation logic and a React + Vite frontend (`woms_frontend`) that provides the observer-facing web portal.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start (Windows)](#quick-start-windows)
  - [Manual Setup](#manual-setup)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [SYNOP Message Format](#synop-message-format)
- [Validation Engine](#validation-engine)
- [Data Storage &amp; CSV Export](#data-storage--csv-export)
- [Frontend Application](#frontend-application)
- [License](#license)

---

## Overview

WOMS digitizes the workflow of a manual weather observation station. An observer enters raw sensor/manual readings (wind, visibility, cloud, temperature, pressure, rainfall, present/past weather, etc.) through the web portal. The backend then:

1. Normalizes and stores the observation in SQLite.
2. Immediately generates a **FM-12 SYNOP** preview message from the raw data.
3. Runs the data through a rule-based **meteorological validation engine**.
4. On successful validation, marks the record as validated and exports it to CSV (per-observation file + a cumulative rolling file).
5. Optionally decodes raw incoming SYNOP text files in the background via a scheduled job.

It essentially covers the full loop: **capture → encode → validate → store → export**, plus a standalone **decode** path for parsing existing SYNOP bulletins.

## Key Features

- **Station management (CRUD)** — register, edit, activate/deactivate, and delete observing stations with coordinates, elevation, and metadata.
- **Observation intake** — a rich form covering wind, visibility, cloud layers, temperature/humidity, pressure, precipitation, present/past weather, and the optional Section 333 and Section 555 groups (soil/grass temperatures, sunshine, evaporation).
- **SYNOP encoding engine** — assembles a WMO FM-12 compliant SYNOP message (`AAXX`, `YYGGiw`, `IIiii`, `iRixhVV`, `Nddff`, temperature/dew-point/pressure groups, rainfall, present/past weather, cloud groups, and optional sections) with a human-readable group-by-group explanation.
- **SYNOP decoding engine** — parses raw SYNOP text/bulletins back into structured meteorological data, including a batch **auto-decoder** background service that watches an `incoming_synops/` folder and moves processed files to `decoded_synops/`.
- **Two-tier validation**:
  - a fast save-time sanity check (`validate_observation`) for required fields and obvious range errors;
  - a deep, domain-by-domain `SynopValidationEngine` that runs 13 sequential validation passes (header, format, station/sensor, temperature, humidity, pressure, wind, visibility, cloud, weather, rainfall, temporal, and cross-parameter consistency) and returns a structured `ValidationReport` with pass/warning/error counts.
- **CSV export** — automatic per-observation CSV plus a cumulative `all_validated_readings.csv`, with download endpoints for single or bulk export.
- **Meteorological calculators** — dew point (Magnus-Tetens), relative humidity, MSLP from station pressure (hypsometric equation), and wind-speed unit conversion (knots / m/s / km/h).
- **Configurable runtime settings** — theme, default station, unit preferences, Section 333 visibility, and auto-decoder behavior, stored in `synop-config.toml` and editable from the Settings page.
- **Dark/light themed web portal** with dedicated Stations, Observations, New Observation, and Settings pages.

## Architecture

```
┌─────────────────────────┐        REST / JSON        ┌────────────────────────────────┐
│      woms_frontend       │ ─────────────────────────▶│           woms_backend           │
│  React 19 + Vite (SPA)   │◀───────────────────────── │        FastAPI application       │
│  http://localhost:5173   │                            │        http://localhost:8000     │
└─────────────────────────┘                            └────────────────┬─────────────────┘
                                                                          │
                                       ┌──────────────────────────────────┼───────────────────────────────┐
                                       ▼                                  ▼                                ▼
                             SQLite database (woms.db)      SYNOP encoder / decoder engine      Validation engine (13 rule domains)
                             stations · observations        encoders/ · decoders/               validators/engine.py
                                       │                                  │
                                       ▼                                  ▼
                          CSV export service                  Background auto-decoder
                       validated_readings_csv/                 (APScheduler, watches
                                                                  incoming_synops/)
```

## Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) — REST API and ASGI server
- [Pydantic](https://docs.pydantic.dev/) — request/response schema validation
- SQLite (`sqlite3`) — embedded relational storage
- [APScheduler](https://apscheduler.readthedocs.io/) — background auto-decoder scheduling
  

**Frontend**
- [React 19](https://react.dev/) + [Vite](https://vitejs.dev/)
- [lucide-react](https://lucide.dev/) — icon set
- ESLint for linting

## Project Structure

```
SYNOP-Encoder-/
├── run_all.bat                    # Launches backend + frontend together (Windows)
├── run_frontend.bat               # Launches only the frontend
│
├── woms_backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── main_backup.py             # Earlier monolithic version of the backend
│   ├── backend_core.py            # DB access, request cleaning, quick validation, CSV helpers
│   ├── api_routes.py              # All REST route definitions
│   ├── run_backend.bat            # Creates venv, installs deps, runs uvicorn
│   ├── requirements.txt
│   ├── synop-config.toml          # Runtime configuration (theme, units, auto-decoder, ...)
│   ├── BACKEND_WORKFLOW.md        # Detailed internal workflow documentation
│   │
│   ├── calculators/
│   │   └── meteorology.py         # Dew point, RH, MSLP, wind unit conversion
│   ├── config/
│   │   └── settings.py            # Load/save synop-config.toml
│   ├── database/
│   │   └── db.py                  # SQLite connection + schema init
│   ├── encoders/
│   │   ├── synop_encoder.py       # generate_synop_message() wrapper
│   │   └── synop_engine.py        # SynopEncodingEngine — FM-12 group assembly
│   ├── decoders/
│   │   └── synop_decoder.py       # SynopDecoder — parses raw SYNOP text/files
│   ├── models/
│   │   └── schemas.py             # Pydantic models (Station, Observation, ValidationReport, ...)
│   ├── services/
│   │   ├── auto_decoder.py        # Background scheduler that decodes incoming SYNOP files
│   │   └── csv_exporter.py        # Per-observation & cumulative CSV writers
│   ├── validators/
│   │   ├── engine.py              # SynopValidationEngine orchestrator
│   │   ├── header_validator.py
│   │   ├── group_format_validator.py
│   │   ├── sensor_validator.py
│   │   ├── temperature_validator.py
│   │   ├── humidity_validator.py
│   │   ├── pressure_validator.py
│   │   ├── wind_validator.py
│   │   ├── visibility_validator.py
│   │   ├── cloud_validator.py
│   │   ├── weather_validator.py
│   │   ├── rainfall_validator.py
│   │   ├── temporal_validator.py
│   │   ├── cross_parameter_validator.py
│   │   ├── wmo_code_tables.py      # WMO code table lookups
│   │   └── models.py               # ValidationResult / ValidationReport dataclasses
│   ├── validated_readings_csv/     # Auto-generated CSV export output
│   └── woms.db                     # SQLite database file
│
└── woms_frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── eslint.config.js
    ├── public/                     # favicon, icons
    └── src/
        ├── main.jsx                # React entry point
        ├── App.jsx                 # Page router + theme handling
        ├── App.css / index.css     # Styling
        ├── components/
        │   └── Sidebar.jsx         # Navigation (Stations, Observations, New Observation, Settings)
        ├── pages/
        │   ├── Stations.jsx        # Station CRUD UI
        │   ├── Observations.jsx    # Observation list, filters, detail view, CSV download
        │   ├── NewObservation.jsx  # Full observation entry form + SYNOP preview
        │   └── Settings.jsx        # Runtime configuration UI
        └── assets/
```

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- Windows is the primary supported environment for the provided `.bat` launcher scripts (backend/frontend can also be run manually on macOS/Linux — see below).

### Quick Start (Windows)

From the repository root:

```bat
run_all.bat
```

This opens two terminal windows: one that creates/activates a Python virtual environment, installs backend dependencies, and starts the FastAPI server; and one that starts the Vite dev server for the frontend.

- Backend API + docs: **http://localhost:8000/docs**
- Frontend portal: **http://localhost:5173**

### Manual Setup

**1. Backend**

```bash
cd woms_backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The backend auto-creates and seeds `woms.db` (stations + a default observation) on first run.

**2. Frontend**

```bash
cd woms_frontend
npm install
npm run dev
```

The dev server starts on **http://localhost:5173** and talks to the backend at `http://localhost:8000`.

> Note: the frontend currently calls the backend via a hardcoded `http://localhost:8000` base URL, so both services need to run on those default ports for the portal to work out of the box.

## Configuration

Runtime settings live in `woms_backend/synop-config.toml` and are readable/writable via `GET /api/settings/` and `POST /api/settings/` (also editable from the **Settings** page in the UI):

```toml
[general]
theme = "dark"
colors = { primary = "#4facfe", secondary = "#00f2fe" }

[station]
default_station = "43279"
filter_active_only = true

[units]
wind_unit = "knots"        # "knots" or "m/s"
show_section_333 = true

[auto_decoder]
enabled = true
interval_seconds = 60
input_folder = "./incoming_synops"
output_folder = "./decoded_synops"

[storage]
file_naming_format = "{station}_{YYYYMMDD}_{HH}.txt"
```

When `auto_decoder.enabled` is `true`, a background `BackgroundScheduler` job periodically scans `input_folder` for `.txt` files, decodes any SYNOP blocks found, and moves processed files into `output_folder`.

## API Reference

All endpoints are served from the FastAPI app (`woms_backend/main.py` + `api_routes.py`). Interactive Swagger docs are available at `/docs` once the backend is running.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stations/` | List all stations |
| `POST` | `/api/stations/` | Create a station |
| `GET` | `/api/stations/{id}/` | Get a single station |
| `PUT` | `/api/stations/{id}/` | Update a station |
| `DELETE` | `/api/stations/{id}/` | Delete a station |
| `GET` | `/api/observations/` | List observations (filter by `station`, `date`, `email_status`) |
| `POST` | `/api/observations/` | Create an observation (validates + generates SYNOP if `is_validated=true`) |
| `GET` | `/api/observations/{id}/` | Get a single observation |
| `POST` | `/api/observations/{id}/validate_obs/` | Run full validation, mark as validated, export to CSV |
| `GET` | `/api/observations/{id}/csv/` | Download a single observation as CSV |
| `GET` | `/api/observations/csv/all/` | Download all (or all validated) observations as CSV |
| `POST` | `/api/synop/preview/` | Generate a SYNOP preview without saving |
| `POST` | `/api/synop/decode/` | Decode a raw SYNOP message string (body) |
| `GET` | `/api/synop/decode/` | Decode a raw SYNOP message string (query param) |
| `GET` | `/api/settings/` | Read current `synop-config.toml` settings |
| `POST` | `/api/settings/` | Update settings |

## SYNOP Message Format

The encoder (`encoders/synop_engine.py`, wrapped by `encoders/synop_encoder.py`) assembles a WMO FM-12 style message from the observation payload, group by group:

1. `AAXX` — message type indicator
2. `YYGGiw` — day, hour, wind indicator
3. `IIiii` — WMO station number
4. `iRixhVV` — precipitation/weather indicators, visibility
5. `Nddff` — cloud cover, wind direction/speed
6. `1snTTT` — air temperature
7. `2snTdTdTd` — dew-point temperature
8. `3P0P0P0P0` — station pressure
9. `4PPPP` — mean sea level pressure
10. `5appp` — pressure tendency
11. `6RRRtR` — precipitation amount
12. `7wwW1W2` — present/past weather
13. `8NhCLCMCH` — cloud type/height groups
14. Optional `333` and `555` sections — supplementary data (e.g. max/min temperature, sunshine, evaporation, soil and grass temperatures)

Every generated message is returned alongside a human-readable **explanation map** for each group, which the frontend surfaces in the observation preview.

The counterpart `decoders/synop_decoder.py` (`SynopDecoder`) parses raw SYNOP text — including whole bulletin files containing multiple `AAXX ... =` blocks — back into structured fields.

## Validation Engine

Two validation layers exist side by side:

- **Quick validation** (`validate_observation` in `backend_core.py`) — runs automatically when an observation is saved with `is_validated=true`. Checks required fields, wind sanity, visibility range, cloud amount range, temperature sanity, pressure range, and non-negative rainfall. Returns HTTP 400 with error details if it fails.
- **Deep validation engine** (`validators/engine.py` — `SynopValidationEngine`) — the formal WMO-style rule system, invoked from `POST /api/observations/{id}/validate_obs/`. It runs 13 sequential validation domains (header, group format, station/sensor, temperature, humidity, pressure, wind, visibility, cloud, weather, rainfall, temporal consistency, cross-parameter consistency) using dedicated validator modules, and produces a structured `ValidationReport` with total/passed/warning/error counts and a per-check breakdown (`ValidationResultSchema`).

See [`woms_backend/BACKEND_WORKFLOW.md`](woms_backend/BACKEND_WORKFLOW.md) for a full walkthrough of the request lifecycle, from intake to CSV export.

## Data Storage & CSV Export

- **SQLite (`woms.db`)** holds two core tables:
  - `stations` — station number, name, coordinates, elevation, contact email, type, active flag.
  - `observations` — the full meteorological payload plus `is_validated`, `generated_synop`, and `email_status` (`pending` / `sent`).
- **CSV export** (`services/csv_exporter.py`) writes to `woms_backend/validated_readings_csv/`:
  - one file per validated observation, named `Observation_<station>_<date>_<time>_id<id>.csv`;
  - a cumulative `all_validated_readings.csv` that every validated record is appended to.
- Bulk CSV download is also available on demand via `GET /api/observations/csv/all/`, filterable by station and date.

## Frontend Application

The React portal (`woms_frontend`) is a single-page app with four sections, navigated via the sidebar:

- **Stations** — add, edit, and remove observing stations.
- **Observations** — browse recorded observations with station/date/status filters, view details, trigger validation, and download CSVs.
- **New Observation** — the full data-entry form for a fresh observation, including live SYNOP preview.
- **Settings** — edit runtime configuration (theme, units, default station, auto-decoder options) backed by `synop-config.toml`.

The UI supports a **dark/light theme toggle**, persisted to `localStorage`.

## License

No license file is currently included in this repository. Until one is added, all rights are reserved by default — consider adding a license (e.g. MIT, Apache-2.0) if you intend for others to reuse this code.
