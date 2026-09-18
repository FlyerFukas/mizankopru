@echo off
chcp 65001 >nul
title MizanKopru Paneli
cd /d "%~dp0"
echo.
echo   MizanKopru paneli baslatiliyor...
echo   Tarayici otomatik acilacak. Kapatmak icin bu pencerede Ctrl+C.
echo.
py src\panel.py
pause
