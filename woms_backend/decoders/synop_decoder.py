import re
import math
from typing import List, Dict, Any, Tuple

class SynopDecoder:
    def __init__(self):
        pass

    def decode_file(self, file_path: str) -> List[Dict[str, Any]]:
        results = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            blocks = self.extract_synop_blocks(content)
            for block, line_num, _ in blocks:
                decoded = self.decode_message(block)
                decoded["line_number"] = line_num
                results.append(decoded)
        except Exception as e:
            results.append({"error": f"File read error: {str(e)}", "valid": False, "line_number": 0, "raw": ""})
            
        return results

    def extract_synop_blocks(self, text: str) -> List[Tuple[str, int, dict]]:
        blocks = []
        lines = text.split('\n')
        current_block = []
        in_synop = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Skips non-synop lines
            if not line or line.startswith('TOT:') or line.startswith('SMIN90'):
                continue
            if any(line.startswith(x) for x in ['BBXX', 'METAR', 'TTAA', 'TTBB', 'USIN', 'UKIN', 'TEMP', 'SHIP']):
                continue
                
            if line.startswith('AAXX'):
                in_synop = True
                current_block = [line]
                if '=' in line:
                    in_synop = False
                    clean_block = ' '.join(current_block).replace('=', '').strip()
                    blocks.append((clean_block, i + 1, {}))
                    current_block = []
                continue
                
            if in_synop:
                current_block.append(line)
                if '=' in line:
                    in_synop = False
                    clean_block = ' '.join(current_block).replace('=', '').strip()
                    blocks.append((clean_block, i + 1, {}))
                    current_block = []
                    
        return blocks

    def decode_message(self, synop_string: str) -> Dict[str, Any]:
        raw = synop_string.replace('\n', ' ').strip()
        raw = re.sub(r'\s+', ' ', raw)
        
        tokens = raw.split()
        if not tokens or tokens[0].upper() != 'AAXX':
            return {"raw": raw, "error": "First word is not AAXX", "valid": False}
            
        if len(tokens) < 3:
            return {"raw": raw, "error": "Incomplete header", "valid": False}
            
        header = tokens[1]
        station = tokens[2]
        groups = tokens[3:]
        
        try:
            idx_333 = groups.index('333')
            sec1_groups = groups[:idx_333]
            sec3_groups = groups[idx_333+1:]
        except ValueError:
            sec1_groups = groups
            sec3_groups = []
            
        iw = header[4] if len(header) >= 5 else '/'
        parsed = {
            "station": station,
            "header": self.decode_section0(header),
            "section1": self.decode_section1(sec1_groups, iw),
            "section3": self.decode_section3(sec3_groups)
        }
        
        return {
            "raw": raw,
            "groups": groups,
            "valid": True,
            "parsed": parsed
        }

    def decode_section0(self, header: str) -> Dict[str, str]:
        if len(header) < 5: return {}
        return {
            "day": header[:2],
            "hour_utc": header[2:4],
            "wind_indicator_code": header[4]
        }

    def decode_section1(self, groups: List[str], iw: str) -> Dict[str, Any]:
        parsed = {}
        if len(groups) > 0 and len(groups[0]) == 5:
            g = groups[0]
            parsed["precip_indicator"] = self.decode_iR(g[0])
            parsed["station_type"] = self.decode_iX(g[1])
            parsed["cloud_base"] = self.decode_h(g[2])
            parsed["visibility"] = self.decode_vv(g[3:5])
        if len(groups) > 1 and len(groups[1]) == 5:
            g = groups[1]
            parsed["cloud_cover"] = self.decode_N(g[0])
            parsed["wind_direction_compass"] = self.dd_to_compass(g[1:3])
            parsed["wind_speed"] = int(g[3:5]) if g[3:5].isdigit() else g[3:5]
            if iw in ('0', '1'):
                parsed["wind_unit"] = "m/s"
            elif iw in ('3', '4'):
                parsed["wind_unit"] = "knots"
            else:
                parsed["wind_unit"] = "units"
            
        for g in groups[2:]:
            if len(g) != 5: continue
            if g.startswith('1'):
                sn = 1 if g[1] == '0' else -1
                if g[2:5].isdigit(): parsed["temp_dry_bulb_c"] = sn * int(g[2:5]) / 10.0
            elif g.startswith('2'):
                sn = 1 if g[1] == '0' else -1
                if g[2:5].isdigit(): parsed["dew_point_c"] = sn * int(g[2:5]) / 10.0
            elif g.startswith('3'):
                parsed["station_pressure_hpa"] = self.decode_P(g[1:5])
            elif g.startswith('4'):
                parsed["sea_level_pressure_hpa"] = self.decode_P(g[1:5])
            elif g.startswith('5'):
                if g[2:5].isdigit(): parsed["pressure_tendency_hpa"] = int(g[2:5]) / 10.0
            elif g.startswith('6'):
                if g[1:4].isdigit(): parsed["precipitation_mm"] = int(g[1:4])
            elif g.startswith('7'):
                parsed["present_weather_desc"] = self.decode_ww(g[1:3])
                parsed["past_weather_W1_desc"] = self.decode_W(g[3])
                parsed["past_weather_W2_desc"] = self.decode_W(g[4])
            elif g.startswith('8'):
                parsed["cloud_types"] = self.decode_cloud_type(g[2], g[3], g[4])
        return parsed

    def decode_section3(self, groups: List[str]) -> Dict[str, Any]:
        parsed = {}
        for g in groups:
            if len(g) != 5: continue
            if g.startswith('1'):
                sn = 1 if g[1] == '0' else -1
                if g[2:5].isdigit(): parsed["max_temp_c"] = sn * int(g[2:5]) / 10.0
            elif g.startswith('2'):
                sn = 1 if g[1] == '0' else -1
                if g[2:5].isdigit(): parsed["min_temp_c"] = sn * int(g[2:5]) / 10.0
            elif g.startswith('3'):
                if len(g) == 5 and g[1] == 'E':
                    parsed["ground_state"] = g[2:5] # 3Ejjj -> snow/ground state
                else:
                    parsed["ground_state_code"] = g[1]
                    parsed["snow_depth"] = g[2:5]
            elif g.startswith('5'):
                # 5SSS format according to prompt
                parsed["sunshine_duration"] = g[1:]
            elif g.startswith('6'):
                if g[1:4].isdigit(): parsed["precipitation_mm_24h"] = int(g[1:4])
        return parsed

    # Helpers
    def dd_to_compass(self, dd: str) -> str:
        if dd == "00": return "Calm"
        if dd == "99": return "Variable"
        try:
            val = int(dd)
            deg = val * 10
            dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            idx = round(deg / 22.5) % 16
            return f"{dirs[idx]} ({deg} deg)"
        except: return f"{dd} (unknown)"

    def decode_vv(self, vv: str) -> str:
        try:
            val = int(vv)
            if val == 0: return "< 0.1 km"
            if 1 <= val <= 50: return f"{val / 10} km"
            if 56 <= val <= 80: return f"{val - 50} km"
            if val == 90: return "Very thick fog < 0.05 km"
            if val == 91: return "Thick fog 0.05 km"
            if val == 97: return "10 km"
            if val == 99: return ">= 50 km"
            return f"Code {vv}"
        except: return f"Code {vv}"

    def decode_N(self, N: str) -> str:
        mapping = {'0': "SKC Clear", '1': "FEW", '2': "FEW", '3': "SCT", '4': "SCT", 
                   '5': "BKN", '6': "BKN", '7': "OVC Overcast", '8': "OVC Overcast", '9': "Sky obscured", '/': "Not observed"}
        desc = mapping.get(N, f"Code {N}")
        if N.isdigit() and int(N) <= 8: return f"{desc} ({N} oktas)"
        return desc

    def decode_W(self, W: str) -> str:
        mapping = {'0': "Cloud covering 1/2 or less", '1': "Cloud variable", '2': "Cloud > 1/2 throughout", 
                   '3': "Sandstorm/duststorm/blowing snow", '4': "Fog or ice fog or thick haze", '5': "Drizzle",
                   '6': "Rain", '7': "Snow or rain and snow", '8': "Shower(s)", '9': "Thunderstorm"}
        return mapping.get(W, f"Code {W}")

    def decode_ww(self, ww: str) -> str:
        try:
            val = int(ww)
            if 0 <= val <= 9: return "No precipitation"
            if 10 <= val <= 19: return "Visibility phenomena (mist, fog patches, TS no precip)"
            if 20 <= val <= 29: return "Recent weather (past hour)"
            if 30 <= val <= 39: return "Duststorm/sandstorm/blowing snow"
            if 40 <= val <= 49: return "FOG / ICE FOG"
            if 50 <= val <= 59: return "Drizzle"
            if 60 <= val <= 69: return "Rain"
            if 70 <= val <= 79: return "Snow"
            if 80 <= val <= 90: return "Showers"
            if 91 <= val <= 99: return "Thunderstorms TS/TSRA"
        except: pass
        return f"Code {ww}"

    def decode_cloud_type(self, CL: str, CM: str, CH: str) -> str:
        return f"CL={CL}, CM={CM}, CH={CH}"

    def decode_h(self, h: str) -> str:
        mapping = {'0': "< 50m", '1': "50-100m", '2': "100-200m", '3': "200-300m", '4': "300-600m",
                   '5': "600-1000m", '6': "1000-1500m", '7': "1500-2000m", '8': "2000-2500m", '9': ">= 2500m"}
        return mapping.get(h, f"Code {h}")

    def decode_iR(self, iR: str) -> str:
        mapping = {'0': "Precip in Sec1 and Sec3", '1': "Precip in Sec1 only", '2': "Precip in Sec3 only",
                   '3': "No precipitation", '4': "Station not staffed"}
        return mapping.get(iR, f"Code {iR}")

    def decode_iX(self, iX: str) -> str:
        mapping = {'1': "Manned, wx included", '2': "Manned, wx omitted", 
                   '4': "Automatic, wx included", '5': "Automatic, wx omitted"}
        return mapping.get(iX, f"Code {iX}")

    def decode_P(self, PPPP: str) -> float:
        if PPPP == "////": return None
        try:
            val = int(PPPP)
            if val < 5000: val += 10000
            return val / 10.0
        except: return None
