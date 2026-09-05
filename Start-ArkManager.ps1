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

function Invoke-GitQuiet {
  param([Parameter(Mandatory)][string[]]$GitArgs)
  $previousPrompt = $env:GIT_TERMINAL_PROMPT
  $previousGcm = $env:GCM_INTERACTIVE
  $env:GIT_TERMINAL_PROMPT = "0"
  $env:GCM_INTERACTIVE = "never"
  try {
    & git @GitArgs 2>&1 | Out-Null
    return ($LASTEXITCODE -eq 0)
  } finally {
    if ($null -eq $previousPrompt) { Remove-Item Env:\GIT_TERMINAL_PROMPT -ErrorAction SilentlyContinue }
    else { $env:GIT_TERMINAL_PROMPT = $previousPrompt }
    if ($null -eq $previousGcm) { Remove-Item Env:\GCM_INTERACTIVE -ErrorAction SilentlyContinue }
    else { $env:GCM_INTERACTIVE = $previousGcm }
  }
}

function Update-ArkManagerFromGit {
  $gitCommand = Get-Command git -ErrorAction SilentlyContinue
  if (-not $gitCommand) {
    Write-Host "Git was not found on PATH. Skipping update check and starting with the current files." -ForegroundColor Yellow
    return $false
  }

  Push-Location $projectRoot
  try {
    if (-not (Invoke-GitQuiet @("rev-parse", "--is-inside-work-tree"))) {
      Write-Host "This folder is not a git repository. Skipping update check." -ForegroundColor Yellow
      return $false
    }

    $originUrl = (git remote get-url origin 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($originUrl)) {
      Write-Host "No git remote named origin was found. Skipping update check." -ForegroundColor Yellow
      return $false
    }

    # Prefer the public HTTPS URL so updates do not depend on SSH keys or a GitHub login.
    $publicUrl = "https://github.com/Genis221/Ark-Server-GUI.git"
    if ($originUrl -notmatch "Genis221/Ark-Server-GUI(\.git)?(\s|$)") {
      $publicUrl = ($originUrl -replace "^git@github\.com:", "https://github.com/" -replace "^ssh://git@github\.com/", "https://github.com/" -replace "\.git$", "") + ".git"
      if ($publicUrl -notmatch "^https://github\.com/") { $publicUrl = $originUrl }
    }

    Write-Host "Checking GitHub for Ark Manager updates..." -ForegroundColor DarkGray

    # 1) Anonymous fetch — no credential helper (works for public repos).
    $fetched = Invoke-GitQuiet @(
      "-c", "credential.helper=",
      "fetch", "--prune", "--no-tags", $publicUrl,
      "+refs/heads/main:refs/remotes/origin/main"
    )

    # 2) Fall back to saved credentials / default remote if needed.
    if (-not $fetched) {
      $fetched = Invoke-GitQuiet @("fetch", "--prune", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
    }

    if (-not $fetched) {
      Write-Host "Could not reach GitHub. Skipping update and starting with the current files." -ForegroundColor Yellow
      return $false
    }

    $remoteRef = "origin/main"
    if (-not (Invoke-GitQuiet @("rev-parse", "--verify", "$remoteRef^{commit}"))) {
      $remoteRef = "origin/HEAD"
      if (-not (Invoke-GitQuiet @("rev-parse", "--verify", "$remoteRef^{commit}"))) {
        Write-Host "Could not resolve the remote branch. Skipping update." -ForegroundColor Yellow
        return $false
      }
    }

    $localSha = (git rev-parse HEAD).Trim()
    $remoteSha = (git rev-parse $remoteRef).Trim()
    if ($localSha -eq $remoteSha) {
      Write-Host "Already up to date." -ForegroundColor Green
      return $false
    }

    Write-Host "Updating Ark Manager from $remoteRef..." -ForegroundColor Yellow
    # Overwrite local manager source. Do not use -x so gitignored data/ is preserved.
    if (-not (Invoke-GitQuiet @("reset", "--hard", $remoteRef))) {
      Write-Host "git reset failed. Starting with the current files." -ForegroundColor Red
      return $false
    }
    Invoke-GitQuiet @("clean", "-fd") | Out-Null

    $shortSha = (git rev-parse --short HEAD).Trim()
    Write-Host "Updated to $shortSha. Local data/ (profiles, state) was left alone." -ForegroundColor Green
    return $true
  } finally {
    Pop-Location
  }
}

$didUpdate = Update-ArkManagerFromGit

# Always free the port so an update (or a leftover process) starts clean.
if ($didUpdate) {
  Write-Host "Restarting manager with the updated files..." -ForegroundColor Cyan
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
