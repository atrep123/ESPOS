param(
    [string]$ReportsDir = "reports",
    [switch]$NoSimRoundtrip
)
#requires -Version 5.1

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null
New-Item -ItemType Directory -Force -Path "examples" | Out-Null

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$log = Join-Path $ReportsDir "ci_smoke_$ts.log"

function Write-Log($msg) {
    "[$(Get-Date -Format 'HH:mm:ss')] $msg" | Tee-Object -FilePath $log -Append | Out-Null
}

try { $global:PythonExe = (Get-Command python -ErrorAction Stop | Select-Object -First 1).Source } catch { $global:PythonExe = "python" }

function Run-Step($name, $scriptPath) {
    Write-Log "=== $name ==="
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    # Unbuffered + UTF-8
    & $global:PythonExe -X utf8 -u $scriptPath 2>&1 | Tee-Object -FilePath $log -Append
    $code = $LASTEXITCODE
    $sw.Stop()
    Write-Log "--- exit=$code elapsed=$([int]$sw.Elapsed.TotalSeconds)s"
    if ($code -ne 0) { throw "Step failed: $name (exit=$code)" }
}

try {
    Write-Log "Starting CI smoke at $ts"

    Run-Step "UI Designer tests" "./test_ui_designer.py"
    Run-Step "Preview small heights" "./test_preview_small.py"
    if (Test-Path ./test_preview_ascii_extra.py) { Run-Step "ASCII preview extra" "./test_preview_ascii_extra.py" }
    if (Test-Path ./test_showcase.py) { Run-Step "Showcase" "./test_showcase.py" }

    $artifacts = @()
    if (Test-Path ./examples/preview_small_heights.png) { $artifacts += "examples/preview_small_heights.png" }
    if (Test-Path ./test_scene.png) { $artifacts += "test_scene.png" }
    if (Test-Path ./test_scene.html) { $artifacts += "test_scene.html" }

    foreach ($f in $artifacts) {
        $dest = Join-Path $ReportsDir ("${ts}_" + [IO.Path]::GetFileName($f))
        Copy-Item $f $dest -Force
        Write-Log "Artifact: $dest"
    }

    if (-not $NoSimRoundtrip) {
        Write-Log "Starting simulator roundtrip (RPC + UART)"
        $simProc = $null
        try {
            $simArgs = "-NoProfile -ExecutionPolicy Bypass -File .\run_sim.ps1 -AutoPorts -Fps 30"
            $simProc = Start-Process powershell -ArgumentList $simArgs -WindowStyle Hidden -PassThru
            $limit = (Get-Date).AddSeconds(12)
            while (-not (Test-Path ./sim_ports.json)) {
                Start-Sleep -Milliseconds 200
                if ((Get-Date) -gt $limit) { throw "Timeout waiting for sim_ports.json" }
            }
            $p = Get-Content ./sim_ports.json | ConvertFrom-Json
            $rpcPort = $p.rpc_port
            $uartPort = $p.uart_port
            if (-not $rpcPort -or $rpcPort -eq 0) { throw "rpc_port missing/zero" }
            if (-not $uartPort -or $uartPort -eq 0) { throw "uart_port missing/zero" }
            Write-Log "Ports: rpc=$rpcPort uart=$uartPort pid=$($simProc.Id)"
            function Invoke-Rpc([string]$argsLine,[string]$label) {
                $max = 6; $attempt = 0
                while ($true) {
                    $tokens = $argsLine -split ' '
                    & $global:PythonExe -X utf8 -u ./simctl.py $rpcPort @tokens 2>&1 | Tee-Object -FilePath $log -Append
                    if ($LASTEXITCODE -eq 0) { Write-Log "RPC ok: $label"; break }
                    $attempt++
                    if ($attempt -ge $max) { throw "RPC $label failed after $max attempts" }
                    Write-Log "RPC retry ($label) attempt $attempt"
                    Start-Sleep -Milliseconds 300
                }
            }
            # Give the simulator a brief warm-up before RPC
            Start-Sleep -Milliseconds 600
            Invoke-Rpc "set_bg 255 32 32" "set_bg"
            Invoke-Rpc "scene 1" "scene"
            Invoke-Rpc "btn B press" "btn_press"
            Invoke-Rpc "btn B release" "btn_release"
            # Wait for UART port to accept connections
            $uartReadyLimit = (Get-Date).AddSeconds(8)
            while ($true) {
                try {
                    $testClient = New-Object System.Net.Sockets.TcpClient
                    $ar = $testClient.BeginConnect('127.0.0.1',[int]$uartPort,$null,$null)
                    $ok = $ar.AsyncWaitHandle.WaitOne(500)
                    if ($ok -and $testClient.Connected) {
                        $testClient.Close(); break
                    }
                    $testClient.Close()
                } catch { }
                if ((Get-Date) -gt $uartReadyLimit) { throw "UART port $uartPort not ready" }
            }
            # UART command
            $client = New-Object System.Net.Sockets.TcpClient
            $client.Connect('127.0.0.1',[int]$uartPort)
            $w = New-Object System.IO.StreamWriter($client.GetStream()); $w.AutoFlush = $true
            $w.WriteLine('set_bg 00ff00')
            Start-Sleep -Milliseconds 120
            $client.Close()
            Write-Log "Roundtrip commands sent"
        }
        catch {
            Write-Log "Simulator roundtrip FAIL: $_"
            if ($simProc -and -not $simProc.HasExited) { try { Stop-Process -Id $simProc.Id -Force } catch {} }
            throw
        }
        finally {
            if ($simProc -and -not $simProc.HasExited) {
                try { Stop-Process -Id $simProc.Id -Force; Write-Log "Simulator process terminated" } catch { Write-Log "Simulator termination error: $_" }
            }
        }
    }

    Write-Log "CI smoke PASS"
    exit 0
}
catch {
    Write-Log "CI smoke FAIL: $_"
    exit 1
}
