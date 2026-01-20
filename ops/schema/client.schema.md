# Client Schema

Clients are stored as YAML frontmatter + markdown notes. Currently in n8n staticData, designed for future migration to Dropbox md files.

## Structure

```yaml
---
id: "client-uuid"           # Auto-generated unique ID
name: "Jim Birdsall"        # Display name (required)
email: "jim@birdsall.com"   # Primary email (required)
company: "Birdsall Homes"   # Company name (optional)
phone: "555-123-4567"       # Phone number (optional)
address: |                  # Multi-line address (optional)
  123 Main St
  Suite 100
  Portland, OR 97201
created_at: "2026-01-12"
updated_at: "2026-01-12"
---

## Notes

Free-form markdown notes about the client.
Meeting notes, preferences, history, etc.
```

## JSON Representation (n8n storage)

```json
{
  "id": "client-uuid",
  "name": "Jim Birdsall",
  "email": "jim@birdsall.com",
  "company": "Birdsall Homes",
  "phone": "555-123-4567",
  "address": "123 Main St\nSuite 100\nPortland, OR 97201",
  "notes": "## Notes\n\nFree-form markdown...",
  "created_at": "2026-01-12",
  "updated_at": "2026-01-12"
}
```

## API Actions

| Action | Method | Description |
|--------|--------|-------------|
| `list` | GET | List all clients |
| `get` | GET/POST | Get single client by id |
| `create` | POST | Create new client |
| `update` | POST | Update existing client |
| `delete` | POST | Delete client |
| `search` | GET | Search clients by name/email |

## Migration Path

When moving to Dropbox:
1. Each client becomes `clients/{id}.md`
2. YAML frontmatter contains structured fields
3. Markdown body contains notes
4. n8n workflow reads/writes via Dropbox API
