from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .routers import auth, clients, company, contracts, employees, flows, invoices, projects, proposals, tasks

app = FastAPI(title="Conductor API", version="1.0.0")


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
app.include_router(flows.router, prefix="/api/flows", tags=["flows"])

# --- Static files ---
static_root = Path(__file__).resolve().parent.parent

app.mount("/ops", StaticFiles(directory=static_root / "ops", html=True), name="ops")
app.mount("/flows", StaticFiles(directory=static_root / "flows", html=True), name="flows")
app.mount("/uploads", StaticFiles(directory=static_root / "uploads"), name="uploads")
