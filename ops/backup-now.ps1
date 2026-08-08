$ErrorActionPreference = "Stop"

$stamp = Get-Date -Format "yyyyMMddTHHmmss"
$containerPath = "/tmp/tax_ai_$stamp.dump"
$outputDirectory = Join-Path $PSScriptRoot "backups"
$outputPath = Join-Path $outputDirectory "tax_ai_$stamp.dump"

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
docker compose exec -T db pg_dump -U tax_ai -d tax_ai --format=custom --compress=9 --file=$containerPath
docker compose exec -T db pg_restore --list $containerPath | Out-Null
docker compose cp "db:$containerPath" $outputPath
docker compose exec -T db rm -f $containerPath
Write-Output "Backup created: $outputPath"
