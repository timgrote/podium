from pydantic import BaseModel


class CompanySettings(BaseModel):
    company_name: str | None = None
    company_email: str | None = None
    company_phone: str | None = None
    company_address: str | None = None
    tagline: str | None = None
    primary_color: str | None = None
    logo_url: str | None = None
    logo_data: str | None = None
    logo_filename: str | None = None
    invoice_template_id: str | None = None
    invoice_drive_folder_id: str | None = None
    proposal_template_id: str | None = None
    proposal_drive_folder_id: str | None = None
