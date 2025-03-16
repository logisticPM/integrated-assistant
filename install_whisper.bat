@echo off
echo ========================================================
echo Integrated Assistant - Whisper Installation
echo ========================================================
echo.

:: Check if pip is available
where pip >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: pip not found. Please make sure Python is installed correctly.
    exit /b 1
)

:: Check if FFmpeg is installed
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo FFmpeg is not installed. It is required for Whisper to work properly.
    echo.
    echo Step 1: Installing ffmpeg-python package...
    pip install ffmpeg-python
    
    echo.
    echo Step 2: You need to install FFmpeg manually:
    echo 1. Download FFmpeg from https://ffmpeg.org/download.html
    echo    (Get the "Windows builds" from BtbN: https://github.com/BtbN/FFmpeg-Builds/releases)
    echo 2. Extract the zip file to a folder (e.g., C:\ffmpeg)
    echo 3. Add the bin folder to your PATH environment variable
    echo    (e.g., C:\ffmpeg\bin)
    echo.
    echo After installing FFmpeg, please restart this script.
    echo.
    pause
    exit /b 1
)

echo FFmpeg is already installed. Proceeding with Whisper installation...
echo.

:: Install PyTorch
echo Step 1: Installing PyTorch...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Warning: Failed to install PyTorch with CUDA support.
    echo Trying to install CPU-only version...
    pip install torch torchvision torchaudio
)

:: Install Whisper dependencies
echo.
echo Step 2: Installing Whisper dependencies...
pip install setuptools-rust

:: Install Whisper
echo.
echo Step 3: Installing openai-whisper...
pip install openai-whisper

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Failed to install openai-whisper. Please check the error messages above.
    exit /b 1
)

echo.
echo ========================================================
echo Whisper installation completed!
echo ========================================================
echo.
echo Now running the Whisper setup script to download models and configure settings...
echo.

:: Run the Whisper setup script
python scripts\setup_whisper.py

echo.
echo If you encounter any issues, please check the troubleshooting
echo section in the README.md file.
echo.
pause
