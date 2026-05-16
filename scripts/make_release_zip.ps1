# Build dist/b2-automation-<version>.zip for sharing (no .venv, .git, inputs, outputs, .env*).
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$version = "0.1.0"
if (Test-Path "pyproject.toml") {
    $m = Select-String -Path "pyproject.toml" -Pattern 'version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if ($null -ne $m -and $m.Matches.Success) {
        $version = $m.Matches.Groups[1].Value
    }
}

New-Item -ItemType Directory -Path "dist" -Force | Out-Null
$staging = Join-Path $env:TEMP ("b2-automation-staging-" + [Guid]::NewGuid().ToString("n"))
New-Item -ItemType Directory -Path $staging | Out-Null
try {
    $exclude = @(
        ".git", ".venv", "outputs", "inputs", "__pycache__", "dist",
        ".env", ".pytest_cache"
    )
    Get-ChildItem -LiteralPath $RepoRoot -Force | Where-Object {
        $n = $_.Name
        ($exclude -notcontains $n) -and ($n -notlike ".env.*")
    } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $staging $_.Name) -Recurse -Force
    }

    $zipName = "b2-automation-$version.zip"
    $zipPath = Join-Path "dist" $zipName
    if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
    Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -Force
    Write-Host "Created $zipPath"
}
finally {
    if (Test-Path $staging) {
        Remove-Item -Recurse -Force $staging -ErrorAction SilentlyContinue
    }
}
