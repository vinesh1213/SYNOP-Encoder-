import os
import glob
from api_routes import create_observation, validate_observation_endpoint
from backend_core import ObservationSchema, get_db


def test_api_csv_integration():
    print("--- Test 2: Testing API Observation Validation CSV Saving ---")
    
    # 1. Create a validated observation schema instance
    obs_input = ObservationSchema(
        station=1,
        observation_date="2026-08-03",
        observation_time="14:00:00",
        observer_name="Automated Test",
        observation_type="routine",
        precipitation_indicator="1",
        weather_indicator="1",
        wind_direction=180,
        wind_speed=12.0,
        wind_unit="knots",
        visibility=8000,
        visibility_unit="meters",
        total_cloud_cover=5,
        lowest_cloud_base=1000,
        dry_bulb=26.5,
        wet_bulb=21.0,
        dew_point=18.0,
        station_pressure=1006.0,
        msl_pressure=1012.5,
        rainfall=0.0,
        is_validated=True
    )
    
    saved_obs = create_observation(obs_input)
    print("Saved Observation ID:", saved_obs["id"])
    print("Generated SYNOP:", saved_obs["generated_synop"])
    
    # Check if CSV file for this observation was saved
    csv_files = glob.glob(os.path.join("validated_readings_csv", f"*_id{saved_obs['id']}.csv"))
    assert len(csv_files) > 0, f"Expected CSV file for observation ID {saved_obs['id']} to exist!"
    print(f"Found CSV File for Obs {saved_obs['id']}: {csv_files[0]}")
    
    print("--- Test 2 PASSED Successfully! ---\n")

if __name__ == "__main__":
    test_api_csv_integration()
