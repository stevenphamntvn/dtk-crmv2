@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
python -m streamlit run streamlit_app.py --server.port 8506 --server.address localhost --server.headless false
if errorlevel 1 pause
