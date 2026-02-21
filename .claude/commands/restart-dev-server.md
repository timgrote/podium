Kill any running dev servers and start fresh ones for both the FastAPI backend and Vue frontend.

1. Kill existing processes: `pkill -f "uvicorn app.main:app"` and `pkill -f "vite"`, wait 1 second.
2. Start the FastAPI backend: `source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload` in the background.
3. Start the Vue dev server: `cd frontend && npm run dev` in the background.
4. Verify both are up by curling `http://localhost:3000/api/clients` (backend) and `http://localhost:5173` (frontend). Report both HTTP status codes.
5. Always end your response with the clickable link: http://localhost:5173
