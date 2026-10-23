@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set /p CRM_PACKAGE=Duong dan goi ZIP cap nhat V2: 
python tools\update.py "%CRM_PACKAGE%"
pause
