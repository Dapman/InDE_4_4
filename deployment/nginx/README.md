# Nginx Configuration

## Apply HTTP Configuration (Pre-HTTPS)

```bash
sudo cp deployment/nginx/inde.conf /etc/nginx/sites-available/inde
sudo ln -sf /etc/nginx/sites-available/inde /etc/nginx/sites-enabled/inde
sudo nginx -t && sudo systemctl reload nginx
```

## Setting Up HTTPS with Certbot

### Prerequisites
- Domain name pointing to your server IP (A record)
- Port 80 accessible from the internet

### Install Certbot
```bash
apt update
apt install -y certbot python3-certbot-nginx
```

### Issue Certificate
```bash
# Replace app.indeverse.com with your actual domain
certbot --nginx -d app.indeverse.com --non-interactive --agree-tos \
  --email admin@indeverse.com --redirect
```

### Apply HTTPS Configuration (Post-Certbot)

After Certbot runs, it modifies the Nginx config automatically. You can also use our template:

```bash
# Edit inde-ssl.conf to replace 'app.indeverse.com' with your domain
sudo cp deployment/nginx/inde-ssl.conf /etc/nginx/sites-available/inde
sudo nginx -t && sudo systemctl reload nginx
```

## Certificate Auto-Renewal

Certbot installs an automatic renewal timer. Verify it's active:

```bash
systemctl status certbot.timer
```

Test renewal (dry run):
```bash
certbot renew --dry-run
```

If the timer is not active, add a cron job:
```bash
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo tee /etc/cron.d/certbot
```

## Verification

Test HTTPS is working:
```bash
curl -I https://app.indeverse.com/api/v1/health
# Expected: HTTP/2 200 + strict-transport-security header
```

Test WebSocket (from browser console on HTTPS page):
```javascript
new WebSocket('wss://app.indeverse.com/ws/test')
// Expected: connection established (then closed — /ws/test is not a real endpoint)
```
