# InDE v3.9 Deployment Guide

**Version:** 3.8.0 - Commercial Launch Infrastructure
**Last Updated:** February 2026

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Quick Start](#quick-start)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [License Activation](#license-activation)
6. [API Key Configuration (BYOK)](#api-key-configuration-byok)
7. [Production Configuration](#production-configuration)
8. [Health Monitoring](#health-monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Backup and Recovery](#backup-and-recovery)

---

## System Requirements

### Minimum Requirements

| Component | Specification |
|-----------|--------------|
| CPU | 4 cores |
| RAM | 8 GB |
| Storage | 50 GB SSD |
| OS | Linux (Ubuntu 22.04+), Windows Server 2019+, macOS 12+ |
| Docker | 24.0+ |
| Docker Compose | 2.20+ |

### Recommended Requirements

| Component | Specification |
|-----------|--------------|
| CPU | 8+ cores |
| RAM | 16 GB+ |
| Storage | 100 GB+ NVMe SSD |
| Network | 100 Mbps+ |

### Network Requirements

- Outbound HTTPS access to:
  - `api.anthropic.com` (AI coaching)
  - `license.indeverse.com` (license validation)
- Internal ports (configurable):
  - 3000 (Frontend)
  - 8000 (API)
  - 8080 (LLM Gateway)
  - 27017 (MongoDB, internal only)

---

## Pre-Deployment Checklist

Before deploying InDE, ensure you have:

- [ ] Docker and Docker Compose installed
- [ ] License key from InDEVerse (`INDE-XXX-XXXXXXXXXXXX-XXXX`)
- [ ] Anthropic API key (`sk-ant-...`)
- [ ] DNS/hostname configured (if applicable)
- [ ] SSL certificates (for production)
- [ ] Firewall rules configured

---

## Quick Start

### Linux/macOS

```bash
cd deployment
chmod +x start.sh
./start.sh
```

### Windows (PowerShell)

```powershell
cd deployment
.\start.ps1
```

After startup, navigate to `http://localhost:3000/setup` to complete the setup wizard.

---

## Step-by-Step Deployment

### Step 1: Extract the Package

```bash
tar -xzf inde-v3.9.0.tar.gz
cd inde_mvp_v3.9/deployment
```

### Step 2: Configure Environment

Copy the environment template and edit:

```bash
cp .env.template .env
nano .env  # or your preferred editor
```

Required environment variables:

```env
# License Configuration
INDE_LICENSE_KEY=INDE-PRO-XXXXXXXXXXXX-XXXX

# API Configuration (BYOK - Bring Your Own Key)
ANTHROPIC_API_KEY=sk-ant-api03-...

# MongoDB (auto-generated if not set)
MONGO_INITDB_ROOT_USERNAME=inde_admin
MONGO_INITDB_ROOT_PASSWORD=<secure-password>

# Optional: Custom ports
FRONTEND_PORT=3000
API_PORT=8000
```

### Step 3: Start Services

```bash
docker compose -f docker-compose.production.yml up -d
```

### Step 4: Verify Startup

```bash
docker compose -f docker-compose.production.yml ps
```

All services should show as "healthy":

```
NAME              STATUS
inde-app          healthy
inde-db           healthy
inde-license      healthy
inde-llm-gateway  healthy
inde-frontend     healthy
```

### Step 5: Complete Setup Wizard

1. Open your browser to `http://localhost:3000/setup`
2. Follow the 6-step setup wizard:
   - License Activation
   - Organization Setup
   - Admin Account Creation
   - API Key Configuration
   - System Verification
   - Launch

---

## License Activation

### Online Activation (Recommended)

1. Enter your license key in the setup wizard
2. The system validates with `license.indeverse.com`
3. License is cached locally for 24 hours

### Offline Activation

For air-gapped deployments:

1. Contact InDEVerse support for an offline license file
2. Place `license.json` in `/data/license/`
3. Restart the license service

### License States

| State | Description |
|-------|-------------|
| ACTIVE | License valid and operational |
| GRACE_QUIET | License check failed, 30-day grace period started |
| GRACE_VISIBLE | 15 days remaining, warnings shown |
| GRACE_URGENT | 7 days remaining, prominent warnings |
| EXPIRED | Grace period ended, read-only mode |

---

## API Key Configuration (BYOK)

InDE uses Claude AI for coaching. You must provide your own Anthropic API key.

### Getting an API Key

1. Visit [console.anthropic.com](https://console.anthropic.com)
2. Create an account or sign in
3. Generate an API key (starts with `sk-ant-`)
4. Copy the key securely

### Configuring the Key

**Option 1: Environment Variable (Recommended)**
```env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Option 2: Setup Wizard**
Enter the key during initial setup.

**Option 3: Runtime Configuration**
```bash
curl -X POST http://localhost:8080/api/v1/configure \
  -H "Content-Type: application/json" \
  -d '{"anthropic_api_key": "sk-ant-..."}'
```

### API Key Security

- Your API key never leaves your infrastructure
- Keys are stored in memory only (not persisted)
- InDEVerse cannot access your API key
- Monitor usage at console.anthropic.com

---

## Production Configuration

### SSL/TLS Configuration

For production deployments, configure SSL:

```yaml
# docker-compose.override.yml
services:
  inde-frontend:
    environment:
      - SSL_CERT_PATH=/certs/cert.pem
      - SSL_KEY_PATH=/certs/key.pem
    volumes:
      - ./certs:/certs:ro
```

### Resource Limits

Default limits are set for typical deployments. Adjust in `docker-compose.production.yml`:

```yaml
services:
  inde-app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Log Rotation

Logs are automatically rotated (10 files, 10MB each). To customize:

```yaml
services:
  inde-app:
    logging:
      options:
        max-size: "50m"
        max-file: "5"
```

---

## Health Monitoring

### Health Check Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| API | `/health` | `{"status": "healthy"}` |
| License | `/health` | `{"status": "healthy", "license": {...}}` |
| LLM Gateway | `/health` | `{"status": "healthy", "api_key_configured": true}` |

### Docker Health Checks

```bash
# View service health
docker compose -f docker-compose.production.yml ps

# View health check logs
docker inspect inde-app | jq '.[0].State.Health'
```

### Monitoring Integration

InDE exposes Prometheus-compatible metrics at `/metrics` on each service.

---

## Troubleshooting

### Service Won't Start

**Symptoms:** Container exits immediately or fails health check

**Solutions:**
1. Check logs: `docker compose logs inde-app`
2. Verify environment variables in `.env`
3. Ensure ports aren't in use: `netstat -tlnp | grep 8000`

### License Validation Failed

**Symptoms:** "License validation failed" in logs

**Solutions:**
1. Verify license key format: `INDE-XXX-XXXXXXXXXXXX-XXXX`
2. Check network access to `license.indeverse.com`
3. For offline deployments, verify `license.json` is valid

### API Key Not Working

**Symptoms:** Coaching responses return demo/fallback messages

**Solutions:**
1. Verify key format starts with `sk-ant-`
2. Test key: `curl http://localhost:8080/api/v1/validate-key`
3. Check Anthropic console for rate limits or quota

### Database Connection Failed

**Symptoms:** "MongoDB connection error" in logs

**Solutions:**
1. Verify `inde-db` container is running
2. Check credentials in `.env` match docker-compose
3. Clear and reinitialize: `docker compose down -v && docker compose up -d`

### Frontend Not Loading

**Symptoms:** White screen or 404 errors

**Solutions:**
1. Check frontend logs: `docker compose logs inde-frontend`
2. Verify API is reachable: `curl http://localhost:8000/health`
3. Clear browser cache

### Grace Period Triggered

**Symptoms:** Warning banners about license expiration

**Solutions:**
1. Check license status: `curl http://localhost:5001/api/v1/status`
2. Re-validate license: restart license service
3. Contact InDEVerse support if issue persists

---

## Backup and Recovery

### Data Backup

InDE stores data in MongoDB. To backup:

```bash
# Create backup
docker compose exec inde-db mongodump \
  --username=$MONGO_USERNAME \
  --password=$MONGO_PASSWORD \
  --archive=/backup/inde-backup-$(date +%Y%m%d).archive

# Copy backup out of container
docker cp inde-db:/backup ./backups/
```

### Automated Backups

Add to crontab:
```cron
0 2 * * * /opt/inde/scripts/backup.sh
```

### Recovery

```bash
# Restore from backup
docker compose exec inde-db mongorestore \
  --username=$MONGO_USERNAME \
  --password=$MONGO_PASSWORD \
  --archive=/backup/inde-backup-YYYYMMDD.archive
```

---

## Support

- **Documentation:** docs.indeverse.com
- **Support Portal:** support.indeverse.com
- **Email:** support@indeverse.com

For license issues:
- **License Portal:** license.indeverse.com
- **Email:** licensing@indeverse.com

---

*InDE v3.9.0 - Commercial Launch Infrastructure*
*Copyright 2026 InDEVerse, Inc. All rights reserved.*
