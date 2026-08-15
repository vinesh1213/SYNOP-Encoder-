import os
import sqlite3
import math
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from services.csv_exporter import save_observation_to_csv, generate_csv_string_for_observations
from encoders.synop_encoder import generate_synop_message

DATABASE_FILE = "woms.db"


def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_number TEXT UNIQUE NOT NULL,
            station_name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            elevation REAL,
            base_station_email TEXT,
            station_type TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station INTEGER NOT NULL,
            observation_date TEXT NOT NULL,
            observation_time TEXT NOT NULL,
            observer_name TEXT NOT NULL,
            observation_type TEXT NOT NULL,
            wind_direction INTEGER,
            wind_speed REAL,
            wind_unit TEXT,
            max_gust REAL,
            visibility REAL,
            visibility_unit TEXT,
            visibility_reason TEXT,
            total_cloud_cover INTEGER,
            lowest_cloud_base REAL,
            low_cloud_amount INTEGER,
            low_cloud_type INTEGER,
            middle_cloud_type INTEGER,
            high_cloud_type INTEGER,
            dry_bulb REAL,
            wet_bulb REAL,
            dew_point REAL,
            max_temperature REAL,
            min_temperature REAL,
            station_pressure REAL,
            msl_pressure REAL,
            pressure_tendency INTEGER,
            pressure_change REAL,
            present_weather INTEGER,
            past_weather_1 INTEGER,
            past_weather_2 INTEGER,
            rainfall REAL,
            rain_duration INTEGER,
            phenomenon_thunder BOOLEAN DEFAULT 0,
            phenomenon_lightning BOOLEAN DEFAULT 0,
            phenomenon_hail BOOLEAN DEFAULT 0,
            phenomenon_dust_storm BOOLEAN DEFAULT 0,
            phenomenon_fog BOOLEAN DEFAULT 0,
            phenomenon_mist BOOLEAN DEFAULT 0,
            phenomenon_snow BOOLEAN DEFAULT 0,
            sec333_max_temperature REAL,
            sec333_min_temperature REAL,
            ground_state INTEGER,
            sunshine_hours REAL,
            evaporation REAL,
            rainfall_24h REAL,
            sec555_grass_min_temp REAL,
            sec555_soil_temp_5cm REAL,
            sec555_soil_temp_10cm REAL,
            sec555_soil_temp_20cm REAL,
            sec555_soil_temp_30cm REAL,
            sec555_soil_temp_50cm REAL,
            is_validated BOOLEAN DEFAULT 0,
            generated_synop TEXT,
            email_status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM stations")
    if cursor.fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        default_stations = [
            ("43279", "Chennai", 13.00, 80.18, 16.0, "chennai@weather.gov.in", "manned"),
            ("43271", "Pune", 18.53, 73.85, 560.0, "pune@weather.gov.in", "manned"),
            ("43285", "Hyderabad", 17.45, 78.46, 545.0, "hyderabad@weather.gov.in", "manned"),
            ("43295", "Bangalore", 12.97, 77.58, 920.0, "bangalore@weather.gov.in", "manned"),
            ("43269", "Mumbai", 19.12, 72.85, 14.0, "mumbai@weather.gov.in", "manned"),
            ("43185", "Kolkata", 22.65, 88.45, 6.0, "kolkata@weather.gov.in", "manned"),
            ("43049", "New Delhi", 28.58, 77.20, 216.0, "newdelhi@weather.gov.in", "manned"),
            ("43311", "Thiruvananthapuram", 8.48, 76.95, 64.0, "thiruvananthapuram@weather.gov.in", "manned"),
            ("43377", "Visakhapatnam", 17.72, 83.30, 45.0, "visakhapatnam@weather.gov.in", "manned"),
            ("43388", "Port Blair", 11.67, 92.73, 79.0, "portblair@weather.gov.in", "manned"),
        ]
        for num, name, lat, lon, elev, email, stype in default_stations:
            cursor.execute("""
                INSERT INTO stations (
                    station_number, station_name, latitude, longitude, elevation,
                    base_station_email, station_type, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (num, name, lat, lon, elev, email, stype, now, now))

        cursor.execute("SELECT COUNT(*) FROM observations")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO observations (
                    station, observation_date, observation_time, observer_name, observation_type,
                    wind_direction, wind_speed, wind_unit, max_gust, visibility, visibility_unit,
                    visibility_reason, total_cloud_cover, lowest_cloud_base, low_cloud_amount,
                    low_cloud_type, middle_cloud_type, high_cloud_type, dry_bulb, wet_bulb, dew_point,
                    max_temperature, min_temperature, station_pressure, msl_pressure, pressure_tendency,
                    pressure_change, present_weather, past_weather_1, past_weather_2, rainfall,
                    rain_duration, phenomenon_thunder, phenomenon_lightning, phenomenon_hail,
                    phenomenon_dust_storm, phenomenon_fog, phenomenon_mist, phenomenon_snow,
                    sec333_max_temperature, sec333_min_temperature, ground_state, sunshine_hours,
                    evaporation, rainfall_24h, is_validated, generated_synop, email_status,
                    created_at, updated_at
                ) VALUES (
                    1, '2026-07-02', '09:33:00', 'System', 'routine',
                    220, 15.0, 'knots', NULL, 6000.0, 'meters',
                    'none', 6, NULL, NULL, NULL, NULL, NULL, 27.2, 22.4, 19.8,
                    NULL, NULL, 1002.5, 1014.2, NULL, NULL, 2, 0, 0, 0.0,
                    NULL, 0, 0, 0, 0, 0, 0, 0,
                    NULL, NULL, NULL, NULL, NULL, NULL, 0,
                    'AAXX 02094 43279 31/56 62215 10272 20198 30025 40142 70200 86/// =',
                    'pending', ?, ?
                )
            """, (now, now))

    conn.commit()

    _sec555_cols = [
        ("sec555_grass_min_temp", "REAL"),
        ("sec555_soil_temp_5cm", "REAL"),
        ("sec555_soil_temp_10cm", "REAL"),
        ("sec555_soil_temp_20cm", "REAL"),
        ("sec555_soil_temp_30cm", "REAL"),
        ("sec555_soil_temp_50cm", "REAL"),
    ]
    for _col, _typ in _sec555_cols:
        try:
            cursor.execute(f"ALTER TABLE observations ADD COLUMN {_col} {_typ}")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    conn.close()


