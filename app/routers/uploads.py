import logging
from pathlib import Path, PurePath

from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.status import HTTP_201_CREATED

from ..utils import generate_id

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB

root = Path(__file__).resolve().parent.parent.parent

router = APIRouter()


@router.post("/images", status_code=HTTP_201_CREATED)
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Invalid image type: {file.content_type}")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f"File too large ({len(content)} bytes). Max 5MB.")

    safe_name = PurePath(file.filename or "image.png").name
    ext = Path(safe_name).suffix.lower() or ".png"
    filename = f"{generate_id('img-')}{ext}"

    dest = root / "uploads" / "images" / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    return {"url": f"/uploads/images/{filename}"}
