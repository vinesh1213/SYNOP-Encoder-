import math
from typing import Dict, Any, List, Optional
from datetime import datetime

class SynopEncodingEngine:
    def __init__(self):
        self.compass_to_dd = {
            'N': '36', 'NNE': '02', 'NE': '05', 'ENE': '07',
            'E': '09', 'ESE': '11', 'SE': '14', 'SSE': '16',
            'S': '18', 'SSW': '20', 'SW': '23', 'WSW': '25',
            'W': '27', 'WNW': '29', 'NW': '32', 'NNW': '34'
        }
        self.utc_times = ['00', '03', '06', '09', '12', '15', '18', '21']
        
        self.groups = []
        self.debug_trace = []
        self.calc_params = {}

    def _get_float(self, val: Any) -> Optional[float]:
        if val is None or str(val).strip() == '':
            return None
        try:
            return float(val)
        except ValueError:
            return None

    def _get_int(self, val: Any) -> Optional[int]:
        if val is None or str(val).strip() == '':
            return None
        try:
            return int(float(val))
        except ValueError:
            return None

    def _add_debug(self, raw_name, raw_val, calc_name, calc_val, encoded_group, explanation):
        if encoded_group:
            self.groups.append(encoded_group)
        self.debug_trace.append({
            'raw_obs': f'{raw_name}: {raw_val}',
            'calculated': f'{calc_name}: {calc_val}' if calc_name else None,
            'encoded': encoded_group,
            'explanation': explanation
        })

    def _derive_h(self, height_m: Optional[float]) -> Optional[str]:
        if height_m is None or height_m < 0: return None
        if height_m < 50: return '0'
        if height_m < 100: return '1'
        if height_m < 200: return '2'
        if height_m < 300: return '3'
        if height_m < 600: return '4'
        if height_m < 1000: return '5'
        if height_m < 1500: return '6'
        if height_m < 2000: return '7'
        if height_m < 2500: return '8'
        return '9'

    def _derive_VV(self, val: Optional[float], unit: str) -> Optional[str]:
        if val is None or val < 0: return None
        vis_m = val * 1000 if unit == 'km' else val
        if vis_m < 50: return '90'
        if vis_m == 50: return '91'
        if vis_m == 200: return '92'
        if vis_m == 500: return '93'
        if vis_m == 1000: return '94'
        if vis_m == 2000: return '95'
        if vis_m == 4000: return '96'
        if vis_m == 10000: return '97'
        if vis_m == 20000: return '98'
        if vis_m >= 50000: return '99'
        
        vis_km = vis_m / 1000.0
        if vis_km < 0.1: return '00'
        if vis_km <= 5.0: return f"{int(round(vis_km * 10)):02d}"
        if vis_km <= 30.0: return str(int(round(vis_km + 50)))
        if vis_km <= 70.0: return str(int(round((vis_km - 30) / 5 + 80)))
        return '89'
        
    def _encode_RRR(self, amount: float) -> Optional[str]:
        if amount is None or amount < 0:
            return None
        if amount == 0:
            return None # 0 is handled via iR=3 usually
        if amount <= 0.05:
            return '990'
        if amount < 1.0:
            return f"99{int(round(amount * 10))}"
        if amount <= 988:
            return f"{int(round(amount)):03d}"
        return '989'

    def phase1_validate(self, data: Dict[str, Any], station_number: str) -> List[str]:
        errors = []
        if not station_number: errors.append('Missing Station Number')
        else:
            try:
                if len(str(int(station_number))) > 5:
                    errors.append('Invalid station number')
            except:
                errors.append('Invalid station number')
        
        # Mandatory fields
        if self._get_float(data.get('dry_bulb')) is None:
            errors.append('Dry bulb temperature is required')
        if not data.get('precipitation_indicator'):
            errors.append('Precipitation indicator (iR) is required')
        if not data.get('weather_indicator'):
            errors.append('Weather indicator (iX) is required')

        return errors

    def phase2_calculate(self, data: Dict[str, Any]):
        self.calc_params = {}
        
        # Wind Direction Code
        raw_dir = data.get('wind_direction')
        if raw_dir in self.compass_to_dd:
            self.calc_params['wind_direction_code'] = self.compass_to_dd[raw_dir]
            
        # Wind Speed
        ws = self._get_float(data.get('wind_speed'))
        if ws is not None and ws >= 0:
            self.calc_params['average_wind_speed'] = ws

        # Cloud Base Height Code
        cb = self._get_float(data.get('lowest_cloud_base'))
        if cb is not None and cb >= 0:
            self.calc_params['cloud_base_code'] = self._derive_h(cb)

        # Visibility Code
        vis = self._get_float(data.get('visibility'))
        unit = data.get('visibility_unit', 'meters')
        if vis is not None and vis >= 0:
            self.calc_params['visibility_code'] = self._derive_VV(vis, unit)

    def encodeAAXX(self):
        self._add_debug('Fixed', 'AAXX', None, None, 'AAXX', 'Telegraphic report from fixed land station')

    def encodeYYGGiw(self, data):
        obs_date = data.get('observation_date', '')
        try:
            dt = datetime.strptime(obs_date, '%Y-%m-%d')
            yy = f'{dt.day:02d}'
        except:
            yy = '//'
            
        obs_time = data.get('observation_time', '')
        try:
            gg = str(obs_time).split(':')[0].zfill(2)
        except:
            gg = '//'
            
        iw = '4' if data.get('wind_unit') == 'knots' else '1'
        grp = f'{yy}{gg}{iw}'
        self._add_debug('Date/Time/WindUnit', f'{obs_date} {obs_time} {data.get("wind_unit")}', 
                       'YY, GG, iw', f'{yy}, {gg}, {iw}', 
                       grp, 'Day of month, hour in UTC, wind speed indicator')

    def encodeStation(self, station_number):
        st = str(station_number).zfill(5)
        self._add_debug('Station Number', station_number, 'IIiii', st, st, 'Station identifier')

    def encode_iRiXhVV(self, data):
        ir_val = str(data.get('precipitation_indicator', '/'))
        ix_val = str(data.get('weather_indicator', '/'))
        h_val = self.calc_params.get('cloud_base_code', '/')
        vv_str = self.calc_params.get('visibility_code', '//')
        
        grp = f'{ir_val}{ix_val}{h_val}{vv_str}'
        
        self._add_debug(
            'Rainfall, Weather, CloudBase, Visibility', 
            f'iR={ir_val}, iX={ix_val}, CloudBase={data.get("lowest_cloud_base")}m, Vis={data.get("visibility")}',
            'iR, iX, h, VV', f'{ir_val}, {ix_val}, {h_val}, {vv_str}', 
            grp, 
            'Precipitation indicator, weather indicator, cloud base height, visibility'
        )

    def encodeWind(self, data):
        cloud = self._get_int(data.get('total_cloud_cover'))
        n_val = str(cloud) if cloud is not None else '/'
        
        dd_val = self.calc_params.get('wind_direction_code', '//')
        
        avg_wind = self.calc_params.get('average_wind_speed')
        ff_val = f'{int(round(avg_wind)):02d}' if avg_wind is not None else '//'
        
        grp = f'{n_val}{dd_val}{ff_val}'
        self._add_debug('Cloud, WindDir, WindSpd', 
                       f'{cloud}, {data.get("wind_direction")}, {avg_wind}', 
                       'N, dd, ff', f'{n_val}, {dd_val}, {ff_val}', 
                       grp, 'Total cloud cover, wind direction, wind speed')

    def encodeTemperature(self, data):
        dry_bulb = self._get_float(data.get('dry_bulb'))
        if dry_bulb is not None:
            sn = '1' if dry_bulb < 0 else '0'
            ttt = f'{int(round(abs(dry_bulb) * 10)):03d}'[-3:]
            grp = f'1{sn}{ttt}'
            self._add_debug('Dry Bulb', f'{dry_bulb}°C', 'sn, TTT', f'{sn}, {ttt}', grp, 'Air temperature (dry bulb)')

    def encodeDewPoint(self, data):
        dew_point = self._get_float(data.get('dew_point'))
        if dew_point is not None:
            sn = '1' if dew_point < 0 else '0'
            ttt = f'{int(round(abs(dew_point) * 10)):03d}'[-3:]
            grp = f'2{sn}{ttt}'
            self._add_debug('Dew Point', f'{dew_point}°C', 'sn, TdTdTd', f'{sn}, {ttt}', grp, 'Dew point temperature')

    def encodeStationPressure(self, data):
        st_press = self._get_float(data.get('station_pressure'))
        if st_press is not None:
            val = f'{int(round(st_press * 10)):04d}'[-4:]
            grp = f'3{val}'
            self._add_debug('Station Pressure', f'{st_press} hPa', 'P0P0P0P0', val, grp, 'Station pressure')

    def encodeMSLPressure(self, data):
        msl_press = self._get_float(data.get('msl_pressure'))
        if msl_press is not None:
            val = f'{int(round(msl_press * 10)):04d}'[-4:]
            grp = f'4{val}'
            self._add_debug('MSL Pressure', f'{msl_press} hPa', 'PPPP', val, grp, 'Mean sea level pressure')

    def encodePressureTendency(self, data):
        tendency = self._get_int(data.get('pressure_tendency'))
        change = self._get_float(data.get('pressure_change'))
        if tendency is not None and change is not None:
            a = str(tendency)
            ppp = f'{int(round(change * 10)):03d}'[-3:]
            grp = f'5{a}{ppp}'
            self._add_debug('Press Tendency, Change', f'{tendency}, {change} hPa', 'a, ppp', f'{a}, {ppp}', grp, 'Pressure tendency and change')

    def encodeRainfall(self, data):
        iR = str(data.get('precipitation_indicator'))
        # Include if iR is 1 or 2 (precipitation group included)
        if iR in ['1', '2']:
            rainfall = self._get_float(data.get('rainfall'))
            if rainfall is not None and rainfall >= 0:
                rrr = self._encode_RRR(rainfall)
                if rrr is not None:
                    tr = str(data.get('rain_duration') or '6')
                    grp = f'6{rrr}{tr}'
                    section = "Section 1" if iR == '1' else "Section 3"
                    self._add_debug('Rainfall, Duration', f'{rainfall} mm, {tr}', 'RRR, tR', f'{rrr}, {tr}', grp, f'Precipitation amount and duration ({section})')

    def encodeWeather(self, data):
        iX = str(data.get('precipitation_indicator'))
        # iX=1 or 4 means 7-group is included
        # Wait, weather_indicator is iX.
        iX = str(data.get('weather_indicator'))
        if iX in ['1', '4']:
            ww_raw = data.get('present_weather')
            if ww_raw is not None and str(ww_raw).strip() != '':
                ww = f'{int(float(ww_raw)):02d}'
                
                w1_raw = data.get('past_weather_1')
                w1 = '/' if w1_raw is None or str(w1_raw).strip() == '' else str(int(float(w1_raw)))
                
                w2_raw = data.get('past_weather_2')
                w2 = '/' if w2_raw is None or str(w2_raw).strip() == '' else str(int(float(w2_raw)))
                
                grp = f'7{ww}{w1}{w2}'
                self._add_debug('Present Wx, Past Wx1, Wx2', f'{ww_raw}, {w1_raw}, {w2_raw}', 
                               'ww, W1, W2', f'{ww}, {w1}, {w2}', grp, 'Present and past weather')

    def encodeCloud(self, data):
        low_amt = '/' if data.get('low_cloud_amount') is None else str(int(float(data.get('low_cloud_amount'))))
        cl = '/' if data.get('low_cloud_type') is None else str(int(float(data.get('low_cloud_type'))))
        cm = '/' if data.get('middle_cloud_type') is None else str(int(float(data.get('middle_cloud_type'))))
        ch = '/' if data.get('high_cloud_type') is None else str(int(float(data.get('high_cloud_type'))))
        if low_amt != '/' or cl != '/' or cm != '/' or ch != '/':
            grp = f'8{low_amt}{cl}{cm}{ch}'
            self._add_debug('Low Amt, CL, CM, CH', f'{data.get("low_cloud_amount")}, {data.get("low_cloud_type")}, {data.get("middle_cloud_type")}, {data.get("high_cloud_type")}', 
                           'Nh, CL, CM, CH', f'{low_amt}, {cl}, {cm}, {ch}', grp, 'Cloud details')

    def encodeSection333(self, data):
        max_t = self._get_float(data.get('sec333_max_temperature'))
        min_t = self._get_float(data.get('sec333_min_temperature'))
        gr_state = self._get_int(data.get('ground_state'))
        sun = self._get_float(data.get('sunshine_hours'))
        rf_24 = self._get_float(data.get('rainfall_24h'))
        
        has_sec3 = any(x is not None for x in [max_t, min_t, gr_state, sun]) or (rf_24 is not None and rf_24 > 0)
        # Note: Section 3 rainfall (6RRRtR) is already handled in encodeRainfall if iR=2. We don't append it again here.
        # But wait, WMO standard says if it's Section 3, it should be printed AFTER '333'. So let's check iR.
        iR = str(data.get('precipitation_indicator'))
        rainfall = self._get_float(data.get('rainfall'))
        has_sec3_rain = (iR == '2' and rainfall is not None and rainfall >= 0)
        
        if has_sec3 or has_sec3_rain:
            self._add_debug('Section 333', 'Present', None, None, '333', 'Regional supplementary data')
            
            # Section 3 rainfall
            if has_sec3_rain:
                rrr = self._encode_RRR(rainfall)
                if rrr is not None:
                    tr = str(data.get('rain_duration') or '6')
                    grp = f'6{rrr}{tr}'
                    self._add_debug('Rainfall, Duration', f'{rainfall} mm, {tr}', 'RRR, tR', f'{rrr}, {tr}', grp, 'Precipitation amount and duration (Section 3)')
            
            if max_t is not None:
                sn = '1' if max_t < 0 else '0'
                ttt = f'{int(round(abs(max_t) * 10)):03d}'[-3:]
                grp = f'1{sn}{ttt}'
                self._add_debug('Max Temp', f'{max_t}°C', 'sn, TxTxTx', f'{sn}, {ttt}', grp, 'Maximum temperature')
                
            if min_t is not None:
                sn = '1' if min_t < 0 else '0'
                ttt = f'{int(round(abs(min_t) * 10)):03d}'[-3:]
                grp = f'2{sn}{ttt}'
                self._add_debug('Min Temp', f'{min_t}°C', 'sn, TnTnTn', f'{sn}, {ttt}', grp, 'Minimum temperature')
                
            if gr_state is not None:
                grp = f'3{gr_state}///'
                self._add_debug('Ground State', gr_state, 'E, jjj', f'{gr_state}, ///', grp, 'State of ground')
                
            if sun is not None:
                ss = f'{int(round(sun * 10)):03d}'[-3:]
                grp = f'5{ss}/'
                self._add_debug('Sunshine', f'{sun} hrs', 'SSS', ss, grp, 'Sunshine duration')
                
            if rf_24 is not None and rf_24 > 0:
                rrr = '990' if rf_24 <= 0.05 else f'{int(round(rf_24)):03d}'[-3:]
                grp = f'6{rrr}4'
                self._add_debug('24h Rainfall', f'{rf_24} mm', 'RRR, tR', f'{rrr}, 4', grp, '24h precipitation')

    def phase3_encode(self, data: Dict[str, Any], station_number: str):
        self.groups = []
        self.debug_trace = []
        
        self.encodeAAXX()
        self.encodeYYGGiw(data)
        self.encodeStation(station_number)
        self.encode_iRiXhVV(data)
        self.encodeWind(data)
        self.encodeTemperature(data)
        self.encodeDewPoint(data)
        self.encodeStationPressure(data)
        self.encodeMSLPressure(data)
        self.encodePressureTendency(data)
        # Note: If iR=2, encodeRainfall doesn't output anything, it's done in Section 333
        iR = str(data.get('precipitation_indicator'))
        if iR == '1':
            self.encodeRainfall(data)
        self.encodeWeather(data)
        self.encodeCloud(data)
        self.encodeSection333(data)

    def validate_synop(self) -> List[str]:
        errors = []
        if len(self.groups) < 3:
            errors.append('Insufficient groups generated')
        for grp in self.groups:
            if 'None' in grp:
                errors.append(f'Invalid characters in group: {grp}')
        return errors

    def validate_and_encode(self, data: Dict[str, Any], station_number: str) -> Dict[str, Any]:
        # Phase 1: Validate
        validation_errors = self.phase1_validate(data, station_number)
        if validation_errors:
            return {
                'status': 'error',
                'message': '[ERROR] SYNOP Generation Failed\n\nImpossible values rejected:\n' + '\n'.join(f'- {e}' for e in validation_errors)
            }
            
        # Phase 2: Calculate
        self.phase2_calculate(data)
        
        # Phase 3: Encode
        self.phase3_encode(data, station_number)
        
        # Validation
        synop_errors = self.validate_synop()
        if synop_errors:
            return {
                'status': 'error',
                'message': '[ERROR] SYNOP Generation Failed\n\nSYNOP validation errors:\n' + '\n'.join(f'- {e}' for e in synop_errors)
            }
            
        synop_str = ' '.join(self.groups) + ' ='
        
        # Build formatted output text
        out = []
        out.append('Validated Observation')
        out.append('-' * 25)
        for k, v in data.items():
            if v is not None and str(v).strip() != '' and k not in ['station', 'generated_synop', 'email_status']:
                out.append(f'- {k}: {v}')
        out.append('')
        
        out.append('Calculated Parameters')
        out.append('-' * 25)
        for k, v in self.calc_params.items():
            out.append(f'- {k}: {v}')
        out.append('')
        
        out.append('Individual SYNOP Groups (Debug Mode)')
        out.append('-' * 40)
        for d in self.debug_trace:
            out.append(f"Raw Observation: {d['raw_obs']}")
            if d['calculated']:
                out.append(f"Calculated Value: {d['calculated']}")
            out.append(f"Encoded Group: {d['encoded']}")
            out.append(f"Reason: {d['explanation']}")
            out.append('')
            
        out.append('Final SYNOP')
        out.append('-' * 25)
        out.append(synop_str)
        out.append('')
        
        out.append('Decoded SYNOP')
        out.append('-' * 25)
        out.append('\n'.join(self.groups))
        
        return {
            'status': 'success',
            'synop': synop_str,
            'explanations': {d['encoded']: d['explanation'] for d in self.debug_trace},
            'formatted_text': '\n'.join(out)
        }
