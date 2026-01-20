# Podium Deployment & Architecture

## Infrastructure Overview

Podium runs on a DigitalOcean droplet alongside n8n, using Docker Compose for orchestration.

```
┌─────────────────────────────────────────────────────────────────┐
│                    DigitalOcean Droplet                         │
│                    64.23.152.174                                │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                 Docker Compose Stack                     │   │
│   │                                                          │   │
│   │   ┌─────────┐  ┌──────────────┐  ┌─────────┐            │   │
│   │   │  Caddy  │  │ OAuth2 Proxy │  │   n8n   │            │   │
│   │   │  :443   │  │    :4180     │  │  :5678  │            │   │
│   │   └────┬────┘  └──────────────┘  └─────────┘            │   │
│   │        │                                                 │   │
│   │        └── Reverse proxy + TLS termination              │   │
│   │                                                          │   │
│   │   Volumes:                                               │   │
│   │   - /opt/n8n-docker-caddy/podium (static files)         │   │
│   │   - n8n_data (n8n workflows & credentials)              │   │
│   │   - caddy_data (TLS certificates)                       │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## URLs

| URL | Purpose | Auth |
|-----|---------|------|
| `https://pm.irrigationengineers.com` | Podium dashboard | Google OAuth (@irrigationengineers.com) |
| `https://pm.irrigationengineers.com/ops/*` | Protected admin pages | Google OAuth |
| `https://pm.irrigationengineers.com/flows/*` | Client-facing pages | Public |
| `https://n8n.irrigationengineers.com` | n8n workflow editor | n8n built-in auth |

## Authentication Flow

Podium uses OAuth2 Proxy with Google OAuth for employee authentication.

```
┌──────────┐     ┌─────────┐     ┌──────────────┐     ┌────────┐
│  Browser │────►│  Caddy  │────►│ OAuth2 Proxy │────►│ Google │
└──────────┘     └─────────┘     └──────────────┘     └────────┘
     │                │                  │                  │
     │  1. GET /ops/dashboard.html       │                  │
     │───────────────►│                  │                  │
     │                │                  │                  │
     │                │  2. forward_auth │                  │
     │                │─────────────────►│                  │
     │                │                  │                  │
     │                │  3. No cookie = 401                 │
     │                │◄─────────────────│                  │
     │                │                  │                  │
     │  4. 302 Redirect to /oauth2/start │                  │
     │◄───────────────│                  │                  │
     │                │                  │                  │
     │  5. Follow redirect               │                  │
     │───────────────────────────────────►                  │
     │                                   │                  │
     │  6. 302 Redirect to Google        │                  │
     │◄──────────────────────────────────│                  │
     │                                                      │
     │  7. User logs in with Google                         │
     │─────────────────────────────────────────────────────►│
     │                                                      │
     │  8. Google redirects to /oauth2/callback with code   │
     │◄─────────────────────────────────────────────────────│
     │                │                  │                  │
     │───────────────────────────────────►                  │
     │                                   │                  │
     │  9. OAuth2 Proxy validates, sets cookie              │
     │◄──────────────────────────────────│                  │
     │                │                  │                  │
     │  10. Redirect to original URL     │                  │
     │◄───────────────│                  │                  │
     │                │                  │                  │
     │  11. Request with valid cookie    │                  │
     │───────────────►│                  │                  │
     │                │  12. forward_auth passes            │
     │                │─────────────────►│                  │
     │                │◄─────────────────│                  │
     │                │                  │                  │
     │  13. Serve static file            │                  │
     │◄───────────────│                  │                  │
```

### Auth Configuration

- **Provider**: Google OAuth
- **Allowed domain**: `@irrigationengineers.com`
- **Cookie duration**: 7 days
- **Cookie name**: `_oauth2_proxy`

### Headers Passed to Backend

After successful auth, OAuth2 Proxy adds headers to requests:
- `X-Auth-Request-User`: Google user ID
- `X-Auth-Request-Email`: User's email address

## Data Flow

