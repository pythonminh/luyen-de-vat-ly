@echo off
chcp 65001 >nul
cd /d "%~dp0"
python app.py --convert "Luyện Đề Vật Lý.xlsx" --json luyen_de_vat_ly.json --users users.json
pause
