@echo off
setlocal ENABLEDELAYEDEXPANSION
REM Automated setup for Windows Server/Windows 10+
REM - Detects/installs Python venv and dependencies
REM - Detects ffmpeg.exe and writes FFMPEG_PATH user env var
REM - Creates a Windows service using NSSM (if available) or Task Scheduler fallback
REM
REM Usage (Run as Administrator):
REM   setup_server_windows.bat

set PROJECT_DIR=%~dp0
set VENV_DIR=%PROJECT_DIR%\.venv
set PY_EXE=python
set SERVICE_NAME=DownloaderBot

REM Check admin rights
openfiles >nul 2>&1
if NOT %errorlevel%==0 (
  echo [ERROR] Please run this script as Administrator.
  exit /b 1
)

REM Ensure Python exists
where %PY_EXE% >nul 2>&1
if NOT %errorlevel%==0 (
  echo [ERROR] Python not found in PATH. Install Python 3 and re-run.
  exit /b 1
)

REM Create venv if missing
if NOT exist "%VENV_DIR%" (
  echo [INFO] Creating virtual environment at %VENV_DIR%
  %PY_EXE% -m venv "%VENV_DIR%"
) else (
  echo [INFO] Virtual environment already exists.
)

REM Upgrade pip and install requirements
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip wheel
if exist "%PROJECT_DIR%\requirements.txt" (
  "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%PROJECT_DIR%\requirements.txt"
) else (
  echo [WARN] requirements.txt not found; skipping dependency install
)

REM Detect ffmpeg
set FFMPEG_EXE=
for %%I in (ffmpeg.exe) do set FFMPEG_EXE=%%~$PATH:I
if "%FFMPEG_EXE%"=="" (
  REM Try common locations
  if exist "C:\ffmpeg\bin\ffmpeg.exe" set FFMPEG_EXE=C:\ffmpeg\bin\ffmpeg.exe
)
if "%FFMPEG_EXE%"=="" (
  echo [WARN] ffmpeg.exe not found in PATH. Set it manually later.
) else (
  echo [INFO] Found ffmpeg at %FFMPEG_EXE%
  setx FFMPEG_PATH "%FFMPEG_EXE%" >nul
)

REM Try to create a Windows service with NSSM if exists
where nssm >nul 2>&1
if %errorlevel%==0 (
  echo [INFO] Creating Windows service via NSSM: %SERVICE_NAME%
  nssm install %SERVICE_NAME% "%VENV_DIR%\Scripts\python.exe" "%PROJECT_DIR%\bot.py"
  nssm set %SERVICE_NAME% AppDirectory "%PROJECT_DIR%"
  nssm set %SERVICE_NAME% AppEnvironmentExtra "FFMPEG_PATH=%FFMPEG_EXE%"
  nssm set %SERVICE_NAME% AppStdout "%PROJECT_DIR%\service.log"
  nssm set %SERVICE_NAME% AppStderr "%PROJECT_DIR%\service.err.log"
  nssm set %SERVICE_NAME% Start SERVICE_AUTO_START
  nssm restart %SERVICE_NAME%
  echo [SUCCESS] Service %SERVICE_NAME% installed and started.
) else (
  echo [INFO] NSSM not found. Creating a Task Scheduler task as fallback.
  schtasks /Create /TN %SERVICE_NAME% /TR "\"%VENV_DIR%\Scripts\python.exe\" \"%PROJECT_DIR%\bot.py\"" /SC ONSTART /RL HIGHEST /RU SYSTEM /F
  echo [SUCCESS] Scheduled task %SERVICE_NAME% created to run on startup.
)

echo [DONE] Setup completed. To view logs on Windows service mode, check service.log and service.err.log
endlocal