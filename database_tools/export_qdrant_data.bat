@echo off
echo Garden Suite Chatbot - Qdrant Data Export
echo.

cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "export_qdrant_data.ps1"

echo.
pause