from pydantic import BaseModel
from typing import Any, Dict, List, Optional


# =============================================================================
# Validation Engine Response Schemas
# =============================================================================

class ValidationResultSchema(BaseModel):
    """Single validation check result — mirrors validators.models.ValidationResult."""
    validation_name: str
    input_value: Optional[Any] = None
    expected_range: str = ""
    actual_value: Optional[Any] = None
    status: str = "PASS"  # PASS | WARNING | ERROR
    error_message: str = ""
    suggested_correction: str = ""
    domain: str = ""


class ValidationReportSchema(BaseModel):
    """
    Aggregated validation report — mirrors validators.models.ValidationReport.
    Returned by the /api/validate/* endpoints.
    """
    status: str = "ACCEPTED"  # ACCEPTED | WARNING | REJECTED
    overall_score: float = 100.0
    total_checks: int = 0
    passed: int = 0
    warnings: int = 0
    errors: int = 0
    validation_summary: Dict[str, str] = {}
    errors_list: List[Dict[str, Any]] = []
    warnings_list: List[Dict[str, Any]] = []
    all_results: List[Dict[str, Any]] = []


class SynopValidateRequest(BaseModel):
    """Request body for POST /api/validate/synop."""
    synop: str


# =============================================================================
# Existing Schemas
# =============================================================================

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
    precipitation_indicator: str
    weather_indicator: str
    wind_direction: Optional[Any] = None
    wind_speed: Optional[Any] = None
    wind_readings: Optional[List[float]] = []
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
    low_cloud_movement: Optional[Any] = None
    middle_cloud_movement: Optional[Any] = None
    high_cloud_movement: Optional[Any] = None
    cloud_development_c: Optional[Any] = None
    cloud_development_da: Optional[Any] = None
    cloud_development_ec: Optional[Any] = None
    cloud_layer_amount: Optional[Any] = None
    special_cloud_phenomena: Optional[Any] = None
    # Section 555 — Soil & Grass temperatures
    sec555_grass_min_temp: Optional[Any] = None
    sec555_soil_temp_5cm: Optional[Any] = None
    sec555_soil_temp_10cm: Optional[Any] = None
    sec555_soil_temp_20cm: Optional[Any] = None
    sec555_soil_temp_30cm: Optional[Any] = None
    sec555_soil_temp_50cm: Optional[Any] = None
    # Thermograph & Hygrograph (optional instrument readings)
    thermograph_reading: Optional[Any] = None
    hygrograph_reading: Optional[Any] = None
    is_validated: Optional[bool] = False
    generated_synop: Optional[str] = None
    email_status: Optional[str] = None