init_db()


class StationSchema(BaseModel):
    station_number: str
    station_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    base_station_email: Optional[str] = None
    station_type: Optional[str] = None
    is_active: Optional[bool] = True


class ObservationSchema(BaseModel):
    station: int
    observation_date: str
    observation_time: str
    observer_name: str
    observation_type: str
    precipitation_indicator: Optional[Any] = None
    weather_indicator: Optional[Any] = None
    wind_direction: Optional[Any] = None
    wind_speed: Optional[Any] = None
    wind_unit: Optional[str] = None
    max_gust: Optional[Any] = None
    visibility: Optional[Any] = None
    visibility_unit: Optional[str] = None
    visibility_reason: Optional[str] = None
    total_cloud_cover: Optional[Any] = None
    lowest_cloud_base: Optional[Any] = None
    low_cloud_amount: Optional[Any] = None
    low_cloud_type: Optional[Any] = None
    middle_cloud_type: Optional[Any] = None
    high_cloud_type: Optional[Any] = None
    dry_bulb: Optional[Any] = None
    wet_bulb: Optional[Any] = None
    dew_point: Optional[Any] = None
    max_temperature: Optional[Any] = None
    min_temperature: Optional[Any] = None
    station_pressure: Optional[Any] = None
    msl_pressure: Optional[Any] = None
    pressure_tendency: Optional[Any] = None
    pressure_change: Optional[Any] = None
    present_weather: Optional[Any] = None
    past_weather_1: Optional[Any] = None
    past_weather_2: Optional[Any] = None
    rainfall: Optional[Any] = None
    rain_duration: Optional[Any] = None
    phenomenon_thunder: Optional[bool] = False
    phenomenon_lightning: Optional[bool] = False
    phenomenon_hail: Optional[bool] = False
    phenomenon_dust_storm: Optional[bool] = False
    phenomenon_fog: Optional[bool] = False
    phenomenon_mist: Optional[bool] = False
    phenomenon_snow: Optional[bool] = False
    sec333_max_temperature: Optional[Any] = None
    sec333_min_temperature: Optional[Any] = None
    ground_state: Optional[Any] = None
    sunshine_hours: Optional[Any] = None
    evaporation: Optional[Any] = None
    rainfall_24h: Optional[Any] = None
    sec555_grass_min_temp: Optional[Any] = None
    sec555_soil_temp_5cm: Optional[Any] = None
    sec555_soil_temp_10cm: Optional[Any] = None
    sec555_soil_temp_20cm: Optional[Any] = None
    sec555_soil_temp_30cm: Optional[Any] = None
    sec555_soil_temp_50cm: Optional[Any] = None
    is_validated: Optional[bool] = False
    generated_synop: Optional[str] = None
    email_status: Optional[str] = None


