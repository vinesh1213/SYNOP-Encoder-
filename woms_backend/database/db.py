import sqlite3
from datetime import datetime, timezone
import os

DATABASE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "woms.db")

def get_db():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

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
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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
    
    # DB migration: add Section 555 columns
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
            pass
            
    _cloud_cols = [
        ("low_cloud_movement", "INTEGER"),
        ("middle_cloud_movement", "INTEGER"),
        ("high_cloud_movement", "INTEGER"),
        ("cloud_development_c", "INTEGER"),
        ("cloud_development_da", "INTEGER"),
        ("cloud_development_ec", "INTEGER"),
        ("cloud_layer_amount", "INTEGER"),
        ("special_cloud_phenomena", "INTEGER"),
    ]
    for _col, _typ in _cloud_cols:
        try:
            cursor.execute(f"ALTER TABLE observations ADD COLUMN {_col} {_typ}")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    _wind_cols = [
        ("wind_speed_m1", "REAL"),
        ("wind_speed_m2", "REAL"),
        ("wind_speed_m3", "REAL"),
    ]
    for _col, _typ in _wind_cols:
        try:
            cursor.execute(f"ALTER TABLE observations ADD COLUMN {_col} {_typ}")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    _indicator_cols = [
        ("precipitation_indicator", "TEXT"),
        ("weather_indicator", "TEXT"),
        ("rainfall_available", "TEXT"),
        ("weather_status", "TEXT"),
    ]
    for _col, _typ in _indicator_cols:
        try:
            cursor.execute(f"ALTER TABLE observations ADD COLUMN {_col} {_typ}")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    conn.close()
