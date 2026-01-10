# Company Schema

Single company configuration for the Podium instance.

## Core Properties

```yaml
# Identity
company_name: string       # Business name
company_email: string      # Primary contact email
company_phone: string      # Phone number
company_address: string    # Full mailing address

# Branding
logo_url: string           # URL to company logo (stored on n8n server)
primary_color: string      # Hex color for branding (e.g., "#6c63ff")
tagline: string            # Short business tagline

# Metadata
created_at: date           # Initial setup date
updated_at: date           # Last modification
```

## Example Company Object

```json
{
  "company_name": "Thai Directory",
  "company_email": "info@thaidirectory.com",
  "company_phone": "(555) 123-4567",
  "company_address": "123 Main St\nCity, ST 12345",
  "logo_url": "",
  "primary_color": "#6c63ff",
  "tagline": "Professional Directory Services",
  "created_at": "2026-01-09",
  "updated_at": "2026-01-09"
}
```

## API Operations

**Endpoint:** `POST /webhook/podium-company`

```json
// Get company info
{ "action": "get" }

// Save company info
{
  "action": "save",
  "company_name": "Thai Directory",
  "company_email": "info@thaidirectory.com",
  ...
}
```

## Usage

- Settings page loads company info on init
- Dashboard can pull company_name for branding
- Flows can use company info in proposals/invoices