def clean_request_data(data: dict) -> dict:
    cleaned = {}
    for k, v in data.items():
        if v == "" or v is None:
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def validate_observation(data: dict, station_number: Optional[str]) -> dict:
    errors = {}

    if not data.get("station"):
        errors["station"] = ["Station is required."]
    if not data.get("observation_date"):
        errors["observation_date"] = ["Observation date is required."]
    if not data.get("observation_time"):
        errors["observation_time"] = ["Observation time is required."]
    if not data.get("observer_name") or not str(data.get("observer_name")).strip():
        errors["observer_name"] = ["Observer name is required."]

    wd = data.get("wind_direction")
    if wd is not None and str(wd).strip() != "":
        compass_keys = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
            "CALM", "VRB", "VAR", "VARIABLE"
        ]
        if str(wd).strip().upper() not in compass_keys:
            try:
                wd_val = float(wd)
                if not ((0 <= wd_val <= 360) or wd_val == 99):
                    errors["wind_direction"] = ["Wind direction must be a valid compass direction (e.g. N, SW), degrees (0–360), or code (00–36, 99)."]
            except (ValueError, TypeError):
                errors["wind_direction"] = ["Wind direction must be a valid compass direction (e.g. N, SW), degrees (0–360), or code (00–36, 99)."]

    ws = data.get("wind_speed")
    if ws is not None:
        try:
            ws_val = float(ws)
            if ws_val < 0:
                errors["wind_speed"] = ["Wind speed cannot be negative."]
        except ValueError:
            errors["wind_speed"] = ["Wind speed must be a valid number."]


    vis = data.get("visibility")
    if vis is not None:
        try:
            vis_val = float(vis)
            if vis_val < 0:
                errors["visibility"] = ["Visibility cannot be negative."]
        except ValueError:
            errors["visibility"] = ["Visibility must be a valid number."]

    cc = data.get("total_cloud_cover")
    if cc is not None and str(cc).strip() != "":
        try:
            cc_val = int(cc)
            if cc_val < 0 or cc_val > 9:
                errors["total_cloud_cover"] = ["Total cloud cover must be between 0 and 9 oktas (9 = sky obscured)."]

            lca = data.get("low_cloud_amount")
            if lca is not None and str(lca).strip() != "":
                try:
                    lca_val = int(lca)
                    if lca_val < 0 or lca_val > 9:
                        errors["low_cloud_amount"] = ["Low cloud amount must be between 0 and 9 oktas."]
                    elif cc_val <= 8 and lca_val > cc_val:
                        errors["low_cloud_amount"] = ["Low cloud amount cannot exceed total cloud cover."]
                except (ValueError, TypeError):
                    errors["low_cloud_amount"] = ["Low cloud amount must be a valid integer."]
        except (ValueError, TypeError):
            errors["total_cloud_cover"] = ["Total cloud cover must be a valid integer."]

    dry = data.get("dry_bulb")
    if dry is not None:
        try:
            t_dry = float(dry)
            if t_dry < -60 or t_dry > 60:
                errors["dry_bulb"] = ["Dry bulb temperature must be between -60°C and 60°C."]
        except ValueError:
            errors["dry_bulb"] = ["Dry bulb temperature must be a valid number."]

    wet = data.get("wet_bulb")
    if wet is not None:
        try:
            t_wet = float(wet)
            if t_wet < -60 or t_wet > 60:
                errors["wet_bulb"] = ["Wet bulb temperature must be between -60°C and 60°C."]
            if dry is not None:
                t_dry = float(dry)
                if t_wet > t_dry:
                    errors["wet_bulb"] = ["Wet bulb temperature cannot exceed dry bulb temperature."]
        except ValueError:
            errors["wet_bulb"] = ["Wet bulb temperature must be a valid number."]

    dew = data.get("dew_point")
    if dew is not None:
        try:
            t_dew = float(dew)
            if t_dew < -60 or t_dew > 60:
                errors["dew_point"] = ["Dew point temperature must be between -60°C and 60°C."]
            if wet is not None:
                t_wet = float(wet)
                if t_dew > t_wet:
                    errors["dew_point"] = ["Dew point temperature cannot exceed wet bulb temperature."]
            elif dry is not None:
                t_dry = float(dry)
                if t_dew > t_dry:
                    errors["dew_point"] = ["Dew point temperature cannot exceed dry bulb temperature."]
        except ValueError:
            errors["dew_point"] = ["Dew point temperature must be a valid number."]

    sp = data.get("station_pressure")
    if sp is not None:
        try:
            sp_val = float(sp)
            if sp_val < 800 or sp_val > 1100:
                errors["station_pressure"] = ["Station pressure must be between 800 and 1100 hPa."]
        except ValueError:
            errors["station_pressure"] = ["Station pressure must be a valid number."]

    msl = data.get("msl_pressure")
    if msl is not None:
        try:
            msl_val = float(msl)
            if msl_val < 800 or msl_val > 1100:
                errors["msl_pressure"] = ["MSL pressure must be between 800 and 1100 hPa."]
        except ValueError:
            errors["msl_pressure"] = ["MSL pressure must be a valid number."]

    rain = data.get("rainfall")
    if rain is not None:
        try:
            rain_val = float(rain)
            if rain_val < 0:
                errors["rainfall"] = ["Rainfall amount cannot be negative."]
        except ValueError:
            errors["rainfall"] = ["Rainfall amount must be a valid number."]

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
