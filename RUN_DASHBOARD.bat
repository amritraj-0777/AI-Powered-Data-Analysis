@echo off
cd /d "%~dp0"
set PY=
if exist "%USERPROFILE%\anaconda3\python.exe" set PY=%USERPROFILE%\anaconda3\python.exe
if not defined PY if exist "%USERPROFILE%\miniconda3\python.exe" set PY=%USERPROFILE%\miniconda3\python.exe
if not defined PY where python >nul 2>&1 && set PY=python
if not defined PY where py >nul 2>&1 && set PY=py
if not defined PY (echo Python not found. & pause & exit /b 1)

REM Free port 8502 so we never get "Port already in use"
for /f "tokens=6" %%a in ('netstat -ano 2^>nul ^| findstr ":8502"') do taskkill /F /PID %%a 2>nul

echo.
echo  Step 1: Wait until you see "You can now view your app"
echo  Step 2: Open your browser:  http://localhost:8502
echo  Step 3: To stop, close this window.
echo.
"%PY%" -m pip install -q streamlit pandas openpyxl plotly numpy 2>nul
"%PY%" -m streamlit run dashboard.py --server.port 8502
pause
