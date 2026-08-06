import os
import glob
from services.csv_exporter import save_observation_to_csv, generate_csv_string_for_observations, CSV_OUTPUT_DIR

def test_csv_exporter_directly():
    print("--- Test 1: Testing CSV Exporter Service Directly ---")
    sample_obs = {
        "id": 999,
        "station": 1,
        "station_number": "43279",
        "station_name": "Meenambakkam",
        "base_station_email": "meenambakkam@example.com",
        "observation_date": "2026-08-03",
        "observation_time": "12:00:00",
        "observer_name": "Test Observer",
        "observation_type": "routine",
        "wind_direction": 220,
        "wind_speed": 15.0,
        "wind_unit": "knots",
        "visibility": 6000.0,
        "visibility_unit": "meters",
        "total_cloud_cover": 6,
        "lowest_cloud_base": 600.0,
        "dry_bulb": 28.5,
        "wet_bulb": 23.0,
        "dew_point": 20.2,
        "station_pressure": 1004.2,
        "msl_pressure": 1010.5,
        "rainfall": 0.0,
        "phenomenon_thunder": False,
        "is_validated": True,
        "generated_synop": "AAXX 03124 43279 31560 62215 10285 20202 30042 40105 =",
        "created_at": "2026-08-03T12:00:00Z",
        "updated_at": "2026-08-03T12:00:00Z"
    }

    result = save_observation_to_csv(sample_obs)
    print("CSV Export Result:", result)
    
    assert os.path.exists(result["file_path"]), f"Expected CSV file {result['file_path']} to exist!"
    assert os.path.exists(result["cumulative_path"]), f"Expected cumulative CSV file {result['cumulative_path']} to exist!"
    
    with open(result["file_path"], "r", encoding="utf-8") as f:
        content = f.read()
        print("\n--- Individual CSV File Content Preview ---")
        print(content)
        assert "Station Number" in content
        assert "43279" in content
        assert "Meenambakkam" in content
        assert "AAXX 03124" in content
        
    print("--- Test 1 PASSED Successfully! ---\n")

if __name__ == "__main__":
    test_csv_exporter_directly()
