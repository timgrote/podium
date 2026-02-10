import glob
import logging
from pathlib import Path, PurePath

from fastapi import APIRouter, Depends, UploadFile, File

from ..database import get_db, get_database_url, set_database_url, clear_database_url
from ..models.company import CompanySettings

logger = logging.getLogger(__name__)

root = Path(__file__).resolve().parent.parent.parent

router = APIRouter()


def _ensure_table(db):
    db.execute(
        "CREATE TABLE IF NOT EXISTS company_settings (key TEXT PRIMARY KEY, value TEXT)"
    )
    db.commit()


@router.get("", response_model=CompanySettings)
def get_company(db=Depends(get_db)):
    _ensure_table(db)
    rows = db.execute("SELECT key, value FROM company_settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def _check_google_access(file_id: str, label: str) -> dict | None:
    """Check if the service account can access a Google Drive file/folder.
    Returns a warning dict if not accessible, None if OK."""
    sa_email = "unknown"
    try:
        from ..google_sheets import get_drive_service, _get_credentials
        creds = _get_credentials()
        sa_email = creds.service_account_email
        drive = get_drive_service()
        drive.files().get(fileId=file_id).execute()
        return None  # accessible
    except FileNotFoundError:
        return None  # no Google credentials configured, skip check
    except Exception as e:
        logger.warning("Google access check failed for %s (%s): %s", label, file_id, e)
        return {
            "field": label,
            "message": f"Cannot access {label}. Share it with: {sa_email}",
            "service_account_email": sa_email,
        }


@router.put("")
def save_company(data: CompanySettings, db=Depends(get_db)):
    _ensure_table(db)
    for key, value in data.model_dump().items():
        if value is not None:
            db.execute(
                "INSERT INTO company_settings (key, value) VALUES (%s, %s) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
    db.commit()
    rows = db.execute("SELECT key, value FROM company_settings").fetchall()
    result = {r["key"]: r["value"] for r in rows}

    # Check Google access for template and folder if they were just set
    warnings = []
    if data.invoice_template_id:
        w = _check_google_access(data.invoice_template_id, "invoice_template_id")
        if w:
            warnings.append(w)
    if data.invoice_drive_folder_id:
        w = _check_google_access(data.invoice_drive_folder_id, "invoice_drive_folder_id")
        if w:
            warnings.append(w)
    if warnings:
        result["_warnings"] = warnings

    return result


@router.post("/logo")
async def upload_logo(file: UploadFile = File(...), db=Depends(get_db)):
    _ensure_table(db)
    safe_name = PurePath(file.filename).name
    ext = Path(safe_name).suffix.lower() or ".png"
    # Remove any existing logo files
    for old in glob.glob(str(root / "uploads" / "logo.*")):
        Path(old).unlink()
    # Write new file
    dest = root / "uploads" / f"logo{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    dest.write_bytes(content)
    logo_url = f"/uploads/logo{ext}"
    # Save logo_url in settings
    db.execute(
        "INSERT INTO company_settings (key, value) VALUES ('logo_url', %s) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (logo_url,),
    )
    # Remove old base64 data
    db.execute("DELETE FROM company_settings WHERE key IN ('logo_data', 'logo_filename')")
    db.commit()
    return {"logo_url": logo_url}


# --- Database Connection ---

@router.get("/database")
def get_database_connection():
    """Return the current database URL and connection status."""
    url = get_database_url()
    # Test the connection
    connected = False
    error = None
    try:
        import psycopg2
        conn = psycopg2.connect(url, connect_timeout=3)
        conn.close()
        connected = True
    except Exception as e:
        error = str(e)
    return {"database_url": url, "connected": connected, "error": error}


@router.put("/database")
def set_database_connection(data: dict):
    """Update the database URL. Send {"database_url": "..."} or {"database_url": ""} to reset."""
    url = data.get("database_url", "").strip()
    if not url:
        clear_database_url()
        url = get_database_url()
    else:
        # Validate before saving
        try:
            import psycopg2
            conn = psycopg2.connect(url, connect_timeout=5)
            conn.close()
        except Exception as e:
            return {"success": False, "error": f"Cannot connect: {e}", "database_url": get_database_url()}
        set_database_url(url)
    return {"success": True, "database_url": url}
