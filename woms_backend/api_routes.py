from fastapi import APIRouter, HTTPException, Response
from datetime import datetime
from typing import Optional

from backend_core import (
    get_db,
    ObservationSchema,
    StationSchema,
    clean_request_data,
    validate_observation,
    save_observation_to_csv,
    generate_csv_string_for_observations,
)
from pydantic import BaseModel
from encoders.synop_encoder import generate_synop_message
from decoders.synop_decoder import SynopDecoder

class SynopDecodeRequest(BaseModel):
    message: str


router = APIRouter()


@router.get("/api/stations/")
def get_stations():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stations")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/api/stations/", status_code=201)
def create_station(station: StationSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM stations WHERE station_number = ?", (station.station_number,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail={"station_number": ["Station with this number already exists."]})

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


@router.get("/api/stations/{id}/")
def get_station_detail(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stations WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Not found.")
    return dict(row)


@router.put("/api/stations/{id}/")
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


@router.delete("/api/stations/{id}/", status_code=204)
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


@router.get("/api/observations/")
def get_observations(station: Optional[int] = None, date: Optional[str] = None, email_status: Optional[str] = None):
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

    cursor.execute("SELECT id, station_name, station_number, base_station_email FROM stations")
    stations_map = {r["id"]: dict(r) for r in cursor.fetchall()}
    conn.close()

    enriched = []
    for r in rows:
        obs = dict(r)
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

    enriched.sort(key=lambda x: f"{x['observation_date']}T{x['observation_time']}", reverse=True)
    return enriched


@router.post("/api/observations/", status_code=201)
def create_observation(obs: ObservationSchema):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT station_number FROM stations WHERE id = ?", (obs.station,))
    st_row = cursor.fetchone()
    st_num = st_row["station_number"] if st_row else None

    data = clean_request_data(obs.dict())

    if obs.is_validated:
        validation = validate_observation(data, st_num)
        if not validation["valid"]:
            conn.close()
            raise HTTPException(status_code=400, detail={"errors": validation["errors"]})

    now = datetime.utcnow().isoformat() + "Z"
    email_status = "sent" if obs.is_validated else "pending"

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
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?
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

    for col in ["phenomenon_thunder", "phenomenon_lightning", "phenomenon_hail",
                "phenomenon_dust_storm", "phenomenon_fog", "phenomenon_mist", "phenomenon_snow", "is_validated"]:
        row[col] = bool(row[col])

    if obs.is_validated:
        cursor.execute("SELECT station_name, station_number, base_station_email FROM stations WHERE id = ?", (obs.station,))
        st_details_row = cursor.fetchone()
        st_info = dict(st_details_row) if st_details_row else None
        try:
            save_observation_to_csv(row, st_info)
        except Exception as e:
            print(f"Error saving observation reading to CSV: {e}")

    conn.close()
    return row


@router.get("/api/observations/{id}/")
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

    cursor.execute("SELECT station_name, station_number, base_station_email FROM stations WHERE id = ?", (obs["station"],))
    st = cursor.fetchone()
    conn.close()

    obs["station_details"] = {
        "station_name": st["station_name"],
        "station_number": st["station_number"],
        "base_station_email": st["base_station_email"]
    } if st else None

    return obs


@router.post("/api/observations/{id}/validate_obs/")
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

    cursor.execute("SELECT station_name, station_number, base_station_email FROM stations WHERE id = ?", (obs_data["station"],))
    st_row = cursor.fetchone()
    st_num = st_row["station_number"] if st_row else None
    st_info = dict(st_row) if st_row else None

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

        cursor.execute("SELECT * FROM observations WHERE id = ?", (id,))
        updated_row = dict(cursor.fetchone())
        for col in ["phenomenon_thunder", "phenomenon_lightning", "phenomenon_hail",
                    "phenomenon_dust_storm", "phenomenon_fog", "phenomenon_mist", "phenomenon_snow", "is_validated"]:
            updated_row[col] = bool(updated_row[col])
        conn.close()

        csv_info = {}
        try:
            csv_info = save_observation_to_csv(updated_row, st_info)
        except Exception as e:
            print(f"Error saving validated reading to CSV: {e}")

        return {
            "is_validated": True,
            "csv_exported": True,
            "csv_filename": csv_info.get("file_name")
        }
    else:
        conn.close()
        raise HTTPException(status_code=400, detail={"is_validated": False, "errors": validation["errors"]})


@router.get("/api/observations/{id}/csv/")
def download_observation_csv(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM observations WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Observation not found.")

    obs = dict(row)
    for col in ["phenomenon_thunder", "phenomenon_lightning", "phenomenon_hail",
                "phenomenon_dust_storm", "phenomenon_fog", "phenomenon_mist", "phenomenon_snow", "is_validated"]:
        obs[col] = bool(obs[col])

    cursor.execute("SELECT station_name, station_number, base_station_email FROM stations WHERE id = ?", (obs["station"],))
    st = cursor.fetchone()
    conn.close()

    if st:
        obs["station_details"] = dict(st)

    csv_content = generate_csv_string_for_observations([obs])
    st_num = obs.get("station_details", {}).get("station_number") or obs.get("station")
    filename = f"Observation_{st_num}_{obs['observation_date']}_id{id}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/api/observations/csv/all/")
def download_all_observations_csv(station: Optional[int] = None, date: Optional[str] = None, is_validated_only: bool = True):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM observations"
    conditions = []
    params = []

    if is_validated_only:
        conditions.append("is_validated = 1")
    if station is not None:
        conditions.append("station = ?")
        params.append(station)
    if date:
        conditions.append("observation_date = ?")
        params.append(date)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY observation_date DESC, observation_time DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.execute("SELECT id, station_name, station_number, base_station_email FROM stations")
    stations_map = {r["id"]: dict(r) for r in cursor.fetchall()}
    conn.close()

    observations = []
    for r in rows:
        obs = dict(r)
        for col in ["phenomenon_thunder", "phenomenon_lightning", "phenomenon_hail",
                    "phenomenon_dust_storm", "phenomenon_fog", "phenomenon_mist", "phenomenon_snow", "is_validated"]:
            obs[col] = bool(obs[col])
        st = stations_map.get(obs["station"])
        if st:
            obs["station_details"] = st
        observations.append(obs)

    csv_content = generate_csv_string_for_observations(observations)
    filename = "all_validated_readings.csv" if is_validated_only else "all_observations.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/api/synop/preview/")
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


@router.post("/api/synop/decode/")
def decode_synop_direct_post(req: SynopDecodeRequest):
    decoder = SynopDecoder()
    return decoder.decode_message(req.message)


@router.get("/api/synop/decode/")
def decode_synop_direct_get(message: str):
    decoder = SynopDecoder()
    return decoder.decode_message(message)



from config.settings import load_config, save_config


@router.get("/api/settings/")
def get_settings():
    try:
        return load_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/settings/")
def post_settings(settings_data: dict):
    try:
        save_config(settings_data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
