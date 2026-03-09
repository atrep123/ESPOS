param(
  [switch]$SkipPython,
  [switch]$SkipPio,
  [switch]$Fast,
  [string]$Design = "main_scene.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$prev = $env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK
$env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK = "1"

try {
  & "$PSScriptRoot\check_all.ps1" `
    -SkipPython:$SkipPython `
    -SkipPio:$SkipPio `
    -Fast:$Fast `
    -Design $Design `
    -AllowNativePolicyBlock
}
finally {
  if ($null -eq $prev) {
    Remove-Item Env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK -ErrorAction SilentlyContinue
  } else {
    $env:ESP32OS_ALLOW_NATIVE_POLICY_BLOCK = $prev
  }
}
