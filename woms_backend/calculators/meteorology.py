import math
from typing import Optional

def calculate_dew_point(t: float, rh: float) -> float:
    """Calculate dew point using the Magnus-Tetens formula."""
    try:
        a = 17.27
        b = 237.7
        alpha = ((a * t) / (b + t)) + math.log(rh / 100.0)
        td = (b * alpha) / (a - alpha)
        return round(td, 1)
    except Exception:
        return 0.0

def calculate_rh(t: float, td: float) -> float:
    """Calculate Relative Humidity (%) given temp and dew point."""
    try:
        a = 17.27
        b = 237.7
        e = math.exp((a * td) / (b + td))
        es = math.exp((a * t) / (b + t))
        rh = (e / es) * 100.0
        return round(max(0.0, min(100.0, rh)), 1)
    except Exception:
        return 0.0

def calculate_mslp(station_pressure: float, elevation: float, temperature: float) -> float:
    """
    Calculate Mean Sea Level Pressure (MSLP) from Station Pressure.
    simplified hypsometric equation.
    P0 = P * exp((g * h) / (R * T))
    elevation in meters, temperature in Celsius.
    """
    try:
        g = 9.80665 # gravity
        R = 287.05 # specific gas constant for dry air
        T_kelvin = temperature + 273.15
        
        mslp = station_pressure * math.exp((g * elevation) / (R * T_kelvin))
        return round(mslp, 1)
    except Exception:
        return station_pressure

def convert_wind_speed(speed: float, from_unit: str, to_unit: str) -> float:
    """Convert wind speed between knots, m/s, and km/h."""
    try:
        if from_unit == to_unit:
            return speed
            
        # Convert everything to m/s first
        ms = speed
        if from_unit == 'knots':
            ms = speed * 0.514444
        elif from_unit == 'km/h':
            ms = speed / 3.6
            
        # Convert m/s to target
        if to_unit == 'knots':
            return round(ms * 1.94384, 1)
        elif to_unit == 'km/h':
            return round(ms * 3.6, 1)
            
        return round(ms, 1)
    except Exception:
        return speed
