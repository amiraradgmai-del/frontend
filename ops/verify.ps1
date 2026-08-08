$ErrorActionPreference = "Stop"

docker compose ps
$services = docker compose ps --services --filter status=running
foreach ($required in @("db", "redis", "api", "worker", "web", "backup")) {
    if ($services -notcontains $required) { throw "Service is not running: $required" }
}

$apiHealth = Invoke-WebRequest -UseBasicParsing http://localhost:8000/ready
$webHealth = Invoke-WebRequest -UseBasicParsing http://localhost:3000/login
if ($apiHealth.StatusCode -ne 200) { throw "API readiness check failed." }
if ($webHealth.StatusCode -ne 200) { throw "Web health check failed." }

$migration = docker compose exec -T api alembic current
if ($migration -notmatch "head") { throw "Database migration is not at head." }

$webHeaders = (Invoke-WebRequest -UseBasicParsing http://localhost:3000/login).Headers
if ($webHeaders["X-Content-Type-Options"] -ne "nosniff") {
    throw "Web security headers are missing."
}
$apiHeaders = (Invoke-WebRequest -UseBasicParsing http://localhost:8000/health).Headers
if ($apiHeaders["X-Frame-Options"] -ne "DENY") {
    throw "API security headers are missing."
}
Write-Output "Deployment verification passed."
