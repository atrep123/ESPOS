# Capture a full desktop screenshot to a file (default: screenshots\designer.png)
param(
    [string]$OutputPath = "screenshots\\designer.png"
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$gfx = [System.Drawing.Graphics]::FromImage($bmp)

# Copy entire virtual screen
$gfx.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bmp.Size)

# Ensure output directory exists
$outFile = Resolve-Path -LiteralPath (Join-Path -Path (Get-Location) -ChildPath $OutputPath) -ErrorAction SilentlyContinue
if (-not $outFile) {
    $fullPath = Join-Path -Path (Get-Location) -ChildPath $OutputPath
    $dir = Split-Path -Path $fullPath -Parent
    if ($dir) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $outFile = $fullPath
}

$bmp.Save($outFile, [System.Drawing.Imaging.ImageFormat]::Png)
$gfx.Dispose()
$bmp.Dispose()

Write-Host "Screenshot saved to: $outFile"
