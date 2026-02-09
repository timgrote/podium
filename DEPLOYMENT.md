# DigitalOcean Deployment Guide

## Production Architecture
```
Tailscale Network → DigitalOcean Droplet → All Services
```

**Manual Transfer:**
```bash
rsync -av ~/.openclaw/ deploy@droplet:/home/deploy/.openclaw/
```

**Services:**
```bash
# Rotate services tailscale up prove-server
```