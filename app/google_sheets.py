"""Google Sheets/Drive/Gmail integration for invoice creation and delivery."""

import base64
import json
import logging
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from io import BytesIO

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from .config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
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
        "No Google credentials configured. Set CONDUCTOR_GOOGLE_SERVICE_ACCOUNT_JSON "
        "(base64) or CONDUCTOR_GOOGLE_SERVICE_ACCOUNT_PATH (file path)."
    )


def get_drive_service():
    return build("drive", "v3", credentials=_get_credentials(), cache_discovery=False)


def get_sheets_service():
    return build("sheets", "v4", credentials=_get_credentials(), cache_discovery=False)


def get_docs_service():
    return build("docs", "v1", credentials=_get_credentials(), cache_discovery=False)


def get_gmail_service():
    return build("gmail", "v1", credentials=_get_credentials(), cache_discovery=False)


def _find_or_create_folder(drive, name: str, parent_id: str) -> str:
    """Find a subfolder by name under parent_id, or create it. Returns folder ID."""
    escaped_name = name.replace("\\", "\\\\").replace("'", "\\'")
    query = (
        f"name = '{escaped_name}' and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed = false"
    )
    results = drive.files().list(
        q=query, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = drive.files().create(body=metadata, fields="id", supportsAllDrives=True).execute()
    logger.info("Created Drive folder '%s' under %s -> %s", name, parent_id, folder["id"])
    return folder["id"]


def resolve_project_folder(drive, root_folder_id: str, data_path: str) -> str:
    """Walk a slash-separated data_path (e.g. 'DR Horton/Silver Peaks') creating folders as needed.
    Returns the final folder ID."""
    if not data_path or not root_folder_id:
        return root_folder_id
    current = root_folder_id
    for part in data_path.strip("/").split("/"):
        part = part.strip()
        if part:
            current = _find_or_create_folder(drive, part, current)
    return current


def _col_letter(col_index: int) -> str:
    """Convert 0-based column index to sheet letter (0=A, 1=B, ..., 25=Z)."""
    return chr(ord("A") + col_index)


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
    project_data_path: str = "",
) -> str:
    """Copy the invoice template and populate it via token replacement.

    Template tokens (found by scanning all cells):
      Header:  [ProjectName], [InvoiceDate], [InvoiceID], etc.
      Tasks:   {{task_name}}, {{task_fee}}, {{task_percent}}, {{task_previous}}, {{task_amount}}
      Totals:  [TotalFee], [TotalPrevious], [TotalAmount], [InvoiceTotal]

    Returns:
        URL of the new Google Sheet
    """
    drive = get_drive_service()
    sheets = get_sheets_service()

    # 1. Copy the template
    src_template = template_id or settings.invoice_template_id
    dest_folder = folder_id or settings.invoice_drive_folder_id

    if project_data_path and dest_folder:
        dest_folder = resolve_project_folder(drive, dest_folder, project_data_path)

    copy_metadata = {"name": f"Invoice {invoice_number}"}
    if dest_folder:
        copy_metadata["parents"] = [dest_folder]

    copied = drive.files().copy(
        fileId=src_template,
        body=copy_metadata,
        supportsAllDrives=True,
    ).execute()
    spreadsheet_id = copied["id"]

    # 2. Get sheet ID and read all cells
    sheet_meta = sheets.spreadsheets().get(
        spreadsheetId=spreadsheet_id, fields="sheets.properties"
    ).execute()
    sheet_id = sheet_meta["sheets"][0]["properties"]["sheetId"]
    sheet_title = sheet_meta["sheets"][0]["properties"]["title"]

    all_data = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_title}!A1:H50",
        valueRenderOption="FORMATTED_VALUE",
    ).execute()
    grid = all_data.get("values", [])

    # 3. Find the task marker row (contains {{task_name}})
    marker_row = None
    for r, row in enumerate(grid):
        for cell in row:
            if "{{task_name}}" in str(cell):
                marker_row = r
                break
        if marker_row is not None:
            break

    # 4. Insert extra rows for tasks (duplicate marker row formatting)
    num_tasks = len(tasks) if tasks else 0
    rows_to_insert = max(num_tasks - 1, 0)

    if rows_to_insert > 0 and marker_row is not None:
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{
                "insertDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": marker_row + 1,
                        "endIndex": marker_row + 1 + rows_to_insert,
                    },
                    "inheritFromBefore": True,
                }
            }]},
        ).execute()

    # 5. Build token map for header and total replacements
    # Parse address into street + city/state/zip
    addr_line1, addr_line2 = "", ""
    if client_address:
        parts = [l.strip() for l in client_address.replace("\r\n", "\n").split("\n") if l.strip()]
        addr_line1 = parts[0] if len(parts) > 0 else ""
        addr_line2 = parts[1] if len(parts) > 1 else ""

    # Compute totals from task data
    total_fee = sum(float(t.get("unit_price", 0)) for t in tasks) if tasks else 0
    total_previous = sum(float(t.get("previous_billing", 0)) for t in tasks) if tasks else 0
    total_amount = sum(float(t.get("amount", 0)) for t in tasks) if tasks else 0

    token_map = {
        "[ProjectName]": project_name,
        "[ProjectJobCode]": project_id,
        "[InvoiceDate]": invoice_date,
        "[InvoiceID]": invoice_number,
        "[TIE-PM-Email]": company_email,
        "[Client Company]": client_company or client_name,
        "[Client Contact]": client_contact,
        "[Client Address]": addr_line1,
        "[City, State ZIP]": addr_line2,
        "[Client Project #]": client_project_number,
        "[Date]": invoice_date,
        "[TotalFee]": total_fee,
        "[TotalPrevious]": total_previous,
        "[TotalAmount]": total_amount,
        "[InvoiceTotal]": total_amount,
    }

    # 6. Re-read the grid after row insertion
    all_data = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_title}!A1:H{50 + rows_to_insert}",
        valueRenderOption="FORMATTED_VALUE",
    ).execute()
    grid = all_data.get("values", [])

    # Pad rows/cols so we can index safely
    max_cols = 8  # A-H
    for row in grid:
        while len(row) < max_cols:
            row.append("")

    # Tokens whose replacements are text (need left-align to prevent right-align)
    text_tokens = {
        "[ProjectName]", "[ProjectJobCode]", "[InvoiceDate]", "[InvoiceID]",
        "[TIE-PM-Email]", "[Client Company]", "[Client Contact]",
        "[Client Address]", "[City, State ZIP]", "[Client Project #]", "[Date]",
    }

    # 7. Scan and replace all [bracket] tokens; track cells for left-alignment
    updates = []  # list of {"range": "A1", "values": [[val]]}
    header_token_cells = []  # (row, col) of text cells that need left-align

    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            cell_str = str(cell)
            new_val = cell_str
            is_text_token = False

            # Replace [bracket] tokens (may appear as substring, e.g. "Rendered Through: [Date]")
            for token, value in token_map.items():
                if token in new_val:
                    new_val = new_val.replace(token, str(value))
                    if token in text_tokens:
                        is_text_token = True

            if new_val != cell_str:
                col_letter = _col_letter(c)
                cell_ref = f"{col_letter}{r + 1}"
                updates.append({"range": cell_ref, "values": [[new_val]]})
                if is_text_token:
                    header_token_cells.append((r, c))

    # 7b. Write task rows directly (inserted rows are blank — write positionally)
    if marker_row is not None and num_tasks > 0:
        for i, task in enumerate(tasks):
            row_num = marker_row + i + 1  # 1-based sheet row
            percent_val = task.get("quantity", 0)
            decimal_pct = percent_val / 100 if percent_val > 1 else percent_val
            updates.append({"range": f"A{row_num}", "values": [[task.get("name", "")]]})
            updates.append({"range": f"C{row_num}", "values": [[task.get("unit_price", 0)]]})
            updates.append({"range": f"D{row_num}", "values": [[decimal_pct]]})
            updates.append({"range": f"E{row_num}", "values": [[task.get("previous_billing", 0)]]})
            updates.append({"range": f"F{row_num}", "values": [[task.get("amount", 0)]]})
        # Clear the original marker row token text if no tasks replaced it
        # (handled above since task 0 writes to marker_row)

    # 8. Write all replacements
    if updates:
        sheets.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": updates},
        ).execute()

    # 9. Left-align cells that had header tokens (prevent date/number right-alignment)
    if header_token_cells:
        align_requests = []
        for row_idx, col_idx in header_token_cells:
            align_requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_idx,
                        "endRowIndex": row_idx + 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1,
                    },
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
                    "fields": "userEnteredFormat.horizontalAlignment",
                }
            })
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": align_requests},
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
    """Export a Google Sheet as PDF bytes (gridlines hidden)."""
    creds = _get_credentials()
    session = AuthorizedSession(creds)
    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export"
        f"?format=pdf&gridlines=false"
    )
    response = session.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"PDF export failed with status {response.status_code}")
    return response.content


def upload_pdf_to_drive(pdf_bytes: bytes, filename: str, folder_id: str = "", project_data_path: str = "") -> str:
    """Upload PDF bytes to Google Drive. Returns the Drive file URL."""
    drive = get_drive_service()
    dest_folder = folder_id or settings.invoice_drive_folder_id

    if project_data_path and dest_folder:
        dest_folder = resolve_project_folder(drive, dest_folder, project_data_path)

    file_metadata = {"name": filename, "mimeType": "application/pdf"}
    if dest_folder:
        file_metadata["parents"] = [dest_folder]

    media = MediaIoBaseUpload(BytesIO(pdf_bytes), mimetype="application/pdf")
    uploaded = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True,
    ).execute()

    return uploaded.get("webViewLink", f"https://drive.google.com/file/d/{uploaded['id']}/view")


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
