@echo off
cd /d "%~dp0"
echo ============================================
echo   Job Finder - searching fresh offers...
echo ============================================
python -m jobfinder.main
echo.
pause
