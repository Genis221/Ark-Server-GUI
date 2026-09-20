@echo off
title Ark Survival Ascended Server Manager
cd /d "%~dp0"

set "SILENT="
if /i "%~1"=="silent" set "SILENT=1"

REM Self-heal first: a broken Start-ArkManager.ps1 cannot update itself.
set "GIT_SSL_NO_VERIFY=true"
set "GIT_TERMINAL_PROMPT=0"
set "GCM_INTERACTIVE=never"

where git >nul 2>&1
if not errorlevel 1 (
  git rev-parse --is-inside-work-tree >nul 2>&1
  if not errorlevel 1 (
    if not defined SILENT echo Checking GitHub for updates...
    git fetch --prune --no-tags origin +refs/heads/main:refs/remotes/origin/main 2>nul
    if errorlevel 1 git fetch --prune --no-tags https://github.com/Genis221/Ark-Server-GUI.git +refs/heads/main:refs/remotes/origin/main 2>nul
    git reset --hard origin/main 2>nul
    if not errorlevel 1 if not defined SILENT echo Updated launcher files from GitHub.
  )
)

REM If the PowerShell launcher is still unparseable, replace critical files from raw GitHub.
if defined SILENT (
  powershell -WindowStyle Hidden -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$p=Join-Path '%~dp0' 'Start-ArkManager.ps1'; $errs=$null; if(Test-Path -LiteralPath $p){ $null=[System.Management.Automation.Language.Parser]::ParseFile($p,[ref]$null,[ref]$errs) }; if($errs -and $errs.Count){ $base='https://raw.githubusercontent.com/Genis221/Ark-Server-GUI/main'; foreach($f in @('Start-ArkManager.ps1','StartArkManagerAtLogon.vbs','RestartArkManager.cmd','RestartArkManager.vbs')){ try{ Invoke-WebRequest -UseBasicParsing -Uri ($base+'/'+$f) -OutFile (Join-Path '%~dp0' $f) } catch {} } }"
) else (
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$p=Join-Path '%~dp0' 'Start-ArkManager.ps1'; $errs=$null; if(Test-Path -LiteralPath $p){ $null=[System.Management.Automation.Language.Parser]::ParseFile($p,[ref]$null,[ref]$errs) }; if($errs -and $errs.Count){ Write-Host 'Repairing broken launcher from GitHub...' -ForegroundColor Yellow; $base='https://raw.githubusercontent.com/Genis221/Ark-Server-GUI/main'; foreach($f in @('Start-ArkManager.ps1','StartArkManagerAtLogon.vbs','RestartArkManager.cmd','RestartArkManager.vbs')){ try{ Invoke-WebRequest -UseBasicParsing -Uri ($base+'/'+$f) -OutFile (Join-Path '%~dp0' $f) } catch {} } }"
)

REM When silent, skip %%1 ("silent") and pass the remaining args only.
if defined SILENT (
  powershell -WindowStyle Hidden -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ArkManager.ps1" -NoBrowser %2 %3 %4 %5 %6 %7 %8 %9
) else (
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ArkManager.ps1" %*
)

if errorlevel 1 (
  if not defined SILENT pause
  exit /b 1
)
exit /b 0
