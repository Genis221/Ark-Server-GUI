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
>> "%~dp0data\restart.log" echo %DATE% %TIME% launching Start Ark Manager.cmd silent
call "%~dp0Start Ark Manager.cmd" silent -Port %PORT% -HostAddress "%HOSTADDR%"
set "EC=%ERRORLEVEL%"
>> "%~dp0data\restart.log" echo %DATE% %TIME% Start Ark Manager.cmd exited code=%EC%
if not "%EC%"=="0" (
  echo Ark Manager failed to restart. See data\restart.log
  pause
)
exit /b %EC%
