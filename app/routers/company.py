import glob
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File

from ..database import get_db
from ..models.company import CompanySettings

root = Path(__file__).resolve().parent.parent.parent

router = APIRouter()


def _ensure_table(db: sqlite3.Connection):
    db.execute(
        "CREATE TABLE IF NOT EXISTS company_settings (key TEXT PRIMARY KEY, value TEXT)"
    )


@router.get("", response_model=CompanySettings)
def get_company(db: sqlite3.Connection = Depends(get_db)):
    _ensure_table(db)
    rows = db.execute("SELECT key, value FROM company_settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


@router.put("", response_model=CompanySettings)
def save_company(data: CompanySettings, db: sqlite3.Connection = Depends(get_db)):
    _ensure_table(db)
    for key, value in data.model_dump().items():
        if value is not None:
            db.execute(
                "INSERT INTO company_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
    db.commit()
    rows = db.execute("SELECT key, value FROM company_settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


@router.post("/logo")
async def upload_logo(file: UploadFile = File(...), db: sqlite3.Connection = Depends(get_db)):
    _ensure_table(db)
    ext = Path(file.filename).suffix.lower() or ".png"
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
        "INSERT INTO company_settings (key, value) VALUES ('logo_url', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (logo_url,),
    )
    # Remove old base64 data
    db.execute("DELETE FROM company_settings WHERE key IN ('logo_data', 'logo_filename')")
    db.commit()
    return {"logo_url": logo_url}
