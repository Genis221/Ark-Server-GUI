@echo off
setlocal EnableExtensions
title Ark Server Manager — Reset admin password

REM One-shot helper: starts the manager with ARK_RESET_ADMIN_PASSWORD=1 so the
REM admin password is reset and printed in the console (or use ARK_ADMIN_PASSWORD).

cd /d "%~dp0"
echo This will reset the admin password and sign everyone out of that account.
echo.
if defined ARK_ADMIN_PASSWORD (
  echo Using ARK_ADMIN_PASSWORD from the environment.
) else (
  echo A new temporary password will be printed in the Ark Manager console after start.
)
echo.
pause
set "ARK_RESET_ADMIN_PASSWORD=1"
if exist "%~dp0Start Ark Manager.cmd" (
  call "%~dp0Start Ark Manager.cmd" %*
) else (
  echo Start Ark Manager.cmd not found — launching node directly.
  node "%~dp0server.mjs"
)
