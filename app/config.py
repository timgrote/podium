import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://conductor:conductor@localhost:5432/conductor"
    host: str = "0.0.0.0"
    port: int = 3000
    upload_dir: str = os.path.join(os.path.dirname(__file__), "..", "uploads")

    # Google API settings
    # Option 1: base64-encoded JSON (for production / env vars)
    google_service_account_json: str = ""
    # Option 2: path to JSON file (for local dev)
    google_service_account_path: str = ""
    invoice_template_id: str = "16QHE3DdF0AAQtLgXUZSx8c9T2q3dvTvKwjb90B5yGcI"
    invoice_drive_folder_id: str = ""

    # Loki (Raindrop activity logs)
    loki_url: str = "https://logging.raindropirrigationsoftware.com"
    loki_api_key: str = ""

    # KeyGen (Raindrop trial licenses)
    keygen_api_token: str = ""
    keygen_account_id: str = "40280a53-8cd5-4b54-9813-04727b10810f"
    keygen_trial_policy_id: str = "42090eb8-6372-40b3-b6b9-fe5e6e6e058b"
    keygen_yearly_policy_id: str = "04745663-d270-44e0-a281-478bd6dae04e"

    # Proposal settings
    proposal_template_id: str = "1PnVd8O3VgQKDLx8YpqY30U-JvXMdEleASRC87qPxZf4"
    proposal_drive_folder_id: str = "1no2lFCwH3xzPgNc5cG5Gei1GrO47-R8H"

    model_config = {"env_prefix": "CONDUCTOR_", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
