# Conductor API Reference

Base URL: `http://localhost:3000/api` (dev) or `https://conductor.yourdomain.com/api` (prod)

All endpoints accept and return JSON. Dates are ISO 8601 strings. Soft-deleted records are excluded from all queries automatically.

---

## Overview

Conductor manages the lifecycle of service projects:

```
Client → Project → Proposal → Contract → Invoice → Payment
```

**Entity relationships:**
- A **Client** can have many **Projects**
- A **Project** has one or more **Proposals**, **Contracts**, and **Invoices**
- A **Proposal** has **Proposal Tasks** (line items with fees)
- A **Contract** has **Contract Tasks** (line items that invoices bill against)
- An **Invoice** has **Line Items** and chains to previous invoices for cumulative billing
- **Projects** also have internal **Project Tasks** (work tracking, separate from billing)

**ID conventions:**
- Internal IDs are auto-generated with prefixes: `proj-` (project), `c-` (client), `con-` (contract), `prop-` (proposal), `inv-` (invoice), `ctask-` (contract task), `ptask-` (proposal task)
- Projects have three identifiers:
  - `id` — internal PK (e.g., `proj-a1b2c3d4`), used in all API calls
  - `project_number` — auto-incremented display ID (e.g., `26-001`), used in invoices
  - `job_code` — optional shorthand (e.g., `rvi-absal`), editable

---

## Authentication

Session-based auth via httponly cookies. Most `/api/auth/*` endpoints are public; all other endpoints require a valid session.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create account + session |
| POST | `/auth/login` | Login + create session |
| POST | `/auth/logout` | Destroy session |
| GET | `/auth/me` | Get current user (returns 401 if not logged in) |
| POST | `/auth/avatar` | Upload avatar image (multipart form) |
| POST | `/auth/reset-request` | Request password reset (admin) |
| POST | `/auth/reset-password` | Complete password reset |

### Signup

```
POST /api/auth/signup
```

```json
{
  "email": "tim@example.com",
  "password": "securepassword"
}
```

Returns employee object + sets session cookie.

### Login

```
POST /api/auth/login
```

```json
{
  "email": "tim@example.com",
  "password": "securepassword"
}
```

Returns employee object + sets session cookie.

---

## Clients

Clients are the companies or individuals you do business with.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/clients` | List all clients |
| GET | `/clients/{id}` | Get client by ID |
| POST | `/clients` | Create client |
| PATCH | `/clients/{id}` | Update client |
| DELETE | `/clients/{id}` | Soft-delete client |

### Create Client

```
POST /api/clients
```

```json
{
  "name": "John Beggs",
  "email": "jbeggs@rviplanning.com",
  "company": "RVi Planning + Landscape Architecture",
  "phone": "512-555-0100",
  "address": "123 Main St, Austin, TX 78701",
  "notes": "Preferred contact method: email"
}
```

**Required:** `name`
**Optional:** `email`, `company`, `phone`, `address`, `notes`

### Response

```json
{
  "id": "c-a1b2c3d4",
  "name": "John Beggs",
  "email": "jbeggs@rviplanning.com",
  "company": "RVi Planning + Landscape Architecture",
  "phone": "512-555-0100",
  "address": "123 Main St, Austin, TX 78701",
  "notes": null,
  "created_at": "2026-02-18T10:00:00",
  "updated_at": "2026-02-18T10:00:00"
}
```

### Update Client

```
PATCH /api/clients/{id}
```

Send only the fields you want to change:

```json
{
  "phone": "512-555-0200"
}
```

---

## Projects

Projects are the core entity. Each project tracks proposals, contracts, invoices, and internal tasks.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects` | List all projects (with nested contracts, invoices, proposals) |
| GET | `/projects/{id}` | Get project detail |
| POST | `/projects` | Create project |
| PATCH | `/projects/{id}` | Update project |
| DELETE | `/projects/{id}` | Soft-delete project (optional `?cascade=true`) |
| POST | `/projects/{id}/invoices` | Add standalone invoice to project |

### Create Project

```
POST /api/projects
```

```json
{
  "project_name": "Oak Valley HOA Irrigation",
  "job_code": "rvi-oakval",
  "client_name": "John Beggs",
  "client_email": "jbeggs@rviplanning.com",
  "client_id": null,
  "location": "Austin, TX",
  "status": "proposal",
  "data_path": "TBG/OakValley",
  "notes": "Phase 1 of 3"
}
```

