# =============================================================================
# InDE — Startup Script (Windows PowerShell)
# =============================================================================
# Usage:
#   .\start.ps1                    # Single-host deployment (default)
#   .\start.ps1 -Tier enterprise   # Enterprise with external DB/Redis
#   .\start.ps1 -Tier federated    # Federated with IKF hub connection
# =============================================================================

param(
    [ValidateSet("single", "enterprise", "federated")]
    [string]$Tier = "single"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Map tier to compose file
$ComposeFiles = @{
    "single" = "$ComposeFile"
    "enterprise" = "docker-compose.enterprise.yml"
    "federated" = "docker-compose.federated.yml"
}
$ComposeFile = $ComposeFiles[$Tier]

# =============================================================================
# Display Header
# =============================================================================
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Blue
Write-Host "║        InDE — Startup                                         ║" -ForegroundColor Blue
Write-Host "║        Innovation Development Environment v3.9.0              ║" -ForegroundColor Blue
Write-Host "║        Deployment Tier: $($Tier.ToUpper().PadRight(38))║" -ForegroundColor Blue
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Blue
Write-Host ""

# =============================================================================
# Check for .env file
# =============================================================================
if (-not (Test-Path ".env")) {
    Write-Host "No .env file found. Creating from template..." -ForegroundColor Yellow
    if (Test-Path ".env.template") {
        Copy-Item ".env.template" ".env"
        Write-Host "Please edit .env with your configuration and run this script again." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Required settings:"
        Write-Host "  - INDEVERSE_LICENSE_KEY: Your InDE license key"
        Write-Host "  - ANTHROPIC_API_KEY: Your Anthropic API key"
        Write-Host "  - INDE_ADMIN_EMAIL: Admin email for setup"
        exit 1
    } else {
        Write-Host "Error: .env.template not found" -ForegroundColor Red
        exit 1
    }
}

# Load environment variables from .env
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($value -and $name) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# =============================================================================
# Validate required variables
# =============================================================================
Write-Host "Checking configuration for $Tier tier..."

$MissingVars = @()

# Common required variables
if (-not $env:INDEVERSE_LICENSE_KEY) {
    $MissingVars += "INDEVERSE_LICENSE_KEY"
}

if (-not $env:ANTHROPIC_API_KEY) {
    $MissingVars += "ANTHROPIC_API_KEY"
}

if (-not $env:INDE_ADMIN_EMAIL) {
    $MissingVars += "INDE_ADMIN_EMAIL"
}

# Enterprise/Federated tier requires external services
if ($Tier -in @("enterprise", "federated")) {
    if (-not $env:MONGODB_URL) {
        $MissingVars += "MONGODB_URL (required for $Tier tier)"
    }
    if (-not $env:REDIS_URL) {
        $MissingVars += "REDIS_URL (required for $Tier tier)"
    }
    if (-not $env:JWT_SECRET) {
        $MissingVars += "JWT_SECRET (required for $Tier tier)"
    }
    if (-not $env:SERVICE_TOKEN) {
        $MissingVars += "SERVICE_TOKEN (required for $Tier tier)"
    }
}

# Federated tier requires IKF hub configuration
if ($Tier -eq "federated") {
    if (-not $env:IKF_HUB_URL) {
        $MissingVars += "IKF_HUB_URL (required for federated tier)"
    }
    if (-not $env:IKF_ORG_ID) {
        $MissingVars += "IKF_ORG_ID (required for federated tier)"
    }
    if (-not $env:IKF_FEDERATION_KEY) {
        $MissingVars += "IKF_FEDERATION_KEY (required for federated tier)"
    }
}

if ($MissingVars.Count -gt 0) {
    Write-Host "Error: Missing required configuration:" -ForegroundColor Red
    foreach ($var in $MissingVars) {
        Write-Host "  - $var"
    }
    Write-Host ""
    Write-Host "Please edit .env and set the required values."
    exit 1
}

Write-Host "[OK] Configuration valid for $Tier tier" -ForegroundColor Green

# =============================================================================
# Check Docker
# =============================================================================
Write-Host "Checking Docker installation..."

try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>$null
    if (-not $dockerVersion) {
        throw "Docker not responding"
    }
    Write-Host "[OK] Docker is running (v$dockerVersion)" -ForegroundColor Green
} catch {
    Write-Host "Error: Docker is not installed or not running" -ForegroundColor Red
    Write-Host "Please install Docker Desktop: https://docs.docker.com/desktop/windows/install/"
    exit 1
}

# Check Docker Compose
try {
    $composeVersion = docker compose version --short 2>$null
    Write-Host "[OK] Docker Compose is available (v$composeVersion)" -ForegroundColor Green
} catch {
    Write-Host "Error: Docker Compose is not available" -ForegroundColor Red
    exit 1
}

# =============================================================================
# Check system requirements
# =============================================================================
Write-Host "Checking system requirements..."

# Check available memory
$totalMemGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
if ($totalMemGB -lt 6) {
    Write-Host "Warning: System has ${totalMemGB}GB RAM. Recommended: 8GB+" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Memory: ${totalMemGB}GB available" -ForegroundColor Green
}

# Check disk space
$drive = (Get-Location).Drive.Name
$freeSpaceGB = [math]::Round((Get-PSDrive $drive).Free / 1GB, 1)
if ($freeSpaceGB -lt 10) {
    Write-Host "Warning: ${freeSpaceGB}GB disk space available. Recommended: 20GB+" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Disk space: ${freeSpaceGB}GB available" -ForegroundColor Green
}

# =============================================================================
# Create data directories
# =============================================================================
Write-Host "Preparing data directories..."

$dbDataPath = if ($env:INDE_DB_DATA_PATH) { $env:INDE_DB_DATA_PATH } else { ".\data\db" }
if (-not (Test-Path $dbDataPath)) {
    New-Item -ItemType Directory -Path $dbDataPath -Force | Out-Null
}
Write-Host "[OK] Data directories ready" -ForegroundColor Green

# =============================================================================
# Start services
# =============================================================================
Write-Host ""
Write-Host "Starting InDE services..."
Write-Host ""

docker compose -f $ComposeFile up -d

# =============================================================================
# Wait for health checks
# =============================================================================
Write-Host ""
Write-Host "Waiting for services to become healthy..."

$maxWait = 120
$waitInterval = 5
$elapsed = 0

while ($elapsed -lt $maxWait) {
    $services = docker compose -f $ComposeFile ps --format json 2>$null | ConvertFrom-Json
    $healthyCount = ($services | Where-Object { $_.Health -eq "healthy" }).Count
    $totalCount = $services.Count

    if ($healthyCount -eq $totalCount -and $totalCount -gt 0) {
        Write-Host "[OK] All services healthy" -ForegroundColor Green
        break
    }

    Write-Host "  Waiting... ($healthyCount/$totalCount services healthy)"
    Start-Sleep -Seconds $waitInterval
    $elapsed += $waitInterval
}

if ($elapsed -ge $maxWait) {
    Write-Host "Warning: Some services may not be fully healthy yet" -ForegroundColor Yellow
    docker compose -f $ComposeFile ps
}

# =============================================================================
# Success message
# =============================================================================
$indePort = if ($env:INDE_PORT) { $env:INDE_PORT } else { "8080" }

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    InDE is ready!                             ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Access InDE at: http://localhost:${indePort}"
Write-Host ""
Write-Host "Commands:"
Write-Host "  View logs:    docker compose -f $ComposeFile logs -f"
Write-Host "  Stop InDE:    docker compose -f $ComposeFile down"
Write-Host "  Restart:      docker compose -f $ComposeFile restart"
Write-Host ""
