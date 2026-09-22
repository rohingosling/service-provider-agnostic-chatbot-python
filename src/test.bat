@echo off
REM Run the automated test suite (offline; no API key or network required).
REM Install the dev dependencies first: pip install -r test_requirements.txt
cd /d "%~dp0.."
python -m pytest tests %*
