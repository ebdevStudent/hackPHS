# Compile and flash ball_bridge_esp32 from the terminal (no Arduino IDE window).
# Uses the arduino-cli bundled with Arduino IDE 2 unless arduino-cli is on PATH.
#   .\flash.ps1            auto-detect the CH343 port (1a86:55d3)
#   .\flash.ps1 -Port COM5
param([string]$Port)
$ErrorActionPreference = 'Stop'

$cli = (Get-Command arduino-cli -ErrorAction SilentlyContinue).Source
if (-not $cli) { $cli = "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" }
if (-not (Test-Path $cli)) { throw "arduino-cli not found" }

$sketch = Join-Path $PSScriptRoot '..\ball_bridge_esp32'
$fqbn = 'esp32:esp32:esp32s3'

if (-not $Port) {
    $dev = Get-CimInstance Win32_PnPEntity | Where-Object { $_.DeviceID -match 'VID_1A86&PID_55D3' -and $_.Name -match '\((COM\d+)\)' }
    if (-not $dev) { throw "No CH343 port found. Plug in the USB-C port next to BOOT, or pass -Port COMx." }
    $Port = [regex]::Match($dev[0].Name, 'COM\d+').Value
}
Write-Host "Flashing $sketch to $Port"

& $cli compile --fqbn $fqbn --warnings all $sketch
if ($LASTEXITCODE -ne 0) { throw "compile failed" }
& $cli upload --fqbn $fqbn -p $Port $sketch
if ($LASTEXITCODE -ne 0) { throw "upload failed. Hold BOOT, tap RST, release BOOT, then rerun." }
Write-Host "Done. Control it with: python $PSScriptRoot\esp_term.py --port $Port"
