# diagnose_usb_hdc.ps1 -- USB HDC diagnostics for HarmonyOS/OpenHarmony devices (e.g. CPRO)
# ASCII-only on purpose: safe on Windows PowerShell 5.1 regardless of code page.
#
# Usage (read-only, installs nothing, kills nothing):
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\diagnose_usb_hdc.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\diagnose_usb_hdc.ps1 -OutFile .\evidence.txt
#
# Place this file next to the hdc_6.1.1.280 folder, or keep hdc.exe on PATH.

param(
  [string]$OutFile = ''
)

$ErrorActionPreference = 'SilentlyContinue'
if ($OutFile) { Start-Transcript -Path $OutFile -Force | Out-Null }

function Show($t) { ""; "== $t ==" }

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$hdc = Join-Path $here 'hdc_6.1.1.280\hdc.exe'
if (-not (Test-Path $hdc)) { $c = Get-Command hdc -ErrorAction SilentlyContinue; if ($c) { $hdc = $c.Source } }

Show '1. host'
"OS        : " + (Get-CimInstance Win32_OperatingSystem).Caption
"Version   : " + [System.Environment]::OSVersion.Version
"Arch      : " + $env:PROCESSOR_ARCHITECTURE
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
"Admin     : $isAdmin"

Show '2. hdc binary'
"path      : $hdc"
if (Test-Path $hdc) {
  "sha256    : " + (Get-FileHash $hdc -Algorithm SHA256).Hash
  $dll = Join-Path (Split-Path $hdc) 'libusb_shared.dll'
  if (Test-Path $dll) {
    "libusb    : present  " + (Get-FileHash $dll -Algorithm SHA256).Hash
  } else {
    "libusb    : MISSING  (hdc exits 0xC0000135 -- copy libusb_shared.dll next to hdc.exe)"
  }
  "version   : " + ((& $hdc -v 2>&1 | Out-String).Trim())
} else {
  "hdc.exe   : NOT FOUND in this folder and not on PATH"
}

Show '3. USB nodes for VID_12D1 (Huawei / HarmonyOS)'
$devs = @(Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_12D1' })
if ($devs.Count -eq 0) {
  "none. Either the cable/port is not carrying data, or the device is not attached to THIS host."
} else {
  foreach ($d in $devs) {
    "instance  : " + $d.InstanceId
    "  status  : " + $d.Status + "   present: " + $d.Present + "   class: " + $d.Class + "   name: " + $d.FriendlyName
    foreach ($k in 'DEVPKEY_Device_ProblemCode', 'DEVPKEY_Device_DriverInfPath', 'DEVPKEY_Device_Service', 'DEVPKEY_Device_DriverProvider', 'DEVPKEY_Device_DriverVersion') {
      $v = try { (Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName $k).Data } catch { $null }
      "  " + $k.Replace('DEVPKEY_Device_', '') + " = " + $v
    }
  }
}

Show '4. present USB devices that are not healthy (candidate: unbound CPRO)'
Get-PnpDevice -PresentOnly | Where-Object { $_.Status -ne 'OK' } |
  Select-Object Status, Class, FriendlyName, InstanceId |
  Format-Table -AutoSize | Out-String -Width 200

Show '5. other hdc / HarmonyOS toolchains on this host'
foreach ($p in @(
    "$env:LOCALAPPDATA\Huawei",
    "$env:ProgramFiles\Huawei",
    "${env:ProgramFiles(x86)}\Huawei",
    "$env:ProgramFiles\DevEco Studio",
    "$env:LOCALAPPDATA\OpenHarmony")) {
  if (Test-Path $p) { "found path: $p" }
}
Get-Process hdc -ErrorAction SilentlyContinue | Select-Object Id, Path | Format-Table -AutoSize | Out-String -Width 160
$listen = @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq 8710 })
if ($listen.Count -eq 0) { "port 8710 : not listening (normal before the first hdc call)" }
else { $listen | Select-Object LocalAddress, LocalPort, OwningProcess | Format-Table -AutoSize | Out-String -Width 100 }

Show '6. hdc targets'
if (Test-Path $hdc) { ((& $hdc list targets -v 2>&1 | Out-String).Trim()) } else { 'skipped (no hdc.exe)' }

Show '7. what the findings mean / what to do next'
@'
  no VID_12D1 node at all          -> physical path: use a data cable, a mainboard USB port,
                                      and the CPRO port wired to its USB device controller.
  VID_12D1 present, problem 28/43  -> driver: no usable WinUSB binding. Remove a conflicting
                                      HiSuite / Huawei phone driver, or install the WinUSB driver,
                                      then rescan in Device Manager.
  VID_12D1 OK but targets empty    -> hdc layer: run "hdc kill" once, then "hdc list targets -v".
                                      Confirm "hdc -v" is Ver: 3.2.0d on this host; stop any other
                                      hdc.exe started by DevEco Studio or an old toolchain.
  targets show "Unauthorized"      -> accept the authorization on the device side.
  hdc exits 0xC0000135             -> libusb_shared.dll is missing next to hdc.exe.
'@

if ($OutFile) {
  "`n[evidence saved] " + (Resolve-Path $OutFile).Path
  Stop-Transcript | Out-Null
}
