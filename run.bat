@echo off
REM ============================================================
REM run.bat — Social-Downloader Direct Runner for Windows
REM Simple script to run without Docker
REM ============================================================

echo ============================================================
echo  Social-Downloader - Direct Runner (Windows)
echo  Running without Docker
echo ============================================================
echo.

REM ============================================================
REM Step 1: Check Python 3
REM ============================================================
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

python --version
echo [OK] Python found
echo.

REM ============================================================
REM Step 2: Check ffmpeg
REM ============================================================
echo [2/6] Checking ffmpeg installation...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] ffmpeg is not installed or not in PATH
    echo ffmpeg is required for video downloads and processing.
    echo Please download from https://ffmpeg.org/download.html
    echo.
    set /p CONTINUE="Continue without ffmpeg? (y/N): "
    if /i not "%CONTINUE%"=="y" exit /b 1
) else (
    ffmpeg -version | findstr "ffmpeg version"
    echo [OK] ffmpeg found
)
echo.

REM ============================================================
REM Step 3: Check .env file
REM ============================================================
echo [3/6] Checking environment configuration...
if not exist ".env" (
    echo [ERROR] .env file not found
    echo Please create .env file from .env.example:
    echo   copy .env.example .env
    echo   notepad .env  # Edit with your credentials
    pause
    exit /b 1
)

findstr /C:"BOT_TOKEN=your_" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo [ERROR] BOT_TOKEN not configured in .env
    echo Please edit .env file and set proper values
    pause
    exit /b 1
)

echo [OK] Environment configuration OK
echo.

REM ============================================================
REM Step 4: Create virtual environment
REM ============================================================
echo [4/6] Setting up virtual environment...
if not exist "venv" (
    echo Creating new virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)
echo.

REM ============================================================
REM Step 5: Install dependencies
REM ============================================================
echo [5/6] Installing dependencies...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip >nul

REM Install requirements
if exist "requirements.txt" (
    echo Installing packages from requirements.txt...
    pip install -r requirements.txt
    echo [OK] Dependencies installed
) else (
    echo [ERROR] requirements.txt not found
    pause
    exit /b 1
)
echo.

REM ============================================================
REM Step 6: Create required directories
REM ============================================================
echo [6/6] Creating required directories...
if not exist "logs" mkdir logs
if not exist "downloads" mkdir downloads
if not exist "data\cookies" mkdir data\cookies
if not exist "data\cookies_tmp" mkdir data\cookies_tmp
if not exist "data\sessions" mkdir data\sessions
if not exist "data\database" mkdir data\database
echo [OK] Directories created
echo.

REM ============================================================
REM Launch bot
REM ============================================================
echo ============================================================
echo [OK] All checks passed - Starting bot...
echo ============================================================
echo.
echo Bot is starting. Press Ctrl+C to stop.
echo.

REM Run the bot
python bot.py

pause
