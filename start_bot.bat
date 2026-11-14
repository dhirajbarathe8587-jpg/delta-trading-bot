@echo off
title Delta Exchange 24/7 Multi-Currency Scanner & Trading Bot
color 0A
cd /d "%~dp0"

echo ======================================================================
echo    Starting Delta Exchange Multi-Currency Scanner & Scalper Bot...
echo ======================================================================
echo.
python bot.py
pause
