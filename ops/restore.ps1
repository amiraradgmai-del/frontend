param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath
)

$ErrorActionPreference = "Stop"
$resolvedPath = (Resolve-Path -LiteralPath $BackupPath).Path
if ([IO.Path]::GetExtension($resolvedPath) -ne ".dump") {
    throw "Backup file must use the .dump extension."
}

$confirmation = Read-Host "This replaces the current database. Type RESTORE to continue"
if ($confirmation -ne "RESTORE") {
    Write-Output "Restore cancelled."
    exit 0
}

$containerPath = "/tmp/tax_ai_restore.dump"
docker compose cp $resolvedPath "db:$containerPath"
docker compose exec -T db pg_restore -U tax_ai -d tax_ai --clean --if-exists --no-owner --no-privileges $containerPath
docker compose exec -T db rm -f $containerPath
Write-Output "Database restored successfully."
