import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: str = os.path.join(os.path.dirname(__file__), "..", "db", "podium.db")
    host: str = "0.0.0.0"
    port: int = 8000
    upload_dir: str = os.path.join(os.path.dirname(__file__), "..", "uploads")

    # Google API settings
    google_service_account_path: str = os.path.join(
        os.path.dirname(__file__), "..", "credentials", "google-service-account.json"
    )
    invoice_template_id: str = "16QHE3DdF0AAQtLgXUZSx8c9T2q3dvTvKwjb90B5yGcI"
    invoice_drive_folder_id: str = ""

    model_config = {"env_prefix": "PODIUM_"}


settings = Settings()
