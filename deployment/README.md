# InDE v3.16 Deployment Reference

## Droplet: InDEVerse-1
- IP: 159.203.111.160
- SSH: ssh root@159.203.111.160
- App directory: /opt/inde_v316

## Environment Validation (run before any deployment)

```bash
bash scripts/validate_env.sh
```

## Container Operations

```bash
cd /opt/inde_v316

# Pull latest code
git pull origin main

# Rebuild frontend after code changes
cd frontend && npm run build && cd ..

# Restart application container
docker compose restart inde-app

# Recreate container (required after .env changes)
docker compose down inde-llm-gateway
docker compose up -d inde-llm-gateway

# View logs
docker compose logs inde-app --tail 100
docker compose logs inde-llm-gateway --tail 50
```

## Common Fixes

### Fix Windows line endings in .env (if symptoms: 401 on API key)
```bash
sed -i 's/\r$//' .env
```

### Test Nginx config and reload
```bash
nginx -t && systemctl reload nginx
```

## HTTPS Setup

See [deployment/nginx/README.md](nginx/README.md) for Certbot/Let's Encrypt instructions.

## Data Migration

To migrate data from v3.15 to v3.16:
```bash
bash scripts/migrate_v315_data.sh
```

## Full Deployment Checklist

1. [ ] Copy `.env.template` to `.env` and configure
2. [ ] Run `bash scripts/validate_env.sh`
3. [ ] Build frontend: `cd frontend && npm install && npm run build && cd ..`
4. [ ] Start containers: `docker compose up -d`
5. [ ] Set up Nginx (see nginx/README.md)
6. [ ] Set up HTTPS with Certbot (see nginx/README.md)
7. [ ] Migrate data from v3.15 if applicable
8. [ ] Test health endpoint: `curl http://localhost:8000/api/v1/health`
