"""Google Sheets/Drive/Gmail integration for invoice creation and delivery."""

import base64
import json
import logging
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

from .config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
]

_credentials = None


def _get_credentials():
    global _credentials
    if _credentials and _credentials.valid:
        return _credentials
    if _credentials and _credentials.expired:
        _credentials.refresh(Request())
        return _credentials

    # Option 1: base64-encoded JSON string (production)
    if settings.google_service_account_json:
        info = json.loads(base64.b64decode(settings.google_service_account_json))
        _credentials = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
        return _credentials

    # Option 2: file path (local dev)
    path = settings.google_service_account_path
    if path and os.path.exists(path):
        _credentials = service_account.Credentials.from_service_account_file(
            path, scopes=SCOPES
        )
        return _credentials

    raise FileNotFoundError(
        "No Google credentials configured. Set PODIUM_GOOGLE_SERVICE_ACCOUNT_JSON "
        "(base64) or PODIUM_GOOGLE_SERVICE_ACCOUNT_PATH (file path)."
    )


def get_drive_service():
    return build("drive", "v3", credentials=_get_credentials(), cache_discovery=False)


def get_sheets_service():
    return build("sheets", "v4", credentials=_get_credentials(), cache_discovery=False)


def get_gmail_service():
    return build("gmail", "v1", credentials=_get_credentials(), cache_discovery=False)


def create_invoice_sheet(
    invoice_number: str,
    project_name: str,
    project_id: str,
    invoice_date: str,
    company_email: str,
    client_name: str,
    tasks: list[dict],
    folder_id: str = "",
) -> str:
    """Copy the invoice template and populate it with invoice data.

    Args:
        invoice_number: e.g. "JBHL21-1"
        project_name: Project display name
        project_id: Job ID
        invoice_date: ISO date string
        company_email: Sender's email
        client_name: Client/company name
        tasks: List of dicts with keys: name, unit_price, quantity, previous_billing, amount
        folder_id: Google Drive folder ID (overrides config default)

    Returns:
        URL of the new Google Sheet
    """
    drive = get_drive_service()
    sheets = get_sheets_service()

    # 1. Copy the template
    dest_folder = folder_id or settings.invoice_drive_folder_id
    copy_metadata = {"name": f"Invoice {invoice_number}"}
    if dest_folder:
        copy_metadata["parents"] = [dest_folder]

    copied = drive.files().copy(
        fileId=settings.invoice_template_id,
        body=copy_metadata,
    ).execute()
    spreadsheet_id = copied["id"]

    # 2. Write project info to header cells
    # B6: Project Name, B7: Job ID, B8: Invoice Date, B9: Invoice Number, B10: Company Email
    # F7: Client Name
    header_data = [
        {"range": "B6", "values": [[project_name]]},
        {"range": "B7", "values": [[project_id]]},
        {"range": "B8", "values": [[invoice_date]]},
        {"range": "B9", "values": [[invoice_number]]},
        {"range": "B10", "values": [[company_email]]},
        {"range": "F7", "values": [[client_name]]},
    ]

    # 3. Write task rows to A15:F24
    task_rows = []
    for task in tasks[:10]:  # Max 10 task rows
        task_rows.append([
            task.get("name", ""),
            task.get("unit_price", 0),
            task.get("quantity", 0),
            task.get("previous_billing", 0),
            task.get("amount", 0),
        ])

    if task_rows:
        end_row = 14 + len(task_rows)
        header_data.append({
            "range": f"A15:E{end_row}",
            "values": task_rows,
        })

    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "valueInputOption": "USER_ENTERED",
            "data": header_data,
        },
    ).execute()

    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    logger.info("Created invoice sheet %s: %s", invoice_number, sheet_url)
    return sheet_url


def export_sheet_as_pdf(spreadsheet_id: str) -> bytes:
    """Export a Google Sheet as PDF bytes."""
    drive = get_drive_service()
    pdf_bytes = drive.files().export(
        fileId=spreadsheet_id,
        mimeType="application/pdf",
    ).execute()
    return pdf_bytes


def send_invoice_email(
    to_emails: list[str],
    subject: str,
    body_text: str,
    pdf_bytes: bytes,
    pdf_filename: str,
    from_email: str | None = None,
) -> dict:
    """Send an email with PDF attachment via Gmail API.

    Note: The service account must have domain-wide delegation configured,
    or use a delegated user (from_email) to send on behalf of.
    """
    gmail = get_gmail_service()

    msg = MIMEMultipart()
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    if from_email:
        msg["From"] = from_email

    msg.attach(MIMEText(body_text, "plain"))

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=pdf_filename)
    msg.attach(attachment)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    user_id = from_email or "me"
    result = gmail.users().messages().send(
        userId=user_id,
        body={"raw": raw},
    ).execute()

    logger.info("Sent invoice email to %s, message ID: %s", to_emails, result.get("id"))
    return result
