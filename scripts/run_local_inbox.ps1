# Run local inbox review into outputs/local_rag_run (repo root resolved for double-click usage).
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$outDir = Join-Path $RepoRoot "outputs\local_rag_run"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$b2 = Join-Path $RepoRoot ".venv\Scripts\b2.exe"
& $b2 inbox --inbox (Join-Path $RepoRoot "inbox") --out $outDir
$code = $LASTEXITCODE
if ($null -eq $code) { $code = 0 }
exit $code
