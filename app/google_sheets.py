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
    template_id: str = "",
    client_contact: str = "",
    client_company: str = "",
    client_address: str = "",
    client_project_number: str = "",
) -> str:
    """Copy the invoice template and populate it with invoice data.

    Returns:
        URL of the new Google Sheet
    """
    drive = get_drive_service()
    sheets = get_sheets_service()

    # 1. Copy the template
    src_template = template_id or settings.invoice_template_id
    dest_folder = folder_id or settings.invoice_drive_folder_id
    copy_metadata = {"name": f"Invoice {invoice_number}"}
    if dest_folder:
        copy_metadata["parents"] = [dest_folder]

    copied = drive.files().copy(
        fileId=src_template,
        body=copy_metadata,
        supportsAllDrives=True,
    ).execute()
    spreadsheet_id = copied["id"]

    # 2. Write project info to header cells
    # Left side: B6=Project Name, B7=Job ID, B8=Invoice Date, B9=Invoice #, B10=PM Email
    # Right side: F6=Client Contact, F7=Client Company, F8-F9=Address, F10=Client Project #
    # A12: "Professional Services Rendered Through: <date>"

    # Parse address into street + city/state/zip lines
    addr_line1 = ""
    addr_line2 = ""
    if client_address:
        parts = [line.strip() for line in client_address.replace("\r\n", "\n").split("\n") if line.strip()]
        addr_line1 = parts[0] if len(parts) > 0 else ""
        addr_line2 = parts[1] if len(parts) > 1 else ""

    header_data = [
        {"range": "B6", "values": [[project_name]]},
        {"range": "B7", "values": [[project_id]]},
        {"range": "B8", "values": [[invoice_date]]},
        {"range": "B9", "values": [[invoice_number]]},
        {"range": "B10", "values": [[company_email]]},
        # Client info column F
        {"range": "F6", "values": [[client_contact]]},
        {"range": "F7", "values": [[client_company or client_name]]},
        {"range": "F8", "values": [[addr_line1]]},
        {"range": "F9", "values": [[addr_line2]]},
        {"range": "F10", "values": [[client_project_number]]},
        # A12: services rendered date
        {"range": "A12", "values": [[f"Professional Services Rendered Through: {invoice_date}"]]},
    ]

    # 3. Write task rows — A=name, C=fee, D=percent, E=previous_billing
    #    Column B and F are left for sheet formulas (F = calculated amount)
    #    Clear all 10 task rows first (15-24), then write actual data
    max_task_rows = 10
    num_tasks = min(len(tasks), max_task_rows) if tasks else 0

    # Build blank rows to clear template defaults in columns A, C, D, E
    clear_names = [[""] for _ in range(max_task_rows)]
    clear_data = [["", "", ""] for _ in range(max_task_rows)]
    header_data.append({"range": "A15:A24", "values": clear_names})
    header_data.append({"range": "C15:E24", "values": clear_data})

    if num_tasks > 0:
        name_rows = []
        data_rows = []
        for task in tasks[:max_task_rows]:
            name_rows.append([task.get("name", "")])
            percent_val = task.get("quantity", 0)
            # Write percent as decimal (e.g. 10% → 0.10) for sheet formatting
            decimal_val = percent_val / 100 if percent_val > 1 else percent_val
            data_rows.append([
                task.get("unit_price", 0),      # C: task fee
                decimal_val,                     # D: percent complete (as decimal)
                task.get("previous_billing", 0), # E: previous billing
            ])

        end_row = 14 + num_tasks
        header_data.append({
            "range": f"A15:A{end_row}",
            "values": name_rows,
        })
        header_data.append({
            "range": f"C15:E{end_row}",
            "values": data_rows,
        })

    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "valueInputOption": "USER_ENTERED",
            "data": header_data,
        },
    ).execute()

    # Left-align project info cells B6:B10 (dates auto-right-align otherwise)
    # Get the first sheet's ID
    sheet_meta = sheets.spreadsheets().get(
        spreadsheetId=spreadsheet_id, fields="sheets.properties.sheetId"
    ).execute()
    sheet_id = sheet_meta["sheets"][0]["properties"]["sheetId"]

    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [
            # Left-align B6:B10
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 5,
                        "endRowIndex": 10,
                        "startColumnIndex": 1,  # B
                        "endColumnIndex": 2,
                    },
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
                    "fields": "userEnteredFormat.horizontalAlignment",
                }
            },
            # Left-align F6:F10
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 5,
                        "endRowIndex": 10,
                        "startColumnIndex": 5,  # F
                        "endColumnIndex": 6,
                    },
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
                    "fields": "userEnteredFormat.horizontalAlignment",
                }
            },
        ]},
    ).execute()

    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    logger.info("Created invoice sheet %s: %s", invoice_number, sheet_url)
    return sheet_url


def read_invoice_sheet(spreadsheet_id: str) -> list[dict]:
    """Read task rows from an invoice Google Sheet.

    Layout: A=name, C=fee, D=percent, E=previous_billing, F=calculated amount.
    Returns list of dicts with keys: name, unit_price, quantity, previous_billing, amount.
    """
    sheets = get_sheets_service()

    # Read name from column A, and fee/percent/previous/amount from C:F
    result = sheets.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id,
        ranges=["A15:A24", "C15:F24"],
        valueRenderOption="UNFORMATTED_VALUE",
    ).execute()

    ranges = result.get("valueRanges", [])
    names = ranges[0].get("values", []) if len(ranges) > 0 else []
    data = ranges[1].get("values", []) if len(ranges) > 1 else []

    tasks = []
    for i in range(max(len(names), len(data))):
        name = names[i][0] if i < len(names) and names[i] else ""
        if not name:
            continue
        row = data[i] if i < len(data) else []
        # D column stores percent as decimal (0.10 = 10%), convert back to whole number
        raw_percent = row[1] if len(row) > 1 else 0
        quantity = raw_percent * 100 if raw_percent <= 1 else raw_percent
        tasks.append({
            "name": name,
            "unit_price": row[0] if len(row) > 0 else 0,      # C: fee
            "quantity": quantity,                                # D: percent (converted from decimal)
            "previous_billing": row[2] if len(row) > 2 else 0,  # E: previous billing
            "amount": row[3] if len(row) > 3 else 0,            # F: calculated amount
        })

    logger.info("Read %d task rows from sheet %s", len(tasks), spreadsheet_id)
    return tasks


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
