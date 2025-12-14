# HED-BOT Deployment Guide

This guide provides deployment options for HED-BOT.

## Current Production Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  User Browser   │────────▶│ Cloudflare Pages │         │  hedtools.org   │
│                 │         │   (Frontend CDN)  │         │   (Backend)     │
└─────────────────┘         └──────────────────┘         │                 │
                                      │                   │  ┌───────────┐  │
                                      │ API Requests      │  │  FastAPI  │  │
                                      └──────────────────▶│  │  + LLM    │  │
                                        Direct HTTPS      │  │  (Docker) │  │
                                                          │  └───────────┘  │
                                                          └─────────────────┘
```

- **Frontend**: Cloudflare Pages (`hed-bot.pages.dev`, `develop.hed-bot.pages.dev`)
- **Backend**: Docker container on hedtools.org (`hedtools.org/hed-bot-api`, `hedtools.org/hed-bot-dev-api`)
- **Authentication**: API keys + Cloudflare Turnstile (bot protection)

## Deployment Options

### Option 1: Production Deployment (hedtools.org)

**Current setup for public access:**
- Frontend: Cloudflare Pages (auto-deploys from GitHub)
- Backend: Docker on hedtools.org server
- LLM: OpenRouter API (Cerebras provider)
- Cost: ~$2-5/month for API usage

See: [`deploy/README.md`](../../deploy/README.md)

### Option 2: Local GPU Development

**Best for:** Local development with your own GPU
- Backend runs locally with Ollama
- No API costs after setup
- Requires NVIDIA GPU with 24GB+ VRAM

See: [`docs/deployment/docker-quickstart.md`](docker-quickstart.md)

### Option 3: Local Development (No GPU)

**Best for:** Quick testing without GPU
- Uses OpenRouter API for LLM
- No Docker required
- Minimal setup

```bash
# Clone and setup
git clone https://github.com/neuromechanist/hed-bot.git
cd hed-bot

# Create environment
conda create -n hed-bot python=3.12
conda activate hed-bot
pip install -e ".[dev]"

# Set API key
export OPENROUTER_API_KEY="your-key"

# Run backend
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 38427

# Open frontend
open frontend/index.html
```

---

## Frontend Deployment (Cloudflare Pages)

The frontend is automatically deployed when changes are pushed to GitHub.

### Branch Deployments:
- `main` → `hed-bot.pages.dev` (production)
- `develop` → `develop.hed-bot.pages.dev` (development)

### Configuration

The frontend auto-detects environment via `frontend/config.js`:

```javascript
// Development (develop.hed-bot.pages.dev or localhost)
window.BACKEND_URL = 'https://hedtools.org/hed-bot-dev-api';

// Production (hed-bot.pages.dev)
window.BACKEND_URL = 'https://hedtools.org/hed-bot-api';
```

---

## Backend Deployment (Docker)

See [`deploy/README.md`](../../deploy/README.md) for complete Docker deployment instructions.

Quick reference:
```bash
# Build and deploy
./deploy/deploy.sh prod  # or 'dev' for development

# View logs
docker logs -f hed-bot-prod

# Health check
curl https://hedtools.org/hed-bot-api/health
```

---

## Security

- **API Authentication**: X-API-Key header for protected endpoints
- **Bot Protection**: Cloudflare Turnstile (silent CAPTCHA)
- **CORS**: Strict origin validation
- **Audit Logging**: All requests logged

See: [`SECURITY.md`](../../SECURITY.md)
