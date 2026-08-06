@echo off
echo Starting WOMS Weather Observation Portal Frontend...
echo Opening browser at http://localhost:5173
start http://localhost:5173
cd woms_frontend
python -m http.server 5173
pause
