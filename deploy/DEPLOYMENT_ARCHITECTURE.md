# HED-BOT Deployment Architecture

This document explains the deployment architecture for hedtools.org with proper CORS and security configuration.

## Overview

**Server**: hedtools.org (hedtools.ucsd.edu)
**Frontend**: `hed-bot.pages.dev` (Cloudflare Pages)
**Backend**: FastAPI + Docker

### Architecture

```
┌─────────────────────────────┐
│  hed-bot.pages.dev          │  ← Frontend (Cloudflare Pages)
│  (Static Site)              │
│                             │
│  - Production: main branch  │
│  - Development: develop     │
└──────────────┬──────────────┘
               │ HTTPS (Direct)
               ▼
┌─────────────────────────────┐
│  hedtools.org               │  ← Server
│                             │
│  Nginx Reverse Proxy        │
│  /hed-bot-api → :38427      │
│  /hed-bot-dev-api → :38428  │
│  (CORS validation)          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Docker Containers          │
│                             │
│  hed-bot-prod (38427)       │
│  hed-bot-dev (38428)        │
│  (FastAPI + CORS)           │
└─────────────────────────────┘
```

### Benefits

- **Simple**: Direct HTTPS connection, no proxy layers
- **Fast**: No extra hops
- **Secure**: CORS enforced at both Nginx and FastAPI layers
- **Maintainable**: Single deployment, easy to debug

### CORS Protection

**Two-Layer Defense:**

1. **Nginx Layer**: Only allows requests from allowed origins
2. **FastAPI Layer**: Validates Origin header programmatically

---

## Security Configuration

### CORS Origins

**Production**: `https://hed-bot.pages.dev`
**Development**: `https://develop.hed-bot.pages.dev`, localhost ports

### Authentication

- **API Keys**: X-API-Key header for protected endpoints
- **Turnstile**: Cloudflare Turnstile for bot protection (silent CAPTCHA)

### Environment Variables

```bash
# Required
OPENROUTER_API_KEY=your-key
HED_BOT_API_KEY=your-api-key

# Optional (for feedback processing)
GITHUB_TOKEN=your-github-token
OPENROUTER_API_KEY_FOR_TESTING=separate-key-for-feedback

# Turnstile
TURNSTILE_SECRET_KEY=your-turnstile-secret
```

### Nginx Security Headers

```nginx
# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

---

## Setup Instructions

### Step 1: Deploy Docker Container

```bash
# Deploy production container
./deploy/deploy.sh prod

# Or development
./deploy/deploy.sh dev

# Verify it's running
docker ps | grep hed-bot
curl http://localhost:38427/health
```

### Step 2: Configure Nginx

```bash
# Copy Nginx config
sudo cp deploy/nginx-hedtools.conf /etc/nginx/conf.d/hed-bot.conf

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Step 3: Test CORS

```bash
# Should succeed (from allowed origin)
curl -H "Origin: https://hed-bot.pages.dev" \
     -I https://hedtools.org/hed-bot-api/health

# Should fail (from disallowed origin)
curl -H "Origin: https://evil.com" \
     -I https://hedtools.org/hed-bot-api/health
```

---

## Testing Checklist

- [ ] Docker container builds successfully
- [ ] Container runs on correct port (38427 prod, 38428 dev)
- [ ] Nginx proxies correctly
- [ ] Health check accessible: `https://hedtools.org/hed-bot-api/health`
- [ ] CORS allows `hed-bot.pages.dev`
- [ ] CORS blocks other origins
- [ ] Frontend can make API requests
- [ ] Turnstile verification works
- [ ] Feedback endpoint works

---

## Troubleshooting

### CORS errors in browser console

**Error**: `Access to fetch at '...' has been blocked by CORS policy`

**Solutions**:
1. Check Nginx is running and configured correctly
2. Verify FastAPI CORS settings in `src/api/main.py`
3. Check Origin header in request
4. Look at response headers in Network tab

### 502 Bad Gateway

**Cause**: Nginx can't reach Docker container

**Solutions**:
1. Check container is running: `docker ps | grep hed-bot`
2. Check container health: `curl http://localhost:38427/health`
3. Check Nginx error logs: `sudo tail -f /var/log/nginx/error.log`

### Turnstile verification fails

**Error**: `Bot verification failed`

**Solutions**:
1. Ensure TURNSTILE_SECRET_KEY is set in environment
2. Check Turnstile token is being sent from frontend
3. Verify Turnstile site key matches secret key pair

---

**Last Updated**: December 14, 2025
