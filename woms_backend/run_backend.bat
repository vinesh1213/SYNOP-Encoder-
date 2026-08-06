@echo off
echo Starting Weather Observation Management System Backend...
cd /d "%~dp0"

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Upgrading pip and installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Starting FastAPI server at http://localhost:8000/docs ...
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
