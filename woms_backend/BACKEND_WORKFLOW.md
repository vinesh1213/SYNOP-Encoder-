# WOMS Backend Workflow

This document explains how the backend of the Weather Observation Management System works from startup to final storage and export.

## 1. Backend entry point

The backend is a FastAPI application defined in `main.py`.

Main responsibilities:
- expose REST API endpoints for stations, observations, SYNOP preview, and settings
- initialize and manage the SQLite database
- normalize request payloads
- run manual validation checks
- generate SYNOP messages from observation data
- export validated observations to CSV
- support background SYNOP auto-decoding from incoming files

The app is created with:

```python
app = FastAPI(title="WOMS Weather Observation Portal Backend")
```

CORS is enabled for the frontend with `allow_origins=["*"]`.

---

## 2. Startup and database initialization

When the backend starts, it runs `init_db()`.

That function:
1. opens the SQLite database file `woms.db`
2. creates the `stations` table
3. creates the `observations` table
4. seeds default station records if the table is empty
5. seeds a default observation record if the table is empty
6. adds migration columns for later sections of the SYNOP data model

The database connection layer is in `database/db.py` and uses `sqlite3.Row` so rows can be accessed like dictionaries.

### Core data tables

`stations`
- stores station metadata such as station number, name, coordinates, elevation, email, type, and activity flag

`observations`
- stores the main weather observation payload
- includes meteorological fields (wind, visibility, cloud, temperature, pressure, rainfall, phenomena, etc.)
- stores `is_validated`, `generated_synop`, and `email_status`

---

## 3. Request lifecycle for a normal observation

A typical backend workflow looks like this:

### Step A — frontend sends observation data

The frontend sends a JSON payload to the observation POST endpoint:

- `POST /api/observations/`

The payload matches the `ObservationSchema` model defined in `main.py`.

### Step B — input is normalized

`clean_request_data()` removes empty strings and converts them into `None` so the later encoder and validator logic gets clean values.

### Step C — observation is optionally validated on save

If the client marks the observation as `is_validated = True`, the backend performs a fast validation pass using `validate_observation(data, st_num)`.

This quick validator checks:
- required fields
- wind direction and speed sanity
- visibility numeric range
- cloud cover and low cloud amount range
- dry/wet/dew temperature sanity
- station and mean sea level pressure range
- rainfall non-negative checks

If any errors are found, the endpoint rejects the request with HTTP 400.

### Step D — a SYNOP message is always generated

Even before formal validation, the backend always builds a SYNOP preview string using:

- `generate_synop_message(data, station_number)`
- wrapper in `encoders/synop_encoder.py`
- engine logic in `encoders/synop_engine.py`

This is the backend’s encoding stage.

The encoder follows a WMO-style FM-12 SYNOP message assembly:
1. `AAXX`
2. `YYGGiw`
3. `IIiii`
4. `iRixhVV`
5. `Nddff`
6. `1snTTT`
7. `2snTdTdTd`
8. `3P0P0P0P0`
9. `4PPPP`
10. `5appp`
11. `6RRRtR`
12. `7wwW1W2`
13. `8NhCLCMCH`
14. optional section 333 and section 555 groups

The output is stored in the database’s `generated_synop` column.

### Step E — the observation is persisted to SQLite

The `create_observation()` route inserts all observation fields into the `observations` table.

The database stores:
- the raw observation values
- the generated SYNOP string
- `email_status` set to `pending` for drafts and `sent` for validated observations
- `created_at` and `updated_at`

### Step F — CSV export is triggered for validated records

If the observation is marked validated on create, the route calls `save_observation_to_csv()` from the CSV service.

That service:
- creates the directory `validated_readings_csv/`
- writes one individual CSV file per observation
- appends to the cumulative file `all_validated_readings.csv`

The file naming pattern is:

`Observation_<station>_<date>_<time>_id<id>.csv`

---

## 4. Validation engine: the deeper rule system

The main detailed validation architecture is in `validators/engine.py` and is centered around `SynopValidationEngine`.

This engine performs a domain-by-domain validation pass in a strict sequence:

1. header validation
2. group format validation
3. station/sensor validation
4. temperature validation
5. humidity validation
6. pressure validation
7. wind validation
8. visibility validation
9. cloud validation
10. weather validation
11. rainfall validation
12. temporal consistency validation
13. cross-parameter validation

