# API and Deployment Architecture

## FastAPI Backend (`src/api/main.py`)

### Endpoints
- `POST /annotate`: Text-to-HED annotation
- `POST /annotate/stream`: Streaming annotation via Server-Sent Events (SSE)
- `POST /annotate-from-image`: Image-to-HED annotation
- `POST /annotate-from-image/stream`: Streaming image annotation
- `POST /validate`: Standalone HED validation
- `POST /feedback`: User feedback submission
- `GET /health`: Service health check
- `GET /version`: Version information

### Authentication Modes
1. **Server mode**: `X-API-Key` header (server's OpenRouter key)
2. **BYOK mode**: `X-OpenRouter-Key` header (user's own API key)
3. **Public endpoints**: `/feedback`, `/health`, `/version`

### Model Override Headers
- `X-OpenRouter-Model`: Override annotation model
- `X-OpenRouter-Vision-Model`: Override vision model
- `X-OpenRouter-Provider`: Override provider routing
- `X-OpenRouter-Temperature`: Override temperature

### CORS
- Production: `hedit.pages.dev`, `annotation.garden`
- Development: Cloudflare Workers, localhost
- Custom: `EXTRA_CORS_ORIGINS` environment variable

## Deployment

### Docker
- Image: `hedit-api`
- Ports: 38427 (production), 38428 (development)
- Includes: Python, Node.js, HED schemas, JavaScript validator

### API Hosting (api.annotation.garden)
- Cloudflare DNS: CNAME `api` -> `hedtools.ucsd.edu`
- Cloudflare SSL: Origin Certificate for SCCN VM
- Apache reverse proxy: `/hedit` (prod), `/hedit-dev` (dev)

### Frontend (Cloudflare Pages)
- URL: `https://hedit.pages.dev`
- Static HTML/CSS/JS
- Cloudflare Workers proxy for API routing
- SSE streaming support

## CLI (`src/cli/`)
- Built with Typer + Rich
- Commands: `annotate`, `annotate-image`, `validate`, `health`, `init`, `config`
- Config: `~/.config/hedit/config.yaml` + `credentials.yaml`
- Supports both local and remote API modes
