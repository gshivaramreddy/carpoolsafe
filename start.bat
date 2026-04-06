@echo off
echo.
echo  ============================================
echo   CarpoolSafe - Full Stack Carpooling App
echo  ============================================
echo.

echo [1/3] Installing backend dependencies...
pip install -r backend\requirements.txt -q

echo [2/3] Installing frontend dependencies...
pip install -r frontend\requirements.txt -q

echo [3/3] Starting backend...
start "CarpoolSafe Backend" cmd /k python run_backend.py

timeout /t 5 /nobreak > nul

echo Starting frontend...
cd frontend
set BACKEND_URL=http://localhost:8000

for /f "tokens=2 delims==" %%a in ('findstr "GOOGLE_MAPS_API_KEY" ..\.env') do set GOOGLE_MAPS_API_KEY=%%a

streamlit run app.py
