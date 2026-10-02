@echo off
REM Detached relaunch helper used by the browser "Restart Manager" button.
REM Waits so the old node process can exit and free the port, then runs the normal launcher.
setlocal
set "PORT=%~1"
set "HOSTADDR=%~2"
if "%PORT%"=="" set "PORT=3220"
if "%HOSTADDR%"=="" set "HOSTADDR=0.0.0.0"
cd /d "%~dp0"
if not exist "%~dp0data" mkdir "%~dp0data"
>> "%~dp0data\restart.log" echo %DATE% %TIME% helper started port=%PORT% host=%HOSTADDR%
timeout /t 3 /nobreak >nul

if exist "%~dp0Start Ark Manager.cmd" (
  >> "%~dp0data\restart.log" echo %DATE% %TIME% launching Start Ark Manager.cmd silent
  call "%~dp0Start Ark Manager.cmd" silent -Port %PORT% -HostAddress "%HOSTADDR%"
  set "EC=%ERRORLEVEL%"
  >> "%~dp0data\restart.log" echo %DATE% %TIME% Start Ark Manager.cmd exited code=%EC%
) else if exist "%~dp0Start-ArkManager.ps1" (
  >> "%~dp0data\restart.log" echo %DATE% %TIME% Start Ark Manager.cmd missing; launching Start-ArkManager.ps1
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ArkManager.ps1" -NoBrowser -Port %PORT% -HostAddress "%HOSTADDR%"
  set "EC=%ERRORLEVEL%"
  >> "%~dp0data\restart.log" echo %DATE% %TIME% Start-ArkManager.ps1 exited code=%EC%
) else if exist "%~dp0server.mjs" (
  >> "%~dp0data\restart.log" echo %DATE% %TIME% Launchers missing; starting node server.mjs directly
  where node >nul 2>&1
  if errorlevel 1 (
    >> "%~dp0data\restart.log" echo %DATE% %TIME% node not found on PATH
    set "EC=1"
  ) else (
    start "Ark Server Manager" /min cmd /c "cd /d ""%~dp0"" && set ARK_PORT=%PORT%&& set ARK_HOST=%HOSTADDR%&& node server.mjs --no-open"
    set "EC=0"
    >> "%~dp0data\restart.log" echo %DATE% %TIME% node server.mjs started detached
  )
) else (
  >> "%~dp0data\restart.log" echo %DATE% %TIME% FATAL: no Start launcher and no server.mjs
  set "EC=1"
)

if not "%EC%"=="0" (
  echo Ark Manager failed to restart. See data\restart.log
  pause
)
exit /b %EC%
