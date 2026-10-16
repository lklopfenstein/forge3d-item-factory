@echo off
setlocal
title Forge3D Item Factory
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 local_server.py
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python local_server.py
  ) else (
    echo Python 3 was not found. Install it free from python.org and try again.
    pause
  )
)
