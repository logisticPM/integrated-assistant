@echo off
echo ========================================================
echo Integrated Assistant - Dependency Installation
echo ========================================================
echo.

:: Check if pip is available
where pip >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: pip not found. Please make sure Python is installed correctly.
    exit /b 1
)

:: Install core dependencies first
echo Step 1: Installing core dependencies...
pip install flask pyyaml numpy requests

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Failed to install core dependencies. Please check the error messages above.
    exit /b 1
)

:: Install visualization dependencies
echo.
echo Step 2: Installing visualization and analysis dependencies...
pip install matplotlib pandas seaborn scikit-learn

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Warning: Some visualization dependencies could not be installed.
    echo The application may have limited functionality.
    echo.
)

:: Install remaining dependencies from requirements.txt
echo.
echo Step 3: Installing remaining dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ========================================================
echo Dependencies installed successfully!
echo ========================================================
echo.
echo You can now run the setup script with: python scripts\setup_all.py
echo Or start the application directly with: python start.py
echo.
echo If you encounter any issues, please check the troubleshooting
echo section in the README.md file.
echo.
pause
