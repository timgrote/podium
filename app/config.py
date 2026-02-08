import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: str = os.path.join(os.path.dirname(__file__), "..", "db", "podium.db")
    host: str = "0.0.0.0"
    port: int = 8000
    upload_dir: str = os.path.join(os.path.dirname(__file__), "..", "uploads")

    # Google API settings
    # Option 1: base64-encoded JSON (for production / env vars)
    google_service_account_json: str = ""
    # Option 2: path to JSON file (for local dev)
    google_service_account_path: str = ""
    invoice_template_id: str = "16QHE3DdF0AAQtLgXUZSx8c9T2q3dvTvKwjb90B5yGcI"
    invoice_drive_folder_id: str = ""

    model_config = {"env_prefix": "PODIUM_"}


settings = Settings()
