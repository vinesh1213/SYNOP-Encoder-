import urllib.request, json
data = {'station': '43279', 'observation_date': '2026-07-09', 'observation_time': '09:00:00', 'observer_name': 'System', 'observation_type': 'routine', 'is_validated': True, 'dry_bulb': 25.0, 'wet_bulb': 20.0, 'dew_point': 15.0, 'wind_direction': 'SW', 'wind_speed': 10.0, 'total_cloud_cover': 4, 'visibility': 5000, 'visibility_unit': 'meters', 'station_pressure': 1005.5, 'msl_pressure': 1012.0}
req = urllib.request.Request('http://localhost:8000/api/observations/', data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
try:
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except Exception as e:
    print(e.read().decode())
