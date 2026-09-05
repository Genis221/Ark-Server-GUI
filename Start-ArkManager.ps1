param(
  [ValidateRange(1024, 65535)]
  [int]$Port = 3220,
  [string]$HostAddress = "0.0.0.0",
  [switch]$NoBrowser
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:ARK_PORT = "$Port"
$env:ARK_HOST = $HostAddress
if (-not $env:ARK_ALLOW_REMOTE) { $env:ARK_ALLOW_REMOTE = "true" }

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
  Write-Host "Node.js 20+ was not found on PATH. Install Node.js, then try again." -ForegroundColor Red
  exit 1
}

function Get-LanIPv4 {
  Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
      $_.IPAddress -notlike "127.*" -and
      $_.PrefixOrigin -ne "WellKnown" -and
      $_.AddressState -eq "Preferred"
    } |
    Select-Object -ExpandProperty IPAddress -First 1
}

function Stop-ListenerOnPort {
  param([int]$Port)

  $pids = @()
  try {
    $pids = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique)
  } catch {
    # Fall through to netstat
  }

  if (-not $pids) {
    $pattern = ":\s*$Port\s+.*LISTENING\s+(\d+)\s*$"
    $pids = @(netstat -ano -p tcp |
      ForEach-Object {
        if ($_ -match $pattern) { [int]$Matches[1] }
      } |
      Select-Object -Unique)
  }

  foreach ($processId in $pids) {
    if ($processId -le 0) { continue }
    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
    $label = if ($proc) { "$($proc.ProcessName) (PID $processId)" } else { "PID $processId" }
    try {
      Stop-Process -Id $processId -Force -ErrorAction Stop
      Write-Host "Stopped previous manager on port $Port ($label)." -ForegroundColor DarkGray
    } catch {
      Write-Host "Could not stop $label : $($_.Exception.Message)" -ForegroundColor Yellow
    }
  }

  Start-Sleep -Milliseconds 400
}

Stop-ListenerOnPort -Port $Port

$lanIp = Get-LanIPv4
if ($lanIp) {
  Write-Host "Starting Ark Server Manager..." -ForegroundColor Cyan
  Write-Host "  Local: http://127.0.0.1:$Port"
  Write-Host "  LAN:   http://${lanIp}:$Port"
} else {
  Write-Host "Starting Ark Server Manager at http://127.0.0.1:$Port ..." -ForegroundColor Cyan
}

Set-Location $projectRoot
$nodeArgs = @("server.mjs")
if ($NoBrowser) { $nodeArgs += "--no-open" }
& node @nodeArgs
exit $LASTEXITCODE
