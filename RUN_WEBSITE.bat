@echo off
cd /d "%~dp0"
set PY=
if exist "%USERPROFILE%\anaconda3\python.exe" set PY=%USERPROFILE%\anaconda3\python.exe
if not defined PY if exist "%USERPROFILE%\miniconda3\python.exe" set PY=%USERPROFILE%\miniconda3\python.exe
if not defined PY where python >nul 2>&1 && set PY=python
if not defined PY where py >nul 2>&1 && set PY=py
if not defined PY (echo Python not found. & pause & exit /b 1)

REM Free port 5000 if already in use
for /f "tokens=6" %%a in ('netstat -ano 2^>nul ^| findstr ":5000"') do taskkill /F /PID %%a 2>nul

echo.
echo  Website dashboard (Flask) - no Streamlit
echo  Step 1: Wait until you see "Open in browser: http://localhost:5000"
echo  Step 2: Open your browser and go to:  http://localhost:5000
echo  Step 3: To stop, close this window.
echo.
"%PY%" -m pip install -q flask pandas openpyxl plotly 2>nul
"%PY%" dashboard_web.py
pause
