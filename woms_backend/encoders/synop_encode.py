"""
SYNOP Encoding Module (synop_encode.py)
---------------------------------------
Modular, robust WMO SYNOP FM 12-XII encoding engine for Weather Observation Management System (WOMS).

Sections Handled:
- Section 0: Identifier & Header (AAXX YYGGiw IIiii)
- Section 1: Surface Data (iRiXhVV Nddff 1snTTT 2snTdTdTd 3P0P0P0P0 4PPPP 5appp 6RRRtR 7wwW1W2 8NhCLCMCH)
- Section 3: Regional Supplementary Data (333 1snTxTxTx 2snTnTnTn 3Ejjj 5SSS 6RRRtR)
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Add parent directory to path if run standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import load_config, save_config

# ==============================================================================
# 1. SAFE PRINT & UNICODE HANDLING FOR WINDOWS TERMINAL
# ==============================================================================

SAFE_TRANS = str.maketrans({
    "°": "deg ",
    "±": "+/-",
    "µ": "u",
    "•": "*",
    "–": "-",
    "—": "-"
})

def safe_print(*args, **kwargs) -> None:
    """Safely print text to standard output avoiding Windows encoding (cp1252) crashes."""
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    file = kwargs.get("file", sys.stdout)
    
    text = sep.join(str(a) for a in args) + end
    try:
        file.write(text)
        file.flush()
    except UnicodeEncodeError:
        safe_text = text.translate(SAFE_TRANS)
        file.write(safe_text.encode("ascii", "replace").decode("ascii"))
        file.flush()

def show_config() -> None:
    """Print the current persistent user settings configuration."""
    cfg = load_config()
    safe_print("\n=== Current System Configuration ===")
    safe_print(json.dumps(cfg, indent=4))
    safe_print("===================================\n")


# ==============================================================================
# 2. LOOKUP TABLES & WMO PARAMETER CODE CONVERTERS
# ==============================================================================

COMPASS_TO_DD = {
    "N": "36", "NNE": "02", "NE": "05", "ENE": "07",
    "E": "09", "ESE": "11", "SE": "14", "SSE": "16",
    "S": "18", "SSW": "20", "SW": "23", "WSW": "25",
    "W": "27", "WNW": "29", "NW": "32", "NNW": "34",
    "CALM": "00", "VRB": "99"
}

def encode_vv(val: Optional[float], unit: str = "meters") -> str:
    """Convert visibility value to 2-digit WMO VV code."""
    if val is None or str(val).strip() == "":
        return "//"
    try:
        v = float(val)
        vis_m = v * 1000.0 if unit == "km" else v
        if vis_m < 50: return "90"
        if vis_m == 50: return "91"
        if vis_m == 200: return "92"
        if vis_m == 500: return "93"
        if vis_m == 1000: return "94"
        if vis_m == 2000: return "95"
        if vis_m == 4000: return "96"
        if vis_m == 10000: return "97"
        if vis_m == 20000: return "98"
        if vis_m >= 50000: return "99"
        
        vis_km = vis_m / 1000.0
        if vis_km < 0.1: return "00"
        if vis_km <= 5.0: return f"{int(round(vis_km * 10)):02d}"
        if vis_km <= 30.0: return str(int(round(vis_km + 50)))
        if vis_km <= 70.0: return str(int(round((vis_km - 30) / 5 + 80)))
        return "89"
    except (ValueError, TypeError):
        return "//"

def encode_N(oktas: Optional[Any]) -> str:
    """Convert total cloud cover oktas (0-8, 9 for sky obscured) to 1-digit code N."""
    if oktas is None or str(oktas).strip() in ("", "/"):
        return "/"
    try:
        n = int(float(oktas))
        if 0 <= n <= 9:
            return str(n)
        return "/"
    except (ValueError, TypeError):
        return "/"

def encode_W(weather_val: Optional[Any]) -> str:
    """Convert past weather code (0-9) to 1-digit code W."""
    if weather_val is None or str(weather_val).strip() in ("", "/"):
        return "/"
    try:
        w = int(float(weather_val))
        if 0 <= w <= 9:
            return str(w)
        return "/"
    except (ValueError, TypeError):
        return "/"

def encode_ww(weather_val: Optional[Any]) -> str:
    """Convert present weather code (00-99) to 2-digit code ww."""
    if weather_val is None or str(weather_val).strip() in ("", "/"):
        return "//"
    try:
        ww = int(float(weather_val))
        if 0 <= ww <= 99:
            return f"{ww:02d}"
        return "//"
    except (ValueError, TypeError):
        return "//"


# ==============================================================================
# 3. CLOUD TABLES & HEIGHT ENCODERS
# ==============================================================================

def encode_cloud_type(cloud_type: Optional[Any]) -> str:
    """Encode low, middle, or high cloud type (0-9 or /)."""
    if cloud_type is None or str(cloud_type).strip() in ("", "/"):
        return "/"
    try:
        c = int(float(cloud_type))
        if 0 <= c <= 9:
            return str(c)
        return "/"
    except (ValueError, TypeError):
        return "/"

def encode_h(height_m: Optional[float]) -> str:
    """Convert lowest cloud base height in meters to 1-digit WMO code h."""
    if height_m is None or str(height_m).strip() == "":
        return "/"
    try:
        h = float(height_m)
        if h < 0: return "/"
        if h < 50: return "0"
        if h < 100: return "1"
        if h < 200: return "2"
        if h < 300: return "3"
        if h < 600: return "4"
        if h < 1000: return "5"
        if h < 1500: return "6"
        if h < 2000: return "7"
        if h < 2500: return "8"
        return "9"
    except (ValueError, TypeError):
        return "/"


# ==============================================================================
# 4. STATION & INDICATOR ENCODERS
# ==============================================================================

def encode_iR(precipitation_indicator: Optional[Any], rainfall: Optional[float] = None) -> str:
    """Encode precipitation indicator iR (1-4)."""
    if precipitation_indicator is not None and str(precipitation_indicator).strip() != "":
        return str(precipitation_indicator).strip()[0]
    if rainfall is not None and rainfall > 0:
        return "1"
    return "3"

def encode_iX(weather_indicator: Optional[Any]) -> str:
    """Encode weather indicator iX (1-7)."""
    if weather_indicator is not None and str(weather_indicator).strip() != "":
        return str(weather_indicator).strip()[0]
    return "1"

def encode_P(pressure_hpa: Optional[float]) -> str:
    """Convert pressure (station or MSL) in hPa to 4-digit WMO representation."""
    if pressure_hpa is None or str(pressure_hpa).strip() == "":
        return "////"
    try:
        p = float(pressure_hpa)
        p_tenths = int(round(p * 10.0))
        return f"{p_tenths:04d}"[-4:]
    except (ValueError, TypeError):
        return "////"

def encode_RRR(amount: Optional[float]) -> Optional[str]:
    """Encode precipitation amount in mm to 3-digit RRR code."""
    if amount is None or amount < 0:
        return None
    if amount == 0:
        return None
    if amount <= 0.05:
        return "990"
    if amount < 1.0:
        return f"99{int(round(amount * 10))}"
    if amount <= 988:
        return f"{int(round(amount)):03d}"
    return "989"


# ==============================================================================
# 5. SECTION ENCODERS (Section 0, Section 1, Section 3)
# ==============================================================================

def encode_section0(obs_date: str, obs_time: str, wind_unit: str, station_number: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Construct Section 0: Identifier & Header
    Format: AAXX YYGGiw IIiii
    """
    groups = []
    debug = []
    
    # Group 1: AAXX
    groups.append("AAXX")
    debug.append({
        "encoded": "AAXX",
        "raw_obs": "Fixed Land Station Identifier",
        "explanation": "Telegraphic report from fixed land station"
    })
    
    # Group 2: YYGGiw
    try:
        dt = datetime.strptime(obs_date, "%Y-%m-%d")
        yy = f"{dt.day:02d}"
    except Exception:
        yy = "//"
        
    try:
        gg = str(obs_time).split(":")[0].zfill(2)
    except Exception:
        gg = "//"
        
    iw = "4" if str(wind_unit).lower() in ("knots", "kt") else "1"
    yyggiw = f"{yy}{gg}{iw}"
    groups.append(yyggiw)
    debug.append({
        "encoded": yyggiw,
        "raw_obs": f"Date={obs_date}, Time={obs_time}, WindUnit={wind_unit}",
        "explanation": f"Day of month ({yy}), Hour UTC ({gg}), Wind unit indicator ({iw})"
    })
    
    # Group 3: IIiii (Station WMO Number)
    st = str(station_number).zfill(5)
    groups.append(st)
    debug.append({
        "encoded": st,
        "raw_obs": f"Station={station_number}",
        "explanation": f"WMO Station Index Number ({st})"
    })
    
    return groups, debug

