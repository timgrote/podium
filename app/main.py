import logging
import time
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .routers import api_keys, auth, clients, company, contacts, contracts, employees, flows, invoices, projects, proposals, tasks, time_entries, uploads, updates

_log_file = Path(__file__).resolve().parent.parent / "conductor.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(), logging.FileHandler(_log_file)],
)
logger = logging.getLogger("conductor")

app = FastAPI(title="Conductor API", version="1.0.0")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    logger.warning(f"HTTPException {exc.status_code} {request.method} {request.url.path}: {exc.detail}\n{''.join(tb)}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    logger.error(f"Unhandled {request.method} {request.url.path}: {exc}\n{''.join(tb)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


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
    if response.status_code >= 400:
        logger.warning(msg)
    else:
        logger.info(msg)
    return response


# --- API routers ---
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(api_keys.router, prefix="/api/auth", tags=["api-keys"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(company.router, prefix="/api/company", tags=["company"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["contracts"])
app.include_router(proposals.router, prefix="/api/proposals", tags=["proposals"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(employees.router, prefix="/api/employees", tags=["employees"])
app.include_router(time_entries.router, prefix="/api/time-entries", tags=["time-entries"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(flows.router, prefix="/api/flows", tags=["flows"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
app.include_router(updates.router, prefix="/api/updates", tags=["updates"])

# --- Static files (Vue SPA) ---
static_root = Path(__file__).resolve().parent.parent
vue_dist = static_root / "frontend" / "dist"

app.mount("/uploads", StaticFiles(directory=static_root / "uploads"), name="uploads")
app.mount("/flows", StaticFiles(directory=static_root / "flows", html=True), name="flows")
app.mount("/assets", StaticFiles(directory=vue_dist / "assets"), name="vue-assets")


@app.get("/{path:path}")
async def vue_spa_fallback(path: str):
    """Serve Vue SPA index.html for all non-API, non-static routes."""
    file_path = vue_dist / path
    if file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(vue_dist / "index.html")
