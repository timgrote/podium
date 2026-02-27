import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .routers import auth, clients, company, contracts, employees, flows, invoices, projects, proposals, reports, tasks, uploads

_log_file = Path(__file__).resolve().parent.parent / "conductor.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(), logging.FileHandler(_log_file)],
)
logger = logging.getLogger("conductor")

app = FastAPI(title="Conductor API", version="1.0.0")


@app.middleware("http")
async def log_api_requests(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    body = b""
    if request.method in ("POST", "PATCH", "PUT"):
        body = await request.body()

    start = time.time()
    response = await call_next(request)
    ms = (time.time() - start) * 1000

    msg = f"{request.method} {request.url.path} -> {response.status_code} ({ms:.0f}ms)"
    if body:
        msg += f" body={body[:500].decode(errors='replace')}"
    logger.info(msg)
    return response


frontend_mode = os.environ.get("CONDUCTOR_FRONTEND_MODE", "legacy")


if frontend_mode != "vue":
    @app.get("/")
    def root_redirect():
        return RedirectResponse(url="/ops/dashboard.html")


# --- API routers ---
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(company.router, prefix="/api/company", tags=["company"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["contracts"])
app.include_router(proposals.router, prefix="/api/proposals", tags=["proposals"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(employees.router, prefix="/api/employees", tags=["employees"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(flows.router, prefix="/api/flows", tags=["flows"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])

# --- Static files ---
static_root = Path(__file__).resolve().parent.parent

if frontend_mode == "vue":
    vue_dist = static_root / "frontend" / "dist"
    app.mount("/uploads", StaticFiles(directory=static_root / "uploads"), name="uploads")
    app.mount("/flows", StaticFiles(directory=static_root / "flows", html=True), name="flows")
    app.mount("/assets", StaticFiles(directory=vue_dist / "assets"), name="vue-assets")

    @app.get("/{path:path}")
    async def vue_spa_fallback(path: str):
        """Serve Vue SPA index.html for all non-API, non-static routes."""
        # If a real file exists in dist/, serve it
        file_path = vue_dist / path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for client-side routing
        return FileResponse(vue_dist / "index.html")
else:
    app.mount("/ops", StaticFiles(directory=static_root / "ops", html=True), name="ops")
    app.mount("/flows", StaticFiles(directory=static_root / "flows", html=True), name="flows")
    app.mount("/uploads", StaticFiles(directory=static_root / "uploads"), name="uploads")