**Required:** `project_name`
**Optional:** Everything else. If `client_email` is provided without `client_id`, the system auto-finds or creates the client.

**Auto-generated fields:**
- `id` — internal PK (`proj-xxxxxxxx`)
- `project_number` — sequential (`26-001`, `26-002`, etc.)

### Response (ProjectDetail)

```json
{
  "id": "proj-a1b2c3d4",
  "project_number": "26-003",
  "job_code": "rvi-oakval",
  "project_name": "Oak Valley HOA Irrigation",
  "status": "proposal",
  "client_id": "c-a1b2c3d4",
  "client_name": "John Beggs",
  "client_company": "RVi",
  "client_email": "jbeggs@rviplanning.com",
  "client_phone": null,
  "pm_name": null,
  "pm_email": null,
  "client_project_number": null,
  "location": "Austin, TX",
  "data_path": "TBG/OakValley",
  "notes": "Phase 1 of 3",
  "current_invoice_id": null,
  "total_contracted": 0,
  "total_invoiced": 0,
  "total_paid": 0,
  "total_outstanding": 0,
  "contracts": [],
  "invoices": [],
  "proposals": [],
  "created_at": "2026-02-18T10:00:00",
  "updated_at": "2026-02-18T10:00:00"
}
```

### Update Project

```
PATCH /api/projects/{id}
```

```json
{
  "name": "Oak Valley HOA - Phase 1",
  "status": "contract",
  "project_number": "26-003",
  "job_code": "rvi-oakval-1",
  "pm_name": "Jane Smith",
  "pm_email": "jane@example.com",
  "location": "Round Rock, TX",
  "client_project_number": "PO-2026-045"
}
```

All fields optional. Only sends what changed.

### Delete Project

```
DELETE /api/projects/{id}
DELETE /api/projects/{id}?cascade=true
```

Without `cascade`: soft-deletes the project only.
With `cascade=true`: also soft-deletes all contracts, invoices, and proposals.

### Status Workflow

Projects progress through these statuses:

```
proposal → contract → invoiced → paid → complete
```

---

## Proposals

Proposals are quotes sent to clients. They contain tasks with fees. Proposals can be promoted to contracts.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/proposals` | List all proposals |
| GET | `/proposals/defaults` | Get default engineer info for new proposals |
| GET | `/proposals/{id}` | Get proposal with tasks |
| POST | `/proposals` | Create proposal with inline tasks |
| PATCH | `/proposals/{id}` | Update proposal metadata |
| DELETE | `/proposals/{id}` | Soft-delete proposal |
| POST | `/proposals/{id}/tasks` | Add single task to proposal |
| PATCH | `/proposals/{id}/tasks/{task_id}` | Update a task |
| DELETE | `/proposals/{id}/tasks/{task_id}` | Delete a task |
| POST | `/proposals/{id}/promote` | Promote proposal to contract |
| POST | `/proposals/{id}/generate-doc` | Generate Google Doc |
| POST | `/proposals/{id}/export-pdf` | Export as PDF |
| POST | `/proposals/{id}/send` | Send via email |
| POST | `/proposals/generate` | All-in-one: create client + project + proposal + doc |

### Create Proposal (with tasks)

```
POST /api/proposals
```

```json
{
  "project_id": "proj-a1b2c3d4",
  "client_company": "RVi Planning",
  "client_contact_email": "jbeggs@rviplanning.com",
  "engineer_key": "tim",
  "engineer_name": "Tim Bienek",
  "engineer_title": "P.E.",
  "contact_method": "site meeting",
  "proposal_date": "2026-02-18",
  "status": "draft",
  "tasks": [
    { "name": "Irrigation Design", "description": "Full irrigation design for common areas", "amount": 5500 },
    { "name": "Construction Observation", "description": "Site visits during installation", "amount": 2200 },
    { "name": "Record Drawings", "amount": 1500 }
  ]
}
```

**Required:** `project_id`
**Optional:** Everything else. `total_fee` auto-computes from tasks if not provided.

### All-in-One Proposal Generation

Creates client, project, proposal, and optionally a Google Doc in one call. Ideal for automation.

```
POST /api/proposals/generate
```

```json
{
  "client_name": "John Beggs",
  "client_email": "jbeggs@rviplanning.com",
  "client_company": "RVi Planning",
  "client_address": "123 Main St",
  "client_city": "Austin",
  "client_state": "TX",
  "client_zip": "78701",
  "project_name": "Sunset Ridge HOA",
  "engineer_key": "tim",
  "contact_method": "phone call",
  "proposal_date": "2026-02-18",
  "tasks": [
    { "name": "Irrigation Design", "amount": 5500 },
    { "name": "Construction Observation", "amount": 2200 }
  ],
  "generate_doc": true
}
```

### Promote Proposal to Contract

Converts a proposal into a signed contract, copying all tasks as contract tasks.

```
POST /api/proposals/{id}/promote
```

Query params (optional):
- `signed_at` — date the contract was signed
- `file_path` — path to signed PDF

---

## Contracts

Contracts are signed agreements with task-based billing. Invoices are generated from contract tasks.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/contracts/{id}` | Get contract with tasks |
| POST | `/contracts` | Create contract (with optional inline tasks) |
| DELETE | `/contracts/{id}` | Soft-delete contract |
| POST | `/contracts/{id}/tasks` | Add single task |
| PATCH | `/contracts/{id}/tasks/{task_id}` | Update task |
| DELETE | `/contracts/{id}/tasks/{task_id}` | Delete task |
| POST | `/contracts/{id}/invoices` | Create invoice from contract tasks |

