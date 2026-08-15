import sys
import os

# Add woms_backend to path so we can import from encoders
sys.path.append(os.path.join(os.path.dirname(__file__), 'woms_backend'))

from encoders.synop_engine import SynopEncodingEngine

def get_input(prompt, required=False, default=None):
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
        
    while True:
        try:
            val = input(full_prompt).strip()
            if not val and default is not None:
                return default
            if not val and required:
                print("This field is required.")
                continue
            return val
        except EOFError:
            print()
            sys.exit(0)

def main():
    print("=" * 50)
    print("WOMS Terminal - SYNOP Generator CLI")
    print("=" * 50)
    print("Enter the observation details below. Press Enter to skip optional fields.")
    print()

    station_number = get_input("Station Number (e.g. 67123)", required=True)
    
    data = {}
    data['observation_date'] = get_input("Observation Date (YYYY-MM-DD)", default="2026-08-14")
    data['observation_time'] = get_input("Observation Time (HH:MM UTC)", default="12:00")
    
    data['dry_bulb'] = get_input("Dry Bulb Temperature (°C)", required=True)
    data['precipitation_indicator'] = get_input("Precipitation Indicator (iR) [0-4]", required=True)
    data['weather_indicator'] = get_input("Weather Indicator (iX) [1-7]", required=True)
    
    data['wind_unit'] = get_input("Wind Unit (knots or m/s)", default="knots")
    data['wind_direction'] = get_input("Wind Direction (e.g. N, NE, 0-360)", default="")
    data['wind_speed'] = get_input("Wind Speed", default="")
    
    data['lowest_cloud_base'] = get_input("Lowest Cloud Base Height (meters)", default="")
    data['visibility'] = get_input("Visibility", default="")
    data['visibility_unit'] = get_input("Visibility Unit (meters or km)", default="meters")
    
    data['dew_point'] = get_input("Dew Point (°C)", default="")
    data['station_pressure'] = get_input("Station Pressure (hPa)", default="")
    data['msl_pressure'] = get_input("MSL Pressure (hPa)", default="")
    
    data['total_cloud_cover'] = get_input("Total Cloud Cover (0-9)", default="")
    data['low_cloud_amount'] = get_input("Low Cloud Amount (0-9)", default="")
    data['low_cloud_type'] = get_input("Low Cloud Type (0-9)", default="")
    data['middle_cloud_type'] = get_input("Middle Cloud Type (0-9)", default="")
    data['high_cloud_type'] = get_input("High Cloud Type (0-9)", default="")
    
    data['present_weather'] = get_input("Present Weather (ww) [00-99]", default="")
    data['past_weather_1'] = get_input("Past Weather 1 (W1) [0-9]", default="")
    data['past_weather_2'] = get_input("Past Weather 2 (W2) [0-9]", default="")
    
    data['rainfall'] = get_input("Rainfall Amount (mm)", default="")
    data['rain_duration'] = get_input("Rainfall Duration (tR) [1-9]", default="")

    engine = SynopEncodingEngine()
    result = engine.validate_and_encode(data, station_number)
    
    print("\n" + "=" * 50)
    if result.get('status') == 'success':
        print("SUCCESS! Generated SYNOP:")
        print(result.get('synop'))
        print("-" * 50)
        print("Details:")
        print(result.get('formatted_text'))
    else:
        print("ERROR generating SYNOP:")
        print(result.get('message'))
    print("=" * 50)

if __name__ == "__main__":
    main()
