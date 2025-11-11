@echo off
title Starting All Bots
color 0A

echo ========================================
echo   Starting All Bots
echo ========================================
echo.
echo [1/2] Starting Main Bot (bot.py)...
start "Main Bot" cmd /k "python bot.py"
timeout /t 3 /nobreak >nul

echo [2/2] Starting Delivery Bot (bot2.py)...
start "Delivery Bot" cmd /k "python bot2.py"

echo.
echo ========================================
echo   All Bots Started Successfully!
echo ========================================
echo.
echo Main Bot: Running in separate window
echo Delivery Bot: Running in separate window
echo.
echo Press any key to exit this window...
pause >nul
