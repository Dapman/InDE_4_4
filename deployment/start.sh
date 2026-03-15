#!/bin/bash
# =============================================================================
# InDE Professional Tier — Startup Script (Linux/macOS)
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║        InDE Professional Tier — Startup                       ║"
echo "║        Innovation Development Environment v3.9.0              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =============================================================================
# Check for .env file
# =============================================================================
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
    if [ -f .env.template ]; then
        cp .env.template .env
        echo -e "${YELLOW}Please edit .env with your configuration and run this script again.${NC}"
        echo ""
        echo "Required settings:"
        echo "  - INDEVERSE_LICENSE_KEY: Your InDE license key"
        echo "  - ANTHROPIC_API_KEY: Your Anthropic API key"
        echo "  - INDE_ADMIN_EMAIL: Admin email for setup"
        exit 1
    else
        echo -e "${RED}Error: .env.template not found${NC}"
        exit 1
    fi
fi

# Load environment variables
source .env

# =============================================================================
# Validate required variables
# =============================================================================
echo "Checking configuration..."

MISSING_VARS=()

if [ -z "$INDEVERSE_LICENSE_KEY" ]; then
    MISSING_VARS+=("INDEVERSE_LICENSE_KEY")
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    MISSING_VARS+=("ANTHROPIC_API_KEY")
fi

if [ -z "$INDE_ADMIN_EMAIL" ]; then
    MISSING_VARS+=("INDE_ADMIN_EMAIL")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing required configuration:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please edit .env and set the required values."
    exit 1
fi

echo -e "${GREEN}✓ Configuration valid${NC}"

# =============================================================================
# Check Docker and Docker Compose
# =============================================================================
echo "Checking Docker installation..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    echo "Please start Docker and try again."
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Check Docker Compose (v2 style)
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose v2: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker Compose is available${NC}"

# =============================================================================
# Check system requirements
# =============================================================================
echo "Checking system requirements..."

# Check available memory (need at least 6GB for comfortable operation)
if command -v free &> /dev/null; then
    TOTAL_MEM_KB=$(free | awk '/^Mem:/{print $2}')
    TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
    if [ $TOTAL_MEM_GB -lt 6 ]; then
        echo -e "${YELLOW}Warning: System has ${TOTAL_MEM_GB}GB RAM. Recommended: 8GB+${NC}"
    else
        echo -e "${GREEN}✓ Memory: ${TOTAL_MEM_GB}GB available${NC}"
    fi
fi

# Check disk space (need at least 10GB)
if command -v df &> /dev/null; then
    AVAILABLE_SPACE_KB=$(df . | awk 'NR==2 {print $4}')
    AVAILABLE_SPACE_GB=$((AVAILABLE_SPACE_KB / 1024 / 1024))
    if [ $AVAILABLE_SPACE_GB -lt 10 ]; then
        echo -e "${YELLOW}Warning: ${AVAILABLE_SPACE_GB}GB disk space available. Recommended: 20GB+${NC}"
    else
        echo -e "${GREEN}✓ Disk space: ${AVAILABLE_SPACE_GB}GB available${NC}"
    fi
fi

# =============================================================================
# Create data directories
# =============================================================================
echo "Preparing data directories..."

INDE_DB_DATA_PATH="${INDE_DB_DATA_PATH:-./data/db}"
mkdir -p "$INDE_DB_DATA_PATH"
echo -e "${GREEN}✓ Data directories ready${NC}"

# =============================================================================
# Start services
# =============================================================================
echo ""
echo "Starting InDE services..."
echo ""

docker compose -f docker-compose.production.yml up -d

# =============================================================================
# Wait for health checks
# =============================================================================
echo ""
echo "Waiting for services to become healthy..."

MAX_WAIT=120
WAIT_INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    HEALTHY_COUNT=$(docker compose -f docker-compose.production.yml ps --format json 2>/dev/null | grep -c '"Health": "healthy"' || true)
    TOTAL_COUNT=$(docker compose -f docker-compose.production.yml ps --format json 2>/dev/null | grep -c '"Service"' || true)

    if [ "$HEALTHY_COUNT" -eq "$TOTAL_COUNT" ] && [ "$TOTAL_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ All services healthy${NC}"
        break
    fi

    echo "  Waiting... ($HEALTHY_COUNT/$TOTAL_COUNT services healthy)"
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}Warning: Some services may not be fully healthy yet${NC}"
    docker compose -f docker-compose.production.yml ps
fi

# =============================================================================
# Success message
# =============================================================================
INDE_PORT="${INDE_PORT:-8080}"

echo ""
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    InDE is ready!                             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "Access InDE at: http://localhost:${INDE_PORT}"
echo ""
echo "Commands:"
echo "  View logs:    docker compose -f docker-compose.production.yml logs -f"
echo "  Stop InDE:    docker compose -f docker-compose.production.yml down"
echo "  Restart:      docker compose -f docker-compose.production.yml restart"
echo ""
