$ErrorActionPreference = 'Stop'
$src = "assets/icons/material/filled"
$outDir = $src
$cats = @('action','navigation','content','device','file','communication','av','editor','image','hardware','notification','social','maps','places','alert')

# Derive icon base names from existing SVG files
$svgs = Get-ChildItem -Path $src -Filter '*_24px.svg' | ForEach-Object {
    $_.BaseName -replace '_24px$',''
}

$downloaded = @()
$failed = @()
foreach ($name in $svgs) {
    $ok = $false
    foreach ($cat in $cats) {
        $url = "https://raw.githubusercontent.com/google/material-design-icons/master/png/$cat/$name/materialicons/24dp/1x/baseline_${name}_black_24dp.png"
        try {
            Invoke-WebRequest -Uri $url -OutFile (Join-Path $outDir ("${name}_24px.png")) -UseBasicParsing -TimeoutSec 10
            $ok = $true
            break
        } catch {
            continue
        }
    }
    if ($ok) { $downloaded += $name } else { $failed += $name }
}

Write-Host "Downloaded PNGs: $($downloaded -join ', ')"
Write-Host "Failed: $($failed -join ', ')"