### Create Contract (with tasks)

```
POST /api/contracts
```

```json
{
  "project_id": "proj-a1b2c3d4",
  "signed_at": "2026-02-15",
  "file_path": "/contracts/rvi-oakval-signed.pdf",
  "notes": "Signed by John Beggs",
  "tasks": [
    { "name": "Irrigation Design", "amount": 5500 },
    { "name": "Construction Observation", "amount": 2200 },
    { "name": "Record Drawings", "amount": 1500 }
  ]
}
```

**Required:** `project_id`
**Optional:** Everything else. `total_amount` auto-computes from tasks.

### Response (Contract with Tasks)

```json
{
  "id": "con-b2c3d4e5",
  "project_id": "proj-a1b2c3d4",
  "total_amount": 9200.00,
  "signed_at": "2026-02-15",
  "file_path": "/contracts/rvi-oakval-signed.pdf",
  "notes": "Signed by John Beggs",
  "created_at": "2026-02-18T10:00:00",
  "updated_at": "2026-02-18T10:00:00",
  "deleted_at": null,
  "tasks": [
    {
      "id": "ctask-c3d4e5f6",
      "contract_id": "con-b2c3d4e5",
      "sort_order": 1,
      "name": "Irrigation Design",
      "description": null,
      "amount": 5500.00,
      "billed_amount": 0.00,
      "billed_percent": 0.00,
      "created_at": "2026-02-18T10:00:00",
      "updated_at": "2026-02-18T10:00:00"
    }
  ]
}
```

### Add Single Task to Contract

```
POST /api/contracts/{id}/tasks
```

```json
{
  "name": "Additional Scope - Pump Station",
  "description": "Design pump station per change order",
  "amount": 3500
}
```

### Create Invoice from Contract

Creates a task-based invoice by specifying what percentage of each contract task to bill.

```
POST /api/contracts/{id}/invoices
```

```json
{
  "tasks": [
    { "task_id": "ctask-c3d4e5f6", "percent_this_invoice": 50 },
    { "task_id": "ctask-d4e5f6g7", "percent_this_invoice": 25 }
  ],
  "pm_email": "tim@example.com"
}
```

This creates the invoice, line items, updates `billed_amount`/`billed_percent` on each contract task, and optionally generates a Google Sheet.

---

## Invoices

