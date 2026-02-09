from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import clients, company, contracts, flows, invoices, projects, proposals

app = FastAPI(title="Podium API", version="1.0.0")

# --- API routers ---
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(company.router, prefix="/api/company", tags=["company"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["contracts"])
app.include_router(proposals.router, prefix="/api/proposals", tags=["proposals"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(flows.router, prefix="/api/flows", tags=["flows"])

# --- Static files ---
root = Path(__file__).resolve().parent.parent

app.mount("/ops", StaticFiles(directory=root / "ops", html=True), name="ops")
app.mount("/flows", StaticFiles(directory=root / "flows", html=True), name="flows")
app.mount("/uploads", StaticFiles(directory=root / "uploads"), name="uploads")
# Root last so it doesn't shadow other mounts
app.mount("/", StaticFiles(directory=root, html=True), name="root")
