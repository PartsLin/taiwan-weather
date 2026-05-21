@echo off
start "Weather API (port 3002)" cmd /k "cd /d %~dp0weather-api && python app.py"
start "Weather UI (port 3001)" cmd /k "cd /d %~dp0temperature-dashboard && set PORT=3001 && npm start"
