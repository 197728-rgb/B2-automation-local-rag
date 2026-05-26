# SPEC-1 TypeScript reference pipeline scaffold (personal local MVP)
$ErrorActionPreference = "Stop"
$Root = Join-Path $PSScriptRoot "..\tools\autonomous-audit-pipeline" | Resolve-Path
$Src = Join-Path $Root "src"
$Zip = Join-Path $Root "autonomous-audit-pipeline.zip"

if (Test-Path $Zip) { Remove-Item $Zip -Force }
New-Item -ItemType Directory -Force -Path $Src | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root "schemas") | Out-Null

Set-Content (Join-Path $Root "package.json") @'
{
  "name": "autonomous-audit-pipeline",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "start": "tsx src/mainPipeline.ts",
    "build": "tsc",
    "pipeline": "tsx src/mainPipeline.ts"
  },
  "dependencies": {
    "@google/genai": "^1.0.0",
    "dotenv": "^16.4.0",
    "fast-glob": "^3.3.0",
    "fs-extra": "^11.2.0",
    "mammoth": "^1.9.0",
    "tsx": "^4.19.0",
    "typescript": "^5.6.0"
  },
  "devDependencies": {
    "@types/fs-extra": "^11.0.4",
    "@types/node": "^22.0.0"
  }
}
'@

Set-Content (Join-Path $Root "tsconfig.json") @'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*.ts"]
}
'@

Set-Content (Join-Path $Root ".env.example") @'
GEMINI_API_KEY=your_key_here
LLM_PROVIDER=google
GEMINI_MODEL=gemini-2.5-pro
'@

Write-Host "Success: scaffold written to $Root" -ForegroundColor Green
