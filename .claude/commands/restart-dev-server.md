Restart the local test server on the canonical port 3100.

1. Kill any existing Conductor server processes (from previous manual runs):
   - `pkill -f "uvicorn app.main:app"` (or on Windows: kill the process on port 3100), wait 1 second.
2. Start the self-contained local test server from the repository root:
   ```bash
   bash scripts/start-local.sh
   ```
   This launcher: creates `.venv` and installs Python deps via `uv` if needed, verifies
   local PostgreSQL is listening, restores the `db/local-test-server.sql` snapshot into
   `conductor_dev` on first run, builds the Vue SPA, and serves both API and SPA from
   FastAPI/Uvicorn on port 3100.
3. Verify both endpoints return 200, then report the HTTP status codes:
   - `http://127.0.0.1:3100/` (SPA root)
   - `http://127.0.0.1:3100/api/clients` (API)
4. Always end your response with the clickable link: http://127.0.0.1:3100

Note: the app is deliberately bound to loopback only, and the frontend shows an
orange "TEST SERVER — not production" banner/frame. See `docs/local-test-server.md`
for full setup, troubleshooting, and reset instructions.
