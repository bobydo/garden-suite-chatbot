@echo off
REM Qdrant Cleanup - Clear all vector collections
REM This batch file runs the PowerShell cleanup script

echo Starting Qdrant Cleanup...
echo.

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0cleanup_qdrant.ps1"

echo.
pause