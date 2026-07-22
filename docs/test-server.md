# Test Server (Thorin)

A local test server running on Thorin with a copy of the production database, for prototyping and testing changes before deploying.

## What's Running

| Component | Details |
|-----------|---------|
| **Postgres** | Docker container `conductor-test-db` (postgres:15-alpine), port `127.0.0.1:5433` |
| **FastAPI / uvicorn** | Port `3001`, serving API + built Vue SPA from `frontend/dist/` |
| **Frontend** | Pre-built (`npm run build` in `frontend/`), served statically by FastAPI |
| **DB data** | Full production dump (pg_dump from droplet, restored into container) |

## Access

- **URL:** `http://100.86.206.66:3001` (Tailscale only — any device on the tailnet)
- **API:** `http://100.86.206.66:3001/api/*`
- **QA login:** `qa_test@conductor.test` / `testtest`

## Starting the Test Server

### 1. Start the database container (if not running)

```bash
docker start conductor-test-db
```

If the container doesn't exist yet (first-time setup):

```bash
docker run -d \
  --name conductor-test-db \
  -e POSTGRES_USER=conductor \
  -e POSTGRES_PASSWORD=conductor \
  -e POSTGRES_DB=conductor \
  -p 127.0.0.1:5433:5432 \
  postgres:15-alpine
```

### 2. Build the frontend (if frontend changed)

```bash
cd /home/hermes/repos/podium/frontend
npm install   # first time only
npm run build
```

### 3. Start uvicorn

```bash
cd /home/hermes/repos/podium
CONDUCTOR_DATABASE_URL="postgresql://conductor:conductor@localhost:5433/conductor" \
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 3001
```

Add `--reload` for hot-reload during development (API changes only; for frontend changes re-run `npm run build`).

## Refreshing the Database from Production

To get a fresh copy of production data:

```bash
# Dump from the droplet and pipe into the local container
ssh root@tie-conductor "sudo -u postgres pg_dump --no-owner --no-acl conductor" \
  | docker exec -i conductor-test-db psql -U conductor -d conductor
```

This overwrites all data in the test DB. No data is written back to production.

## Stopping

```bash
# Stop uvicorn: Ctrl+C or kill the process
# Stop the database container:
docker stop conductor-test-db
```

## Notes

- The test DB is completely isolated from production. Changes here have zero effect on prod.
- The `uploads/` directory at the repo root must exist or FastAPI fails to start (StaticFiles mount).
- Python venv is at `/home/hermes/repos/podium/.venv` (Python 3.11).
- No Caddy or reverse proxy — uvicorn is directly accessible on the tailnet.