Invoices support chaining (each invoice knows its predecessor) for cumulative billing on task-based contracts.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/invoices/{id}` | Get invoice with line items |
| GET | `/invoices/by-number/{number}` | Look up by invoice number (e.g., `26-001-1`) |
| PATCH | `/invoices/{id}` | Update invoice |
| DELETE | `/invoices/{id}` | Soft-delete invoice |
| POST | `/invoices/{id}/export-pdf` | Export Google Sheet as PDF |
| POST | `/invoices/{id}/finalize` | Finalize line items |
| POST | `/invoices/{id}/send` | Send via Google email |
| POST | `/invoices/{id}/create-next` | Create next invoice in chain |

### Invoice Number Format

Invoice numbers are auto-generated: `{project_number}-{sequence}`

Example: Project `26-001` gets invoices `26-001-1`, `26-001-2`, etc.

### Update Invoice

```
PATCH /api/invoices/{id}
```

```json
{
  "sent_status": "sent",
  "paid_status": "paid",
  "total_due": 4500.00
}
```

**Status values:**
- `sent_status`: `unsent`, `sent`
- `paid_status`: `unpaid`, `partial`, `paid`

---

## Project Tasks

Internal work tracking tasks (separate from billing contract/proposal tasks). Supports subtasks, assignees, notes, and status tracking.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects/{id}/tasks` | List tasks for a project |
| POST | `/projects/{id}/tasks` | Create task |
| GET | `/tasks/{id}` | Get single task with subtasks, notes, assignees |
| PATCH | `/tasks/{id}` | Update task |
| DELETE | `/tasks/{id}` | Soft-delete task |
| POST | `/tasks/{id}/notes` | Add note to task |
| DELETE | `/tasks/notes/{note_id}` | Delete note |

### Create Task

```
POST /api/projects/{project_id}/tasks
```

```json
{
  "title": "Review irrigation plans",
  "description": "Check valve sizing and pipe routing",
  "status": "todo",
  "parent_id": null,
  "start_date": "2026-02-18",
  "due_date": "2026-02-25",
  "assignee_ids": ["emp-a1b2c3d4"]
}
```

**Status values:** `todo`, `in_progress`, `blocked`, `done`, `canceled`

---

## Employees

Internal staff members.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/employees` | List all active employees |
| GET | `/employees/{id}` | Get employee |
| POST | `/employees` | Create employee |
| PATCH | `/employees/{id}` | Update employee |
| DELETE | `/employees/{id}` | Soft-delete employee |

### Create Employee

```
POST /api/employees
```

```json
{
  "first_name": "Tim",
  "last_name": "Bienek",
  "email": "tim@example.com"
}
```

---

## Company Settings

Key-value store for company branding, contact info, and integration settings.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/company` | Get all settings |
| PUT | `/company` | Update settings |
| POST | `/company/logo` | Upload company logo |

### Update Settings

```
PUT /api/company
```

```json
{
  "company_name": "TBG Engineers",
  "company_email": "info@tbg.com",
  "company_phone": "512-555-0100",
  "company_address": "100 Congress Ave, Austin TX"
}
```

---

## Common Patterns

### Bulk Import Workflow

To import an existing project with contract and tasks:

```bash
# 1. Create client
curl -X POST /api/clients \
  -H "Content-Type: application/json" \
  -d '{"name": "John Beggs", "email": "jbeggs@rvi.com", "company": "RVi"}'

# 2. Create project (auto-generates project_number)
curl -X POST /api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Sunset Ridge HOA",
    "job_code": "rvi-sunridge",
    "client_email": "jbeggs@rvi.com",
    "location": "Round Rock, TX",
    "status": "contract"
  }'

# 3. Add contract with tasks (use the project id from step 2)
curl -X POST /api/contracts \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj-xxxxxxxx",
    "signed_at": "2026-01-15",
    "tasks": [
      {"name": "Irrigation Design", "amount": 5500},
      {"name": "Construction Observation", "amount": 2200},
      {"name": "Record Drawings", "amount": 1500}
    ]
  }'
```

### Error Responses

All errors return JSON with a `detail` field:

```json
{ "detail": "Project not found" }
```

Common status codes:
- `400` — Bad request (validation error)
- `401` — Not authenticated
- `404` — Entity not found
- `409` — Conflict (duplicate)
- `422` — Validation error (Pydantic)

### Soft Deletes

All DELETE endpoints perform soft deletes (set `deleted_at` timestamp). Records are excluded from all GET queries but remain in the database.

### Nested Data

`GET /projects` and `GET /projects/{id}` return nested arrays for `contracts`, `invoices`, and `proposals`, each with their own nested `tasks` arrays. This gives you the full project picture in a single call.
