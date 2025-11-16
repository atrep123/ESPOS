# Launch UI Simulator in new window (forwards any extra args)
param(
    [int]$Fps = 144,
    [int]$Port = 8765,
    [int]$UartPort = 0,
    [int]$Width = 100,
    [int]$Height = 24,
    [switch]$NoColor,
    [switch]$NoUnicode,
    [string]$Script = "",
    [switch]$AutoPorts,
    [switch]$SameWindow,
    [int]$FullRedrawInterval = 300,
    [switch]$NoDiff,
    [string]$Config = "",
    [string]$ExportMetrics = "",
    [int]$WebSocketPort = 0,
    [string]$Record = "",
    [string]$Playback = "",
    [switch]$AutoSize
)

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python not found!" -ForegroundColor Red
    exit 1
}

# Auto-select free ports if requested
if ($AutoPorts) {
    function Get-FreeTcpPort {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback,0)
        $listener.Start()
        $p = $listener.LocalEndpoint.Port
        $listener.Stop()
        return $p
    }
    if (-not $PSBoundParameters.ContainsKey('Port') -or -not ($Port -gt 0)) { $Port = Get-FreeTcpPort }
    if (-not $PSBoundParameters.ContainsKey('UartPort') -or -not ($UartPort -gt 0)) {
        do { $UartPort = Get-FreeTcpPort } while ($UartPort -eq $Port)
    }
}

$argsList = @("$scriptPath\sim_run.py", "--fps", "$Fps", "--width", "$Width", "--height", "$Height", "--rpc-port", "$Port")
if ($UartPort -gt 0) { $argsList += @("--uart-port", "$UartPort") }
if ($NoColor) { $argsList += "--no-color" }
if ($NoUnicode) { $argsList += "--no-unicode" }
if ($Script -ne "") { $argsList += @("--script", "$Script") }
if ($FullRedrawInterval -gt 0) { $argsList += @("--full-redraw-interval", "$FullRedrawInterval") }
if ($NoDiff) { $argsList += "--no-diff" }
if ($Config -ne "") { $argsList += @("--config", "$Config") }
if ($ExportMetrics -ne "") { $argsList += @("--export-metrics", "$ExportMetrics") }
if ($WebSocketPort -gt 0) { $argsList += @("--websocket-port", "$WebSocketPort") }
if ($Record -ne "") { $argsList += @("--record", "$Record") }
if ($Playback -ne "") { $argsList += @("--playback", "$Playback") }
if ($AutoSize) { $argsList += "--auto-size" }

if ($SameWindow) {
    if ($UartPort -gt 0) {
        Write-Host "Starting UI Simulator in this window on RPC $Port and UART $UartPort (FPS $Fps)" -ForegroundColor Green
    } else {
        Write-Host "Starting UI Simulator in this window on port $Port (FPS $Fps)" -ForegroundColor Green
    }
    & python $argsList
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Host "Simulator exited with code $code. Check 'simulator.log' for details (if present)." -ForegroundColor Red
        exit $code
    }
} else {
    if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
        Start-Process wt.exe -ArgumentList @("python", ($argsList -join ' '))
    } else {
        Start-Process powershell -ArgumentList @("-NoExit", "-Command", "cd '$scriptPath'; python $($argsList -join ' ')")
    }
    if ($UartPort -gt 0) {
        Write-Host "UI Simulator started in new window on RPC $Port and UART $UartPort (FPS $Fps)" -ForegroundColor Green
    } else {
        Write-Host "UI Simulator started in new window on port $Port (FPS $Fps)" -ForegroundColor Green
    }
}
