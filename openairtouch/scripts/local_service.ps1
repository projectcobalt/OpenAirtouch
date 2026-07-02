param(
    [ValidateSet("run", "status", "stop")]
    [string]$Action = "run",
    [string]$TcpHost = "192.168.30.56",
    [int]$TcpPort = 6638,
    [string]$HostAddress = "127.0.0.1",
    [int]$HttpPort = 8099,
    [string]$Protocol = "auto",
    [string]$Python = "python",
    [switch]$Background,
    [switch]$StopExisting
)

$ErrorActionPreference = "Stop"

$worktreeRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$serviceScript = Join-Path $worktreeRoot "openairtouch\scripts\airtouch_service.py"
$logDir = Join-Path $worktreeRoot ".codex-runlogs"
$logPath = Join-Path $logDir "local-service.log"

function Get-LocalListeners {
    Get-NetTCPConnection -LocalPort $HttpPort -State Listen -ErrorAction SilentlyContinue
}

function Show-Status {
    $listeners = @(Get-LocalListeners)
    if (-not $listeners.Count) {
        Write-Host "NO_LISTENER_$HttpPort"
        return
    }

    foreach ($listener in $listeners) {
        Write-Host ("LISTENER_{0} pid={1} address={2}" -f $HttpPort, $listener.OwningProcess, $listener.LocalAddress)
    }

    try {
        $health = Invoke-RestMethod -Uri "http://$HostAddress`:$HttpPort/api/health" -TimeoutSec 2
        Write-Host ("HEALTH ok={0} state={1}" -f $health.ok, $health.status)
    } catch {
        Write-Host ("HEALTH unavailable: {0}" -f $_.Exception.Message)
    }
}

function Stop-LocalListeners {
    $listeners = @(Get-LocalListeners)
    if (-not $listeners.Count) {
        Write-Host "NO_LISTENER_$HttpPort"
        return
    }

    $pids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($listenerPid in $pids) {
        Write-Host ("STOP pid={0}" -f $listenerPid)
        Stop-Process -Id $listenerPid -Force
    }
}

if ($Action -eq "status") {
    Show-Status
    exit 0
}

if ($Action -eq "stop") {
    Stop-LocalListeners
    Show-Status
    exit 0
}

$listeners = @(Get-LocalListeners)
if ($listeners.Count) {
    if ($StopExisting) {
        Stop-LocalListeners
    } else {
        Show-Status
        Write-Error "Port $HttpPort is already in use. Run with -StopExisting or use -Action stop first."
    }
}

Set-Location $worktreeRoot
Write-Host ("RUN OpenAirTouch local service from {0}" -f $worktreeRoot)
Write-Host ("TCP {0}:{1} -> HTTP http://{2}:{3}" -f $TcpHost, $TcpPort, $HostAddress, $HttpPort)

if ($Background) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $errPath = Join-Path $logDir "local-service.err.log"
    Set-Content -Path $logPath -Value ("Starting OpenAirTouch local service at {0}" -f (Get-Date).ToString("s"))
    Set-Content -Path $errPath -Value ("Starting OpenAirTouch local service at {0}" -f (Get-Date).ToString("s"))
    $args = @(
        $serviceScript,
        "--transport", "tcp_serial",
        "--tcp-host", $TcpHost,
        "--tcp-port", $TcpPort,
        "--host", $HostAddress,
        "--http-port", $HttpPort,
        "--protocol", $Protocol
    )
    $process = Start-Process -FilePath $Python -ArgumentList $args -WorkingDirectory $worktreeRoot -WindowStyle Hidden -RedirectStandardOutput $logPath -RedirectStandardError $errPath -PassThru
    Write-Host ("BACKGROUND pid={0} log={1}" -f $process.Id, $logPath)

    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 500
        if (@(Get-LocalListeners).Count) {
            Show-Status
            exit 0
        }
        if ($process.HasExited) {
            break
        }
    }

    Write-Host "BACKGROUND startup did not bind the HTTP port yet."
    if (Test-Path $logPath) {
        Get-Content -Path $logPath -Tail 20
    }
    if (Test-Path $errPath) {
        Get-Content -Path $errPath -Tail 40
    }
    exit 1
}

& $Python $serviceScript `
    --transport tcp_serial `
    --tcp-host $TcpHost `
    --tcp-port $TcpPort `
    --host $HostAddress `
    --http-port $HttpPort `
    --protocol $Protocol
