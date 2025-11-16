# HED-BOT Worker Proxy Setup

The Cloudflare Worker now acts as a **caching proxy** to your Python FastAPI backend, which contains all the strong prompts, real HED validation, and multi-agent workflow.

## Architecture

```
User → Cloudflare Worker → Cloudflare Tunnel → Python Backend (localhost:38427)
        (caching, rate limiting)                   (HED validation, LLM agents)
```

## Setup Steps

### 1. Expose Python Backend with Cloudflare Tunnel

You need to create a public URL for your local Python backend running on port 38427.

#### Option A: Quick Tunnel (for testing)

```bash
# Start quick tunnel (gives random URL, no uptime guarantee)
cloudflared tunnel --url http://localhost:38427
```

This will output something like:
```
https://random-name-1234.trycloudflare.com
```

Copy this URL - you'll need it in step 2.

**Note**: Quick tunnels have no uptime guarantee and are not recommended for production.

#### Option B: Named Tunnel (for production)

1. Login to Cloudflare:
```bash
cloudflared tunnel login
```

2. Create a named tunnel:
```bash
cloudflared tunnel create hed-bot-backend
```

3. Create config file at `~/.cloudflared/config.yml`:
```yaml
tunnel: hed-bot-backend
credentials-file: /home/yahya/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: hed-api.your-domain.com  # Replace with your subdomain
    service: http://localhost:38427
  - service: http_status:404
```

4. Route DNS to your tunnel:
```bash
cloudflared tunnel route dns hed-bot-backend hed-api.your-domain.com
```

5. Run tunnel:
```bash
cloudflared tunnel run hed-bot-backend
```

Or install as a service:
```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

Your backend will be available at: `https://hed-api.your-domain.com`

### 2. Configure Worker with Backend URL

Set the backend URL as a secret in your worker:

```bash
cd /home/yahya/git/hed-bot/workers

# Replace with your tunnel URL
echo "https://your-tunnel-url.trycloudflare.com" | npx wrangler secret put BACKEND_URL
```

### 3. Deploy Worker

```bash
npx wrangler deploy
```

You should see output like:
```
Deployed hed-bot-neuromechanist triggers
  https://hed-bot-neuromechanist.shirazi-10f.workers.dev
```

### 4. Test the Setup

#### Test health endpoint:
```bash
curl https://hed-bot-neuromechanist.shirazi-10f.workers.dev/health | jq .
```

Expected output:
```json
{
  "status": "healthy",
  "proxy": "operational",
  "backend": {
    "status": "healthy",
    "version": "0.1.0",
    "llm_available": true,
    "validator_available": true
  },
  "backend_url": "https://your-tunnel-url.trycloudflare.com"
}
```

#### Test annotation:
```bash
curl -X POST https://hed-bot-neuromechanist.shirazi-10f.workers.dev/annotate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "A red circle appears on the left side of the screen and the user clicks it with the left mouse button",
    "schema_version": "8.3.0",
    "max_validation_attempts": 3
  }' | jq .
```

Expected output should include:
```json
{
  "annotation": "Sensory-event, Visual-presentation, ...",
  "is_valid": true,
  "is_faithful": true,
  "validation_attempts": 1,
  ...
}
```

### 5. Update Frontend

Update `frontend/config.js`:
```javascript
window.BACKEND_URL = 'https://hed-bot-neuromechanist.shirazi-10f.workers.dev';
```

## Features

### Caching
- 1 hour TTL for successful annotations
- Reduces API costs and improves response time
- Cache key: `hed:{schema_version}:{description}`

### Rate Limiting
- 20 requests per minute per IP
- Prevents abuse
- Uses Cloudflare KV for distributed rate limiting

### Request Timeout
- 2 minutes for annotation workflows
- Prevents hanging requests

## Troubleshooting

### "Backend not configured" error
```bash
# Make sure BACKEND_URL secret is set
npx wrangler secret list
```

### "Backend unreachable" error
```bash
# Check if tunnel is running
ps aux | grep cloudflared

# Check tunnel logs
tail -f /tmp/cloudflared-hed-backend.log

# Test backend directly
curl http://localhost:38427/health
```

### "Context deadline exceeded"
- Tunnel creation failed due to network timeout
- Try again or use a different network
- Consider using a VPN if firewall is blocking tunnel creation

## Production Considerations

1. **Use Named Tunnel**: Quick tunnels are not reliable for production
2. **Monitor Backend**: Ensure Python backend stays running (use systemd or Docker)
3. **Environment Variables**: Backend needs `OPENROUTER_API_KEY` set
4. **Scaling**: For high traffic, consider deploying backend to a cloud provider
5. **Costs**: ~$2-5/month for 10k annotations with caching

## Alternative: Deploy Backend to Cloud

Instead of using Cloudflare Tunnel, you can deploy the Python backend to:

- **Fly.io**: `fly launch` in project root
- **Railway**: Connect GitHub repo
- **Heroku**: Use Dockerfile for deployment
- **Google Cloud Run**: Serverless container deployment
- **AWS ECS/Fargate**: For production scale

Then set the deployed URL as `BACKEND_URL`.
