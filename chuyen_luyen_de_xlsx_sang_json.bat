@echo off
chcp 65001 >nul
cd /d "%~dp0"
python app_luyen_de_json_full.py --convert "Luyện Đề Vật Lý.xlsx" --json luyen_de_vat_ly.json
pause
