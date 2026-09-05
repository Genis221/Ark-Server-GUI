@echo off
title Ark Survival Ascended Server Manager
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ArkManager.ps1"
if errorlevel 1 pause
