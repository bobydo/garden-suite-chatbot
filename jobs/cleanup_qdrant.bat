@echo off
echo Starting Qdrant Cleanup...
powershell -ExecutionPolicy Bypass -File "%~dp0cleanup_simple.ps1"
pause