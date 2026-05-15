@echo off
set ZIP_NAME=2026_Audit_Pack.zip
echo Zipping...
powershell -Command "Compress-Archive -Path 'B24_strict_corrected.json', 'B89_strict_corrected.json', 'B90_strict_corrected.json' -DestinationPath '%ZIP_NAME%' -Force"
echo [SUCCESS] Created %ZIP_NAME%
pause
