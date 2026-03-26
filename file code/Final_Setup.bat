@echo off
echo ==========================================
echo      Todo Pro Installer (Global/English)
echo ==========================================
echo.

cd /d "%~dp0"

:: 1. Clean up old environment
if exist venv (
    echo [INFO] Cleaning up old environment...
    rmdir /s /q venv
)

:: 2. Create new environment
echo [INFO] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Python not found or permission denied.
    pause
    exit
)

:: 3. Install dependencies (STANDARD PYPI, NO MIRRORS)
echo [INFO] Upgrading pip...
call venv\Scripts\activate
python -m pip install --upgrade pip

echo.
echo [INFO] Installing libraries from official PyPI...
echo (This might take a few minutes depending on your network)
pip install click rich pywebview plyer pyngrok

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation failed!
    echo Please check your internet connection.
    pause
    exit
)

echo.
echo ==========================================
echo [SUCCESS] Installation Complete!
echo You can now double-click 'TodoPro.vbs'
echo ==========================================
pause