def encode_section1(data: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Construct Section 1: Surface Data
    Format: iRiXhVV Nddff 1snTTT 2snTdTdTd 3P0P0P0P0 4PPPP 5appp 6RRRtR 7wwW1W2 8NhCLCMCH
    """
    groups = []
    debug = []
    
    # iRiXhVV
    ir = encode_iR(data.get("precipitation_indicator"), data.get("rainfall"))
    ix = encode_iX(data.get("weather_indicator"))
    h = encode_h(data.get("lowest_cloud_base"))
    vv = encode_vv(data.get("visibility"), data.get("visibility_unit", "meters"))
    g1 = f"{ir}{ix}{h}{vv}"
    groups.append(g1)
    debug.append({
        "encoded": g1,
        "raw_obs": f"iR={ir}, iX={ix}, BaseHeight={data.get('lowest_cloud_base')}, Vis={data.get('visibility')}",
        "explanation": "Precipitation & Weather indicators, cloud base, visibility"
    })
    
    # Nddff
    n = encode_N(data.get("total_cloud_cover"))
    raw_dir = str(data.get("wind_direction", "")).upper().strip()
    if raw_dir in COMPASS_TO_DD:
        dd = COMPASS_TO_DD[raw_dir]
    else:
        try:
            d_val = float(raw_dir)
            dd = f"{int(round(d_val / 10.0)):02d}"
        except Exception:
            dd = "//"
            
    try:
        ff_val = float(data.get("wind_speed"))
        ff = f"{int(round(ff_val)):02d}"
    except Exception:
        ff = "//"
        
    g2 = f"{n}{dd}{ff}"
    groups.append(g2)
    debug.append({
        "encoded": g2,
        "raw_obs": f"CloudCover={data.get('total_cloud_cover')}, WindDir={data.get('wind_direction')}, WindSpeed={data.get('wind_speed')}",
        "explanation": "Total cloud cover (N), wind direction (dd), wind speed (ff)"
    })
    
    # 1snTTT (Dry Bulb Temperature)
    try:
        tb = float(data.get("dry_bulb"))
        sn = "1" if tb < 0 else "0"
        ttt = f"{int(round(abs(tb) * 10.0)):03d}"[-3:]
        g3 = f"1{sn}{ttt}"
        groups.append(g3)
        debug.append({
            "encoded": g3,
            "raw_obs": f"DryBulb={tb}°C",
            "explanation": "Air temperature (dry bulb)"
        })
    except Exception:
        pass
        
    # 2snTdTdTd (Dew Point)
    try:
        td = float(data.get("dew_point"))
        sn = "1" if td < 0 else "0"
        ttt = f"{int(round(abs(td) * 10.0)):03d}"[-3:]
        g4 = f"2{sn}{ttt}"
        groups.append(g4)
        debug.append({
            "encoded": g4,
            "raw_obs": f"DewPoint={td}°C",
            "explanation": "Dew point temperature"
        })
    except Exception:
        pass

    # 3P0P0P0P0 (Station Pressure)
    try:
        sp = float(data.get("station_pressure"))
        p0 = encode_P(sp)
        g5 = f"3{p0}"
        groups.append(g5)
        debug.append({
            "encoded": g5,
            "raw_obs": f"StationPressure={sp} hPa",
            "explanation": "Station pressure"
        })
    except Exception:
        pass

    # 4PPPP (MSL Pressure)
    try:
        msl = float(data.get("msl_pressure"))
        p = encode_P(msl)
        g6 = f"4{p}"
        groups.append(g6)
        debug.append({
            "encoded": g6,
            "raw_obs": f"MSLPressure={msl} hPa",
            "explanation": "Mean sea level pressure"
        })
    except Exception:
        pass

    # 5appp (Pressure Tendency & Change)
    try:
        a = str(int(float(data.get("pressure_tendency"))))
        p_chg = float(data.get("pressure_change"))
        ppp = f"{int(round(p_chg * 10.0)):03d}"[-3:]
        g7 = f"5{a}{ppp}"
        groups.append(g7)
        debug.append({
            "encoded": g7,
            "raw_obs": f"Tendency={a}, Change={p_chg} hPa",
            "explanation": "Pressure tendency (a) and 3h pressure change (ppp)"
        })
    except Exception:
        pass

    # 6RRRtR (Section 1 Precipitation, if iR == 1)
    if ir == "1":
        try:
            rf = float(data.get("rainfall"))
            rrr = encode_RRR(rf)
            if rrr:
                tr = str(data.get("rain_duration") or "6")
                g8 = f"6{rrr}{tr}"
                groups.append(g8)
                debug.append({
                    "encoded": g8,
                    "raw_obs": f"Rainfall={rf} mm, Duration={tr}",
                    "explanation": "Precipitation amount (RRR) and duration (tR)"
                })
        except Exception:
            pass

    # 7wwW1W2 (Present & Past Weather, if iX in 1, 4)
    if ix in ("1", "4"):
        ww = encode_ww(data.get("present_weather"))
        w1 = encode_W(data.get("past_weather_1"))
        w2 = encode_W(data.get("past_weather_2"))
        if ww != "//" or w1 != "/" or w2 != "/":
            g9 = f"7{ww}{w1}{w2}"
            groups.append(g9)
            debug.append({
                "encoded": g9,
                "raw_obs": f"PresentWx={data.get('present_weather')}, PastWx1={data.get('past_weather_1')}, PastWx2={data.get('past_weather_2')}",
                "explanation": "Present weather (ww) and past weather (W1, W2)"
            })

    # 8NhCLCMCH (Cloud Details)
    nh = encode_N(data.get("low_cloud_amount"))
    cl = encode_cloud_type(data.get("low_cloud_type"))
    cm = encode_cloud_type(data.get("middle_cloud_type"))
    ch = encode_cloud_type(data.get("high_cloud_type"))
    if nh != "/" or cl != "/" or cm != "/" or ch != "/":
        g10 = f"8{nh}{cl}{cm}{ch}"
        groups.append(g10)
        debug.append({
            "encoded": g10,
            "raw_obs": f"LowAmt={nh}, CL={cl}, CM={cm}, CH={ch}",
            "explanation": "Low cloud amount (Nh) and cloud types (CL, CM, CH)"
        })

    return groups, debug

def encode_section3(data: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Construct Section 3: Regional Supplementary Data
    Format: 333 1snTxTxTx 2snTnTnTn 3Ejjj 5SSS 6RRRtR
    """
    groups = []
    debug = []
    
    max_t = data.get("sec333_max_temperature") or data.get("max_temperature")
    min_t = data.get("sec333_min_temperature") or data.get("min_temperature")
    gr_state = data.get("ground_state")
    sun = data.get("sunshine_hours")
    rf_24 = data.get("rainfall_24h")
    
    ir = encode_iR(data.get("precipitation_indicator"), data.get("rainfall"))
    has_sec3_rain = (ir == "2" and data.get("rainfall") is not None)
    has_sec3 = any(x is not None for x in [max_t, min_t, gr_state, sun, rf_24]) or has_sec3_rain
    
    if not has_sec3:
        return groups, debug

    # Section 3 Header: 333
    groups.append("333")
    debug.append({
        "encoded": "333",
        "raw_obs": "Section 3 Indicator",
        "explanation": "Regional supplementary data section"
    })
    
    # Section 3 Rainfall if iR == 2
    if has_sec3_rain:
        try:
            rf = float(data.get("rainfall"))
            rrr = encode_RRR(rf)
            if rrr:
                tr = str(data.get("rain_duration") or "6")
                g = f"6{rrr}{tr}"
                groups.append(g)
                debug.append({
                    "encoded": g,
                    "raw_obs": f"Section 3 Rain={rf} mm",
                    "explanation": "Section 3 Precipitation amount (RRR) and duration (tR)"
                })
        except Exception:
            pass

    # 1snTxTxTx (Max Temp)
    if max_t is not None:
        try:
            tx = float(max_t)
            sn = "1" if tx < 0 else "0"
            ttt = f"{int(round(abs(tx) * 10.0)):03d}"[-3:]
            g = f"1{sn}{ttt}"
            groups.append(g)
            debug.append({
                "encoded": g,
                "raw_obs": f"MaxTemp={tx}°C",
                "explanation": "Maximum air temperature"
            })
        except Exception:
            pass

    # 2snTnTnTn (Min Temp)
    if min_t is not None:
        try:
            tn = float(min_t)
            sn = "1" if tn < 0 else "0"
            ttt = f"{int(round(abs(tn) * 10.0)):03d}"[-3:]
            g = f"2{sn}{ttt}"
            groups.append(g)
            debug.append({
                "encoded": g,
                "raw_obs": f"MinTemp={tn}°C",
                "explanation": "Minimum air temperature"
            })
        except Exception:
            pass

    # 3Ejjj (Ground State)
    if gr_state is not None:
        try:
            e = str(int(float(gr_state)))
            g = f"3{e}///"
            groups.append(g)
            debug.append({
                "encoded": g,
                "raw_obs": f"GroundState={e}",
                "explanation": "State of ground (E)"
            })
        except Exception:
            pass

    # 5SSS (Sunshine)
    if sun is not None:
        try:
            s_val = float(sun)
            sss = f"{int(round(s_val * 10.0)):03d}"[-3:]
            g = f"5{sss}/"
            groups.append(g)
            debug.append({
                "encoded": g,
                "raw_obs": f"Sunshine={s_val}h",
                "explanation": "Duration of sunshine (SSS)"
            })
        except Exception:
            pass

    # 6RRRtR (24h Rainfall)
    if rf_24 is not None:
        try:
            r24 = float(rf_24)
            if r24 > 0:
                rrr = "990" if r24 <= 0.05 else f"{int(round(r24)):03d}"[-3:]
                g = f"6{rrr}4"
                groups.append(g)
                debug.append({
                    "encoded": g,
                    "raw_obs": f"24hRainfall={r24}mm",
                    "explanation": "24-hour precipitation amount"
                })
        except Exception:
            pass

    return groups, debug


# ==============================================================================
# 6. MAIN ENCODE ENTRY POINT
# ==============================================================================

def encode_synop(data: Dict[str, Any], station_number: str) -> Dict[str, Any]:
    """
    Master entry point for encoding observation records to SYNOP format.
    
    Parameters
    ----------
    data : dict
        Observation fields dictionary.
    station_number : str
        5-digit WMO station identifier.
        
    Returns
    -------
    dict
        Status, synop string, explanations dictionary, and detailed debug trace.
    """
    if not station_number or str(station_number).strip() == "":
        station_number = "99999"

    obs_date = data.get("observation_date", datetime.utcnow().strftime("%Y-%m-%d"))
    obs_time = data.get("observation_time", datetime.utcnow().strftime("%H:%M:%S"))
    wind_unit = data.get("wind_unit", "knots")

    all_groups = []
    all_debug = []

    # Encode Sections 0, 1, 3
    s0_grps, s0_dbg = encode_section0(obs_date, obs_time, wind_unit, station_number)
    all_groups.extend(s0_grps)
    all_debug.extend(s0_dbg)

    s1_grps, s1_dbg = encode_section1(data)
    all_groups.extend(s1_grps)
    all_debug.extend(s1_dbg)

    s3_grps, s3_dbg = encode_section3(data)
    all_groups.extend(s3_grps)
    all_debug.extend(s3_dbg)

    synop_string = " ".join(all_groups) + " ="

    # Build formatted debug report
    trace_lines = []
    trace_lines.append("=== WOMS SYNOP Encoding Report ===")
    trace_lines.append(f"Station: {station_number} | Date: {obs_date} {obs_time} UTC")
    trace_lines.append("-" * 40)
    for dbg in all_debug:
        trace_lines.append(f"[{dbg['encoded']:<10}] {dbg['raw_obs']} -> {dbg['explanation']}")
    trace_lines.append("-" * 40)
    trace_lines.append(f"Final SYNOP Message: {synop_string}")

    return {
        "status": "success",
        "synop": synop_string,
        "groups": all_groups,
        "explanations": {d["encoded"]: d["explanation"] for d in all_debug},
        "debug_trace": all_debug,
        "formatted_text": "\n".join(trace_lines)
    }


# ==============================================================================
# 7. BATCH ENCODING PROCESSOR
# ==============================================================================

def encode_synop_blocks(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process multiple observation records in batch."""
    results = []
    for rec in records:
        st_num = rec.get("station_number") or rec.get("station", "99999")
        res = encode_synop(rec, str(st_num))
        results.append(res)
    return results

def cmd_batch_encode(records: List[Dict[str, Any]]) -> None:
    """CLI batch encoder execution helper."""
    safe_print(f"Processing batch of {len(records)} observation records...")
    encoded = encode_synop_blocks(records)
    for idx, res in enumerate(encoded, 1):
        safe_print(f"\n--- Record #{idx} ---")
        safe_print(res["synop"])
        

# ==============================================================================
# 8. JSON CONVERTER & CLI ROUTER
# ==============================================================================

def result_to_json(result_dict: Dict[str, Any]) -> str:
    """Convert encoding result dictionary to formatted JSON string."""
    return json.dumps(result_dict, indent=4)

def save_output(filename: str, content: str) -> None:
    """Save generated string content to disk."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    safe_print(f"Saved output to: {filename}")

def main() -> None:
    """CLI Router entry point."""
    safe_print("=== WOMS SYNOP Encoding Engine CLI ===")
    if len(sys.argv) > 1 and sys.argv[1] == "--config":
        show_config()
        return

    # Demo sample observation
    sample_obs = {
        "observation_date": "2026-08-14",
        "observation_time": "12:00:00",
        "precipitation_indicator": "1",
        "weather_indicator": "1",
        "dry_bulb": 28.4,
        "dew_point": 21.2,
        "wind_direction": "SW",
        "wind_speed": 14.0,
        "wind_unit": "knots",
        "visibility": 8000,
        "station_pressure": 1005.2,
        "msl_pressure": 1011.8,
        "lowest_cloud_base": 800,
        "total_cloud_cover": 5,
        "rainfall": 2.5
    }
    res = encode_synop(sample_obs, "43279")
    safe_print(res["formatted_text"])


if __name__ == "__main__":
    main()