The dashboard is a static HTML/JS application that communicates with n8n webhooks for all data operations.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Browser      │     │      n8n        │     │  Google Sheets  │
│  (dashboard.js) │     │   (webhooks)    │     │   (storage)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │  fetch(/webhook/      │                       │
         │    podium-api)        │                       │
         │──────────────────────►│                       │
         │                       │                       │
         │                       │  Read/Write data      │
         │                       │──────────────────────►│
         │                       │◄──────────────────────│
         │                       │                       │
         │  JSON response        │                       │
         │◄──────────────────────│                       │
         │                       │                       │
```

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/webhook/podium-api` | Project CRUD operations |
| `/webhook/podium-clients` | Client CRUD operations |
| `/webhook/podium-company` | Company settings |
| `/webhook/podium-invoice-create` | Create invoice from template |
| `/webhook/podium-invoice-send` | Send invoice via email |

See `ops/README.md` for detailed API documentation.

## Deployment

### Auto-Deploy via GitHub Actions

Pushes to `main` or `feature/invoicing` trigger automatic deployment.

```
┌──────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub  │────►│ GitHub Actions  │────►│    Droplet      │
│   Push   │     │   (deploy.yml)  │     │   (git pull)    │
└──────────┘     └─────────────────┘     └─────────────────┘
```

**Workflow**: `.github/workflows/deploy.yml`

The action:
1. SSHs to the droplet using `DROPLET_SSH_KEY` secret
2. Runs `git pull` in `/opt/n8n-docker-caddy/podium`
3. Changes are immediately live (static files, no build step)

### Manual Deployment

```bash
ssh root@n8n.irrigationengineers.com
cd /opt/n8n-docker-caddy/podium
git pull origin main
```

### Docker Stack Management

```bash
ssh root@n8n.irrigationengineers.com
cd /opt/n8n-docker-caddy

# View running containers
docker compose ps

# View logs
docker logs n8n-docker-caddy-caddy-1
docker logs n8n-docker-caddy-oauth2-proxy-1
docker logs n8n-docker-caddy-n8n-1

# Restart stack
docker compose down && docker compose up -d

# Reload Caddy config (no downtime)
docker exec n8n-docker-caddy-caddy-1 caddy reload --config /etc/caddy/Caddyfile
```

## Configuration Files

All config files are on the droplet at `/opt/n8n-docker-caddy/`:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Container orchestration |
| `caddy_config/Caddyfile` | Reverse proxy & routing |
| `.env` | Environment variables |
| `podium/` | Static files (git repo) |

### Key Environment Variables

```bash
# .env
DATA_FOLDER=/opt/n8n-docker-caddy
DOMAIN_NAME=irrigationengineers.com
SUBDOMAIN=n8n
SSL_EMAIL=tim@irrigationengineers.com
GENERIC_TIMEZONE=America/Denver
```

### OAuth2 Proxy Settings

Configured via command-line args in `docker-compose.yml`:
- `--email-domain=irrigationengineers.com` - Restrict to company domain
- `--cookie-secure=true` - HTTPS-only cookies
- `--redirect-url=https://pm.irrigationengineers.com/oauth2/callback`

## DNS Configuration

Both subdomains point to the same droplet IP:

| Record | Type | Value |
|--------|------|-------|
| `n8n.irrigationengineers.com` | A | 64.23.152.174 |
| `pm.irrigationengineers.com` | A | 64.23.152.174 |

Managed in Dreamhost DNS panel.

## Security Notes

1. **OAuth2 Proxy** handles all authentication - no credentials stored in Podium
2. **Caddy** terminates TLS with auto-renewed Let's Encrypt certificates
3. **n8n webhooks** are public but should validate requests in workflows
4. **SSH key** for deployment stored as GitHub secret (`DROPLET_SSH_KEY`)

## Troubleshooting

### Blank page after login
- Hard refresh (Ctrl+Shift+R) to clear cached responses
- Check browser console for JavaScript errors
- Verify n8n webhooks are responding

### Auth redirect loop
- Clear cookies for `pm.irrigationengineers.com`
- Check OAuth2 Proxy logs: `docker logs n8n-docker-caddy-oauth2-proxy-1`

### Deploy not working
- Check GitHub Actions tab for errors
- Verify SSH key is set in repo secrets
- Test manual SSH: `ssh root@n8n.irrigationengineers.com`

### Caddy config changes not taking effect
```bash
docker exec n8n-docker-caddy-caddy-1 caddy reload --config /etc/caddy/Caddyfile
```
