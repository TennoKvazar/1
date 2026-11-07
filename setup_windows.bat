@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 (
    echo ERROR: Install Python 3.12 (64-bit) and enable the py launcher.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail
echo Setup complete. Double-click start_windows.bat
pause
exit /b 0
:fail
echo Installation failed. Copy the error message and send it in our chat.
pause
exit /b 1
