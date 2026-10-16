@echo off
setlocal
title Forge3D Helmet Build
cd /d "%~dp0"
set "BLENDER_EXE=%FORGE3D_BLENDER%"
if not defined BLENDER_EXE (
  for /f "delims=" %%F in ('dir /b /s /o-n "C:\Program Files\Blender Foundation\Blender *\blender.exe" 2^>nul') do if not defined BLENDER_EXE set "BLENDER_EXE=%%F"
)
if not defined BLENDER_EXE (
  echo Blender was not found. Install Blender, or set FORGE3D_BLENDER to blender.exe.
  pause
  exit /b 1
)
"%BLENDER_EXE%" --background --python blender\forge3d_item_factory.py -- --recipe presets\futuristic_football_helmet.json --output output\helmet
echo.
echo Build complete. Check output\helmet.
pause
