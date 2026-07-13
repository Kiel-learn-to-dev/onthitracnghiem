param(
    [switch]$SkipWebView2Bootstrapper
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$desktopBuild = Join-Path $root 'build\desktop'
$bootstrapper = Join-Path $desktopBuild 'MicrosoftEdgeWebview2Setup.exe'
$isccCandidates = @(
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 6\ISCC.exe',
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    throw 'Không tìm thấy Inno Setup 6. Cài bằng: winget install --id JRSoftware.InnoSetup --exact'
}

Push-Location $root
try {
    py -m pip install -r requirements-build.txt
    npm.cmd run build
    New-Item -ItemType Directory -Force -Path $desktopBuild | Out-Null
    if (-not $SkipWebView2Bootstrapper) {
        Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $bootstrapper
        $signature = Get-AuthenticodeSignature $bootstrapper
        if ($signature.Status -ne 'Valid') {
            throw "WebView2 Bootstrapper không có chữ ký hợp lệ: $($signature.Status)"
        }
    }
    py -m PyInstaller --noconfirm --clean --windowed --onedir --name CSLT-OnThi --workpath build\pyinstaller --distpath dist --add-data 'templates;templates' --add-data 'static;static' --add-data 'data\review.db;data' --collect-all webview desktop.py
    & $iscc /Qp (Join-Path $root 'installer\CSLT-OnThi.iss')
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup thất bại với mã $LASTEXITCODE" }
}
finally {
    Pop-Location
}
