import os
import csv
import io
from typing import Dict, Any, List, Optional
from datetime import datetime

# Directory for storing validated readings CSV files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_OUTPUT_DIR = os.path.join(BASE_DIR, "validated_readings_csv")
CUMULATIVE_CSV_PATH = os.path.join(CSV_OUTPUT_DIR, "all_validated_readings.csv")

# Define CSV columns mapping (key in observation dict -> CSV Header Title)
CSV_COLUMN_MAPPING = [
    ("id", "Observation ID"),
    ("station_number", "Station Number"),
    ("station_name", "Station Name"),
    ("base_station_email", "Base Station Email"),
    ("observation_date", "Observation Date"),
    ("observation_time", "Observation Time"),
    ("observer_name", "Observer Name"),
    ("observation_type", "Observation Type"),
    ("wind_direction", "Wind Direction (deg)"),
    ("wind_speed", "Wind Speed"),
    ("wind_unit", "Wind Unit"),

    ("visibility", "Visibility"),
    ("visibility_unit", "Visibility Unit"),
    ("visibility_reason", "Visibility Reason"),
    ("total_cloud_cover", "Total Cloud Cover (oktas)"),
    ("lowest_cloud_base", "Lowest Cloud Base (m)"),
    ("low_cloud_amount", "Low Cloud Amount (oktas)"),
    ("low_cloud_type", "Low Cloud Type"),
    ("middle_cloud_type", "Middle Cloud Type"),
    ("high_cloud_type", "High Cloud Type"),
    ("dry_bulb", "Dry Bulb Temp (°C)"),
    ("wet_bulb", "Wet Bulb Temp (°C)"),
    ("dew_point", "Dew Point Temp (°C)"),
    ("max_temperature", "Max Temperature (°C)"),
    ("min_temperature", "Min Temperature (°C)"),
    ("station_pressure", "Station Pressure (hPa)"),
    ("msl_pressure", "MSL Pressure (hPa)"),
    ("pressure_tendency", "Pressure Tendency"),
    ("pressure_change", "Pressure Change (hPa)"),
    ("present_weather", "Present Weather (ww)"),
    ("past_weather_1", "Past Weather 1 (W1)"),
    ("past_weather_2", "Past Weather 2 (W2)"),
    ("rainfall", "Rainfall (mm)"),
    ("rain_duration", "Rain Duration (hrs)"),
    ("phenomenon_thunder", "Thunderstorm"),
    ("phenomenon_lightning", "Lightning"),
    ("phenomenon_hail", "Hail"),
    ("phenomenon_dust_storm", "Dust Storm"),
    ("phenomenon_fog", "Fog"),
    ("phenomenon_mist", "Mist"),
    ("phenomenon_snow", "Snow"),
    ("sec333_max_temperature", "Sec 333 24h Max Temp (°C)"),
    ("sec333_min_temperature", "Sec 333 24h Min Temp (°C)"),
    ("ground_state", "Ground State (E)"),
    ("sunshine_hours", "Sunshine Hours"),
    ("evaporation", "Evaporation (mm)"),
    ("rainfall_24h", "24h Rainfall (mm)"),
    ("sec555_grass_min_temp", "Sec 555 Grass Min Temp (°C)"),
    ("sec555_soil_temp_5cm", "Sec 555 Soil Temp 5cm (°C)"),
    ("sec555_soil_temp_10cm", "Sec 555 Soil Temp 10cm (°C)"),
    ("sec555_soil_temp_20cm", "Sec 555 Soil Temp 20cm (°C)"),
    ("sec555_soil_temp_30cm", "Sec 555 Soil Temp 30cm (°C)"),
    ("sec555_soil_temp_50cm", "Sec 555 Soil Temp 50cm (°C)"),
    ("is_validated", "Is Validated"),
    ("generated_synop", "Generated SYNOP"),
    ("created_at", "Created At"),
    ("updated_at", "Updated At"),
]

def ensure_csv_dir() -> str:
    """Ensures the directory for storing validated CSV readings exists."""
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
    return CSV_OUTPUT_DIR

def format_observation_for_csv(obs: Dict[str, Any], station_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper to structure observation values cleanly for CSV export."""
    data = dict(obs)
    
    # Enrich with station details if provided or present
    st_details = data.get("station_details") or {}
    if station_info:
        st_details.update(station_info)
        
    data["station_number"] = data.get("station_number") or st_details.get("station_number", "")
    data["station_name"] = data.get("station_name") or st_details.get("station_name", "")
    data["base_station_email"] = data.get("base_station_email") or st_details.get("base_station_email", "")

    # Convert boolean indicators to Yes/No or True/False strings
    for col in [
        "phenomenon_thunder", "phenomenon_lightning", "phenomenon_hail",
        "phenomenon_dust_storm", "phenomenon_fog", "phenomenon_mist",
        "phenomenon_snow", "is_validated"
    ]:
        if col in data and data[col] is not None:
            data[col] = "Yes" if bool(data[col]) else "No"
            
    return data

def save_observation_to_csv(obs_data: Dict[str, Any], station_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Saves a validated weather observation reading as a CSV file.
    
    1. Writes an individual CSV file: Observation_{st_num}_{date}_{time}_{id}.csv
    2. Appends to/updates cumulative CSV log: all_validated_readings.csv
    
    Returns details including file_path and file_name.
    """
    ensure_csv_dir()
    formatted = format_observation_for_csv(obs_data, station_info)
    
    obs_id = formatted.get("id", "new")
    st_num = formatted.get("station_number", "unknown")
    obs_date = str(formatted.get("observation_date", "")).replace("-", "")
    obs_time = str(formatted.get("observation_time", "")).replace(":", "")
    
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"Observation_{st_num}_{obs_date}_{obs_time}_id{obs_id}.csv"
    individual_file_path = os.path.join(CSV_OUTPUT_DIR, file_name)
    
    headers = [header for _, header in CSV_COLUMN_MAPPING]
    row_values = [formatted.get(key, "") if formatted.get(key) is not None else "" for key, _ in CSV_COLUMN_MAPPING]
    
    # 1. Write individual CSV file
    with open(individual_file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row_values)
        
    # 2. Append to cumulative CSV file
    file_exists = os.path.exists(CUMULATIVE_CSV_PATH)
    with open(CUMULATIVE_CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(row_values)
        
    return {
        "status": "success",
        "file_name": file_name,
        "file_path": individual_file_path,
        "cumulative_path": CUMULATIVE_CSV_PATH
    }

def generate_csv_string_for_observations(observations: List[Dict[str, Any]]) -> str:
    """Generates a CSV formatted string for a list of observations."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = [header for _, header in CSV_COLUMN_MAPPING]
    writer.writerow(headers)
    
    for obs in observations:
        formatted = format_observation_for_csv(obs)
        row_values = [formatted.get(key, "") if formatted.get(key) is not None else "" for key, _ in CSV_COLUMN_MAPPING]
        writer.writerow(row_values)
        
    return output.getvalue()
