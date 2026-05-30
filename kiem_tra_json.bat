@echo off
chcp 65001 >nul
cd /d "%~dp0"
python app.py --check --json luyen_de_vat_ly.json --users users.json
pause
