import os
import sqlite3
import math
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="WOMS Weather Observation Portal Backend")

# Enable CORS for frontend running on localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_FILE = "woms.db"

def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize SQLite database
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create stations table
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
    
    # Create observations table
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
    
    # Insert default Meenambakkam station if table is empty
    cursor.execute("SELECT COUNT(*) FROM stations")
    if cursor.fetchone()[0] == 0:
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
            INSERT INTO stations (
                station_number, station_name, latitude, longitude, elevation, 
                base_station_email, station_type, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "43279", "Meenambakkam", 12.98, 80.18, 16.0, 
            "meenambakkam@example.com", "manned", 1, now, now
        ))
        
        # Insert default observation if empty
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

    # DB migration: add Section 555 columns to existing databases (safe no-op if already present)
    _sec555_cols = [
        ("sec555_grass_min_temp",  "REAL"),
        ("sec555_soil_temp_5cm",   "REAL"),
        ("sec555_soil_temp_10cm",  "REAL"),
        ("sec555_soil_temp_20cm",  "REAL"),
        ("sec555_soil_temp_30cm",  "REAL"),
        ("sec555_soil_temp_50cm",  "REAL"),
    ]
    for _col, _typ in _sec555_cols:
        try:
            cursor.execute(f"ALTER TABLE observations ADD COLUMN {_col} {_typ}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists

    conn.close()

init_db()

# Pydantic Schemas
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
    # Section 555 — Soil & Grass temperatures
    sec555_grass_min_temp: Optional[Any] = None
    sec555_soil_temp_5cm: Optional[Any] = None
    sec555_soil_temp_10cm: Optional[Any] = None
    sec555_soil_temp_20cm: Optional[Any] = None
    sec555_soil_temp_30cm: Optional[Any] = None
    sec555_soil_temp_50cm: Optional[Any] = None
    is_validated: Optional[bool] = False
    generated_synop: Optional[str] = None
    email_status: Optional[str] = None

# Helper to normalize client-side data
def clean_request_data(data: dict) -> dict:
    cleaned = {}
    for k, v in data.items():
        if v == "" or v is None:
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned

# Translate validation logic
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
    if wd is not None:
        try:
            wd_val = float(wd)
            if wd_val < 0 or wd_val > 360:
                errors["wind_direction"] = ["Wind direction must be between 0 and 360 degrees."]
        except ValueError:
            errors["wind_direction"] = ["Wind direction must be a valid number."]

    ws = data.get("wind_speed")
    if ws is not None:
        try:
            ws_val = float(ws)
            if ws_val < 0:
                errors["wind_speed"] = ["Wind speed cannot be negative."]
            
            gust = data.get("max_gust")
            if gust is not None:
                try:
                    gust_val = float(gust)
                    if gust_val < 0:
                        errors["max_gust"] = ["Max gust speed cannot be negative."]
                    elif gust_val < ws_val:
                        errors["max_gust"] = ["Max gust must be greater than or equal to wind speed."]
                except ValueError:
                    errors["max_gust"] = ["Max gust must be a valid number."]
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
    if cc is not None:
        try:
            cc_val = int(cc)
            if cc_val < 0 or cc_val > 8:
                errors["total_cloud_cover"] = ["Total cloud cover must be between 0 and 8 oktas."]
            
            lca = data.get("low_cloud_amount")
            if lca is not None:
                try:
                    lca_val = int(lca)
                    if lca_val < 0 or lca_val > 8:
                        errors["low_cloud_amount"] = ["Low cloud amount must be between 0 and 8 oktas."]
                    elif lca_val > cc_val:
                        errors["low_cloud_amount"] = ["Low cloud amount cannot exceed total cloud cover."]
                except ValueError:
                    errors["low_cloud_amount"] = ["Low cloud amount must be a valid integer."]
        except ValueError:
            errors["total_cloud_cover"] = ["Total cloud cover must be a valid integer."]

    t_dry = None
    t_wet = None
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
            if t_dry is not None and t_wet > t_dry:
                errors["wet_bulb"] = ["Wet bulb temperature cannot exceed dry bulb temperature."]
        except ValueError:
            errors["wet_bulb"] = ["Wet bulb temperature must be a valid number."]

    dew = data.get("dew_point")
    if dew is not None:
        try:
            t_dew = float(dew)
            if t_dew < -60 or t_dew > 60:
                errors["dew_point"] = ["Dew point temperature must be between -60°C and 60°C."]
            if t_wet is not None and t_dew > t_wet:
                errors["dew_point"] = ["Dew point temperature cannot exceed wet bulb temperature."]
            elif t_dry is not None and t_dew > t_dry:
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

# FM-12 SYNOP message encoder — 12 named encoding stages in WMO transmission order
def generate_synop_message(data: dict, station_number: Optional[str]) -> dict:
    groups = []
    explanation = {}

    # ═══════════════════════════════════════════════════════
    # 1. HEADER ENCODER  —  AAXX  YYGGiw
    # ═══════════════════════════════════════════════════════
    groups.append("AAXX")
    explanation["AAXX"] = "AAXX (Telegraphic report from fixed land station)"

    yy = "//"
    obs_date = data.get("observation_date")
    if obs_date:
        try:
            dt = datetime.strptime(obs_date, "%Y-%m-%d")
            yy = f"{dt.day:02d}"
        except Exception:
            pass

    gg = "//"
    obs_time = data.get("observation_time")
    if obs_time:
        try:
            gg = f"{int(obs_time.split(':')[0]):02d}"
        except Exception:
            pass

    iw = "4" if data.get("wind_unit") == "knots" else "1"
    header = f"{yy}{gg}{iw}"
    groups.append(header)
    explanation[header] = (
        f"{yy} (Day of month), {gg} UTC (Hour of observation), "
        f"{iw} (Wind speed in {data.get('wind_unit') or 'm/s'} measured by anemometer)"
    )

    # ═══════════════════════════════════════════════════════
    # 2. STATION ENCODER  —  IIiii
    # ═══════════════════════════════════════════════════════
    station_str = str(station_number or "99999").zfill(5)
    groups.append(station_str)
    explanation[station_str] = (
        f"IIiii (Station identifier) — Block: {station_str[:2]}, Station: {station_str[2:]}"
    )

    # ═══════════════════════════════════════════════════════
    # 3. VISIBILITY ENCODER  —  iRixhVV
    # ═══════════════════════════════════════════════════════
    rainfall = data.get("rainfall")
    ir_val = "3"
    if rainfall is not None:
        try:
            if float(rainfall) > 0:
                ir_val = "1"
        except (ValueError, TypeError):
            pass

    ix_val = "1" if data.get("present_weather") is not None else "3"

    h_val = "/"
    lowest_cloud = data.get("lowest_cloud_base")
    if lowest_cloud is not None:
        try:
            val = float(lowest_cloud)
            if   val < 50:   h_val = "0"
            elif val < 100:  h_val = "1"
            elif val < 200:  h_val = "2"
            elif val < 300:  h_val = "3"
            elif val < 600:  h_val = "4"
            elif val < 1000: h_val = "5"
            elif val < 1500: h_val = "6"
            elif val < 2000: h_val = "7"
            elif val < 2500: h_val = "8"
            else:            h_val = "9"
        except (ValueError, TypeError):
            pass

    vv_str = "//"
    visibility = data.get("visibility")
    if visibility is not None:
        try:
            vis_km = float(visibility)
            if data.get("visibility_unit") == "meters":
                vis_km /= 1000.0
            if vis_km < 0.1:
                vv_str = "00"
            elif vis_km <= 5.0:
                vv_str = f"{int(round(vis_km * 10)):02d}"
            elif vis_km <= 30.0:
                vv_str = str(int(round(vis_km + 50)))
            elif vis_km <= 50.0:
                vv_str = str(int(round((vis_km - 30) / 5 + 80)))
            else:
                vv_str = "89"
        except (ValueError, TypeError):
            pass

    group_vis = f"{ir_val}{ix_val}{h_val}{vv_str}"
    groups.append(group_vis)
    explanation[group_vis] = (
        f"iRixhVV — Precip indicator: {ir_val}, Weather indicator: {ix_val}, "
        f"Cloud base: {'unknown' if h_val == '/' else h_val}, Visibility: {vv_str}"
    )

    # ═══════════════════════════════════════════════════════
    # 4. WIND ENCODER  —  Nddff
    # ═══════════════════════════════════════════════════════
    n_val = "/"
    t_cloud = data.get("total_cloud_cover")
    if t_cloud is not None:
        n_val = str(t_cloud)

    dd_val = "//"
    w_dir = data.get("wind_direction")
    if w_dir is not None:
        try:
            dd_val = f"{int(round(float(w_dir) / 10)):02d}"
        except (ValueError, TypeError):
            pass

    ff_val = "//"
    w_spd = data.get("wind_speed")
    if w_spd is not None:
        try:
            ff_val = f"{int(round(float(w_spd))):02d}"
        except (ValueError, TypeError):
            pass

    group_wind = f"{n_val}{dd_val}{ff_val}"
    groups.append(group_wind)
    explanation[group_wind] = (
        f"Nddff — Cloud cover: {'unknown' if n_val == '/' else n_val + ' oktas'}, "
        f"Wind dir: {'unknown' if dd_val == '//' else dd_val + '0 deg'}, "
        f"Wind speed: {'unknown' if ff_val == '//' else ff_val + ' ' + (data.get('wind_unit') or 'knots')}"
    )

    # ═══════════════════════════════════════════════════════
    # 5. TEMPERATURE ENCODER  —  1snTTT
    # ═══════════════════════════════════════════════════════
    dry_bulb = data.get("dry_bulb")
    if dry_bulb is not None:
        try:
            temp = float(dry_bulb)
            sn  = "1" if temp < 0 else "0"
            ttt = f"{int(round(abs(temp) * 10)):03d}"[-3:]
            g   = f"1{sn}{ttt}"
            groups.append(g)
            explanation[g] = f"1snTTT — Dry bulb temperature: {temp}°C"
        except (ValueError, TypeError):
            pass

    # ═══════════════════════════════════════════════════════
    # 6. DEW POINT ENCODER  —  2snTdTdTd
    # ═══════════════════════════════════════════════════════
    dew_point = data.get("dew_point")
    if dew_point is not None:
        try:
            temp = float(dew_point)
            sn  = "1" if temp < 0 else "0"
            ttt = f"{int(round(abs(temp) * 10)):03d}"[-3:]
            g   = f"2{sn}{ttt}"
            groups.append(g)
            explanation[g] = f"2snTdTdTd — Dew point temperature: {temp}°C"
        except (ValueError, TypeError):
            pass

    # ═══════════════════════════════════════════════════════
    # 7. PRESSURE ENCODER  —  3P0P0P0P0  ·  4PPPP  ·  5appp
    # ═══════════════════════════════════════════════════════
    st_press = data.get("station_pressure")
    if st_press is not None:
        try:
            press = float(st_press)
            val   = f"{int(round(press * 10)):04d}"[-4:]
            g     = f"3{val}"
            groups.append(g)
            explanation[g] = f"3P0P0P0P0 — Station level pressure: {press} hPa"
        except (ValueError, TypeError):
            pass

    msl_press = data.get("msl_pressure")
    if msl_press is not None:
        try:
            press = float(msl_press)
            val   = f"{int(round(press * 10)):04d}"[-4:]
            g     = f"4{val}"
            groups.append(g)
            explanation[g] = f"4PPPP — Mean sea level pressure: {press} hPa"
        except (ValueError, TypeError):
            pass

    tendency = data.get("pressure_tendency")
    change   = data.get("pressure_change")
    if tendency is not None and change is not None:
        try:
            a          = str(tendency)
            change_val = float(change)
            ppp        = f"{int(round(change_val * 10)):03d}"[-3:]
            g          = f"5{a}{ppp}"
            groups.append(g)
            explanation[g] = f"5aPPP — Tendency: {a}, 3h pressure change: {change_val} hPa"
        except (ValueError, TypeError):
            pass

    # ═══════════════════════════════════════════════════════
    # 8. RAINFALL ENCODER  —  6RRRtR
    # ═══════════════════════════════════════════════════════
    if rainfall is not None:
        try:
            rain_val = float(rainfall)
            if rain_val > 0:
                rrr = "990" if rain_val <= 0.05 else f"{int(round(rain_val)):03d}"[-3:]
                tr  = str(data.get("rain_duration") or "6")
                g   = f"6{rrr}{tr}"
                groups.append(g)
                explanation[g] = f"6RRRtR — Precipitation: {rain_val} mm, Duration code: {tr}"
        except (ValueError, TypeError):
            pass

    # ═══════════════════════════════════════════════════════
    # 9. WEATHER ENCODER  —  7wwW1W2
    # ═══════════════════════════════════════════════════════
    pres_weather = data.get("present_weather")
    if pres_weather is not None:
        try:
            ww = f"{int(pres_weather):02d}"
            w1 = "/" if data.get("past_weather_1") is None else str(data.get("past_weather_1"))
            w2 = "/" if data.get("past_weather_2") is None else str(data.get("past_weather_2"))
            g  = f"7{ww}{w1}{w2}"
            groups.append(g)
            explanation[g] = f"7wwW1W2 — Present weather: {ww}, Past W1: {w1}, W2: {w2}"
        except (ValueError, TypeError):
            pass

    # ═══════════════════════════════════════════════════════
    # 10. CLOUD ENCODER  —  8NhCLCMCH
    # ═══════════════════════════════════════════════════════
    low_amt = "/" if data.get("low_cloud_amount")  is None else str(data.get("low_cloud_amount"))
    cl      = "/" if data.get("low_cloud_type")    is None else str(data.get("low_cloud_type"))
    cm      = "/" if data.get("middle_cloud_type") is None else str(data.get("middle_cloud_type"))
    ch      = "/" if data.get("high_cloud_type")   is None else str(data.get("high_cloud_type"))
    if low_amt != "/" or cl != "/" or cm != "/" or ch != "/":
        g = f"8{low_amt}{cl}{cm}{ch}"
        groups.append(g)
        explanation[g] = (
            f"8NhCLCMCH — Low cloud: {'unknown' if low_amt == '/' else low_amt + ' oktas'}, "
            f"CL: {cl}, CM: {cm}, CH: {ch}"
        )

    # ═══════════════════════════════════════════════════════
    # 11. SECTION 333 ENCODER  —  1snTxTx · 2snTnTn · 4E's's' · 55SSS
    # ═══════════════════════════════════════════════════════
    has_sec333  = False
    sec333_grps = []

    sec_max_t = data.get("sec333_max_temperature")
    if sec_max_t is not None:
        try:
            temp = float(sec_max_t)
            has_sec333 = True
            sn  = "1" if temp < 0 else "0"
            ttt = f"{int(round(abs(temp) * 10)):03d}"[-3:]
            g   = f"1{sn}{ttt}"
            sec333_grps.append(g)
            explanation[f"[333] {g}"] = f"[333] 1snTxTxTx — Maximum temperature: {temp}°C"
        except (ValueError, TypeError):
            pass

    sec_min_t = data.get("sec333_min_temperature")
    if sec_min_t is not None:
        try:
            temp = float(sec_min_t)
            has_sec333 = True
            sn  = "1" if temp < 0 else "0"
            ttt = f"{int(round(abs(temp) * 10)):03d}"[-3:]
            g   = f"2{sn}{ttt}"
            sec333_grps.append(g)
            explanation[f"[333] {g}"] = f"[333] 2snTnTnTn — Minimum temperature: {temp}°C"
        except (ValueError, TypeError):
            pass

    gr_state = data.get("ground_state")
    if gr_state is not None:
        has_sec333 = True
        E = str(gr_state)
        g = f"4{E}///"
        sec333_grps.append(g)
        explanation[f"[333] {g}"] = f"[333] 4E's's' — Ground state code: {E}"

    sun_hours = data.get("sunshine_hours")
    if sun_hours is not None:
        try:
            sun = float(sun_hours)
            has_sec333 = True
            ss  = f"{int(round(sun * 10)):03d}"[-3:]
            g   = f"55{ss}"
            sec333_grps.append(g)
            explanation[f"[333] {g}"] = f"[333] 55SSS — Sunshine duration: {sun} hours"
        except (ValueError, TypeError):
            pass

    if has_sec333:
        groups.append("333")
        explanation["333"] = "Section 333 — Regional and national supplementary data"
        groups.extend(sec333_grps)

    # ═══════════════════════════════════════════════════════
    # 12. SECTION 555 ENCODER  —  Grass & Soil Temperatures
    # ═══════════════════════════════════════════════════════
    has_sec555  = False
    sec555_grps = []

    grass_min = data.get("sec555_grass_min_temp")
    if grass_min is not None:
        try:
            temp = float(grass_min)
            has_sec555 = True
            sn  = "1" if temp < 0 else "0"
            ttt = f"{int(round(abs(temp) * 10)):03d}"[-3:]
            g   = f"1{sn}{ttt}"
            sec555_grps.append(g)
            explanation["[555] Tg"] = f"[555] 1snTgTgTg — Grass minimum temperature: {temp}°C"
        except (ValueError, TypeError):
            pass

    for depth_key, depth_prefix, depth_label in [
        ("sec555_soil_temp_5cm",  "2", "-5cm"),
        ("sec555_soil_temp_10cm", "3", "-10cm"),
        ("sec555_soil_temp_20cm", "4", "-20cm"),
        ("sec555_soil_temp_30cm", "5", "-30cm"),
        ("sec555_soil_temp_50cm", "6", "-50cm"),
    ]:
        soil_val = data.get(depth_key)
        if soil_val is not None:
            try:
                temp = float(soil_val)
                has_sec555 = True
                sn  = "1" if temp < 0 else "0"
                ttt = f"{int(round(abs(temp) * 10)):03d}"[-3:]
                g   = f"{depth_prefix}{sn}{ttt}"
                sec555_grps.append(g)
                explanation[f"[555] Ts{depth_label}"] = (
                    f"[555] {depth_prefix}snTsTsTs — Soil temperature at {depth_label}: {temp}°C"
                )
            except (ValueError, TypeError):
                pass

    if has_sec555:
        groups.append("55555")
        explanation["55555"] = "Section 555 — Soil temperatures and grass minimum temperature"
        groups.extend(sec555_grps)

    return {
        "synop": " ".join(groups) + " =",
        "explanations": explanation
    }

# -----------------
# API Routes

# Station Endpoints
@app.get("/api/stations/")
def get_stations():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stations")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/stations/", status_code=201)
def create_station(station: StationSchema):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check uniqueness
    cursor.execute("SELECT id FROM stations WHERE station_number = ?", (station.station_number,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail={"station_number": ["Station with this number already exists."]}
        )
    
    now = datetime.utcnow().isoformat() + "Z"
    cursor.execute("""
        INSERT INTO stations (
            station_number, station_name, latitude, longitude, elevation, 
            base_station_email, station_type, is_active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        station.station_number, station.station_name, station.latitude, station.longitude,
        station.elevation, station.base_station_email, station.station_type,
        1 if station.is_active else 0, now, now
    ))
    new_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM stations WHERE id = ?", (new_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row)

@app.get("/api/stations/{id}/")
def get_station_detail(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stations WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Not found.")
    return dict(row)

@app.put("/api/stations/{id}/")
def update_station(id: int, station: StationSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM stations WHERE id = ?", (id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Not found.")
    
    now = datetime.utcnow().isoformat() + "Z"
    cursor.execute("""
        UPDATE stations SET 
            station_number = ?, station_name = ?, latitude = ?, longitude = ?,
            elevation = ?, base_station_email = ?, station_type = ?, is_active = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        station.station_number, station.station_name, station.latitude, station.longitude,
        station.elevation, station.base_station_email, station.station_type,
        1 if station.is_active else 0, now, id
    ))
    conn.commit()
    
    cursor.execute("SELECT * FROM stations WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row)

@app.delete("/api/stations/{id}/", status_code=204)
def delete_station(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM stations WHERE id = ?", (id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Not found.")
    
    cursor.execute("DELETE FROM stations WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return Response(status_code=204)

# Observation Endpoints
@app.get("/api/observations/")
def get_observations(
    station: Optional[int] = None,
    date: Optional[str] = None,
    email_status: Optional[str] = None
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM observations"
    conditions = []
    params = []
    
    if station is not None:
        conditions.append("station = ?")
        params.append(station)
    if date:
        conditions.append("observation_date = ?")
        params.append(date)
    if email_status:
        conditions.append("email_status = ?")
        params.append(email_status)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Enrich with station details
    cursor.execute("SELECT id, station_name, station_number, base_station_email FROM stations")
    stations_map = {r["id"]: dict(r) for r in cursor.fetchall()}
    conn.close()
    
    enriched = []
    for r in rows:
        obs = dict(r)
        # Convert bools
        for col in ["phenomenon_thunder", "phenomenon_lightning", "phenomenon_hail", 
                    "phenomenon_dust_storm", "phenomenon_fog", "phenomenon_mist", "phenomenon_snow", "is_validated"]:
            obs[col] = bool(obs[col])
            
        s_id = obs["station"]
        st = stations_map.get(s_id)
        obs["station_details"] = {
            "station_name": st["station_name"],
            "station_number": st["station_number"],
            "base_station_email": st["base_station_email"]
        } if st else None
        enriched.append(obs)
        
    # Sort by date/time descending
    enriched.sort(key=lambda x: f"{x['observation_date']}T{x['observation_time']}", reverse=True)
    return enriched

@app.post("/api/observations/", status_code=201)
def create_observation(obs: ObservationSchema):
    conn = get_db()
    cursor = conn.cursor()
    
    # Get station info
    cursor.execute("SELECT station_number FROM stations WHERE id = ?", (obs.station,))
    st_row = cursor.fetchone()
    st_num = st_row["station_number"] if st_row else None
    
    # Clean data (convert empty strings to None)
    data = clean_request_data(obs.dict())
    
    # Validate only when explicitly marking as validated
    if obs.is_validated:
        validation = validate_observation(data, st_num)
        if not validation["valid"]:
            conn.close()
            raise HTTPException(status_code=400, detail={"errors": validation["errors"]})
            
    now = datetime.utcnow().isoformat() + "Z"
    # Validated observations are marked 'sent'; drafts stay 'pending'
    email_status = "sent" if obs.is_validated else "pending"
    
    # --- NEW WORKFLOW: Generate SYNOP for ALL observations (not just validated) ---
    # SYNOP is always generated immediately on save so observers can review it
    # before the formal validation/transmission step.
    synop_res = generate_synop_message(data, st_num)
    synop_str = synop_res["synop"]
        
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
            evaporation, rainfall_24h,
            sec555_grass_min_temp, sec555_soil_temp_5cm, sec555_soil_temp_10cm,
            sec555_soil_temp_20cm, sec555_soil_temp_30cm, sec555_soil_temp_50cm,
            is_validated, generated_synop, email_status,
            created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?
        )
    """, (
        data.get("station"), data.get("observation_date"), data.get("observation_time"), data.get("observer_name"), data.get("observation_type"),
        data.get("wind_direction"), data.get("wind_speed"), data.get("wind_unit"), data.get("max_gust"), data.get("visibility"), data.get("visibility_unit"),
        data.get("visibility_reason"), data.get("total_cloud_cover"), data.get("lowest_cloud_base"), data.get("low_cloud_amount"),
        data.get("low_cloud_type"), data.get("middle_cloud_type"), data.get("high_cloud_type"), data.get("dry_bulb"), data.get("wet_bulb"), data.get("dew_point"),
        data.get("max_temperature"), data.get("min_temperature"), data.get("station_pressure"), data.get("msl_pressure"), data.get("pressure_tendency"),
        data.get("pressure_change"), data.get("present_weather"), data.get("past_weather_1"), data.get("past_weather_2"), data.get("rainfall"),
        data.get("rain_duration"), 1 if data.get("phenomenon_thunder") else 0, 1 if data.get("phenomenon_lightning") else 0, 1 if data.get("phenomenon_hail") else 0,
        1 if data.get("phenomenon_dust_storm") else 0, 1 if data.get("phenomenon_fog") else 0, 1 if data.get("phenomenon_mist") else 0, 1 if data.get("phenomenon_snow") else 0,
        data.get("sec333_max_temperature"), data.get("sec333_min_temperature"), data.get("ground_state"), data.get("sunshine_hours"),
        data.get("evaporation"), data.get("rainfall_24h"),
        data.get("sec555_grass_min_temp"), data.get("sec555_soil_temp_5cm"), data.get("sec555_soil_temp_10cm"),
        data.get("sec555_soil_temp_20cm"), data.get("sec555_soil_temp_30cm"), data.get("sec555_soil_temp_50cm"),
        1 if obs.is_validated else 0, synop_str, email_status,
        now, now
    ))
    new_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM observations WHERE id = ?", (new_id,))
    row = dict(cursor.fetchone())
    conn.close()
    
    # Normalize types
    for col in ["phenomenon_thunder", "phenomenon_lightning", "phenomenon_hail", 
                "phenomenon_dust_storm", "phenomenon_fog", "phenomenon_mist", "phenomenon_snow", "is_validated"]:
        row[col] = bool(row[col])
    return row

@app.get("/api/observations/{id}/")
def get_observation_detail(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM observations WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Not found.")
    
    obs = dict(row)
    for col in ["phenomenon_thunder", "phenomenon_lightning", "phenomenon_hail", 
                "phenomenon_dust_storm", "phenomenon_fog", "phenomenon_mist", "phenomenon_snow", "is_validated"]:
        obs[col] = bool(obs[col])
        
    # Add station details
    cursor.execute("SELECT station_name, station_number, base_station_email FROM stations WHERE id = ?", (obs["station"],))
    st = cursor.fetchone()
    conn.close()
    
    obs["station_details"] = {
        "station_name": st["station_name"],
        "station_number": st["station_number"],
        "base_station_email": st["base_station_email"]
    } if st else None
    
    return obs

@app.post("/api/observations/{id}/validate_obs/")
def validate_observation_endpoint(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM observations WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Not found.")
    
    obs_data = dict(row)
    for col in ["phenomenon_thunder", "phenomenon_lightning", "phenomenon_hail", 
                "phenomenon_dust_storm", "phenomenon_fog", "phenomenon_mist", "phenomenon_snow", "is_validated"]:
        obs_data[col] = bool(obs_data[col])
        
    cursor.execute("SELECT station_number FROM stations WHERE id = ?", (obs_data["station"],))
    st_row = cursor.fetchone()
    st_num = st_row["station_number"] if st_row else None
    
    validation = validate_observation(obs_data, st_num)
    
    if validation["valid"]:
        synop_res = generate_synop_message(obs_data, st_num)
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
            UPDATE observations SET 
                is_validated = 1,
                email_status = 'sent',
                generated_synop = ?,
                updated_at = ?
            WHERE id = ?
        """, (synop_res["synop"], now, id))
        conn.commit()
        conn.close()
        return {"is_validated": True}
    else:
        conn.close()
        raise HTTPException(status_code=400, detail={"is_validated": False, "errors": validation["errors"]})

# SYNOP Preview Endpoint
@app.post("/api/synop/preview/")
def preview_synop(obs: ObservationSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT station_number FROM stations WHERE id = ?", (obs.station,))
    st_row = cursor.fetchone()
    st_num = st_row["station_number"] if st_row else None
    conn.close()
    
    data = clean_request_data(obs.dict())
    result = generate_synop_message(data, st_num)
    return result
