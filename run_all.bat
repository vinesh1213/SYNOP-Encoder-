@echo off
echo Starting WOMS Backend and Frontend Servers...

:: Start the backend in a new command window
start "WOMS Backend" cmd /k "cd woms_backend && run_backend.bat"

:: Start the frontend in a new command window
start "WOMS Frontend" cmd /k "cd woms_frontend && npm run dev"

echo Both servers are starting up! You can close this window.