This validator is more robust than the lightweight `validate_observation()` helper in `main.py`. It builds a structured `ValidationReport` with:
- total checks
- passed checks
- warnings
- errors
- final status

### Main validator modules

- `validators/header_validator.py`
- `validators/group_format_validator.py`
- `validators/temperature_validator.py`
- `validators/humidity_validator.py`
- `validators/pressure_validator.py`
- `validators/wind_validator.py`
- `validators/visibility_validator.py`
- `validators/cloud_validator.py`
- `validators/weather_validator.py`
- `validators/rainfall_validator.py`
- `validators/temporal_validator.py`
- `validators/sensor_validator.py`
- `validators/cross_parameter_validator.py`

This is the system’s formal WMO-style meteorological validation layer.

---

## 5. Validation endpoint workflow

The dedicated validation route is:

- `POST /api/observations/{id}/validate_obs/`

Flow:
1. load observation by id
2. convert boolean flags to Python booleans
3. look up station metadata
4. run `validate_observation(obs_data, st_num)`
5. if valid:
   - update `is_validated = 1`
   - set `email_status = 'sent'`
   - refresh `generated_synop`
   - save the validated record to CSV
6. if invalid:
   - return HTTP 400 with the validation error payload

So there are two different validation levels in the backend:
- a basic save-time validation in `main.py`
- a detailed structural and meteorological validation engine in `validators/engine.py`

---

## 6. CSV export workflow

The export service is implemented in `services/csv_exporter.py`.

### What it does

For a validated observation, the backend writes:
- one per-observation CSV file to `validated_readings_csv/`
- a cumulative all-observations CSV file named `all_validated_readings.csv`

### API endpoints related to export

- `GET /api/observations/{id}/csv/`
  - downloads a single observation CSV

- `GET /api/observations/csv/all/`
  - downloads validated or all observations as CSV

The export logic takes the observation row, enriches it with station metadata, and serializes it using a fixed column mapping.

---

## 7. SYNOP preview endpoint

The preview endpoint is:

- `POST /api/synop/preview/`

It takes an observation payload, resolves the relevant station number from the database, and immediately generates a preview SYNOP message using the encoder.

This is useful for the frontend preview experience before the record is formally stored or validated.

---

## 8. Station CRUD endpoints

The backend also supports full station CRUD:

- `GET /api/stations/`
- `POST /api/stations/`
- `GET /api/stations/{id}/`
- `PUT /api/stations/{id}/`
- `DELETE /api/stations/{id}/`

These endpoints interact directly with the `stations` table and return station records as JSON.

---

## 9. Settings endpoints

The backend also includes a simple settings service:

- `GET /api/settings/`
- `POST /api/settings/`

The actual settings are loaded and saved from `config/settings.py`, which supports dynamic configuration such as the auto-decoder settings.

---

## 10. Automatic SYNOP decoder service

The folder `services/auto_decoder.py` implements a background task service.

### Behavior

The service:
1. loads configuration from `config/settings.py`
2. creates a scheduler with `BackgroundScheduler`
3. scans the `incoming_synops/` folder for `.txt` files
4. runs `SynopDecoder.decode_file(file_path)` on each file
5. prints the number of decoded line candidates
6. moves the processed file into `decoded_synops/`

This gives you a kind of background file ingestion workflow that is independent of the REST API.

---

## 11. End-to-end mental model

A simplified end-to-end sequence for the backend is:

```text
Frontend form
  -> POST /api/observations/
  -> normalize request
  -> optional save-time validation
  -> generate SYNOP string
  -> insert into SQLite
  -> optional CSV export if validated

Later:
  -> POST /api/observations/{id}/validate_obs/
  -> detailed validation report
  -> mark observation as validated
  -> save export copy to CSV
```

---

## 12. Main design idea

The backend is built around a practical workflow model:

- capture the raw weather observation
- generate SYNOP immediately for preview/review
- validate it through domain rules
- store the record in SQLite
- export validated reports as CSV

So the system blends:
- database persistence
- meteorological encoding
- meteorological validation
- file export
- batch SYNOP ingestion support

---

## 13. Important implementation note

The codebase has two parallel paths for SYNOP-related logic:

- a lightweight `generate_synop_message()` path in `encoders/synop_encoder.py`
- a deeper validation orchestrator in `validators/engine.py`

The first path is the production-facing message generator used by the API. The second path is the formal validation engine that checks the structure and code semantics of SYNOP content.
