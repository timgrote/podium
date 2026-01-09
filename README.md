# Podium

Irrigation design services platform.

## Overview

Podium connects landscape architects with irrigation designers. Upload your planting plan, get a quote, pay, and receive a professional irrigation design.

## Architecture

- **Landing Page**: Static HTML hosted on GitHub Pages
- **Backend**: n8n workflow handles intake submissions
- **Notifications**: Email with attached files

## Development

This is a static site. Just edit `index.html` and push.

### Local Preview

```bash
# Python
python -m http.server 8000

# Node
npx serve
```

Then open http://localhost:8000

## Webhook Endpoint

```
POST https://n8n.irrigationengineers.com/webhook/podium-intake
```

Accepts multipart form data with:
- `project_name` - Project name
- `client_name` - Client name
- `client_email` - Client email
- `notes` - Project notes
- `data` - File upload (ZIP, DWG, DXF, PDF)
