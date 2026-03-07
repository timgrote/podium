"""Generate proposal Google Docs by copying a template and replacing placeholders."""

import logging
import re

from google.auth.transport.requests import AuthorizedSession

from .config import settings
from .engineers import ENGINEERS, RATES
from .google_sheets import get_drive_service, get_docs_service, _get_credentials

logger = logging.getLogger(__name__)


def generate_proposal_doc(
    *,
    project_name: str,
    client_name: str,
    client_company: str = "",
    client_address: str = "",
    client_city: str = "",
    client_state: str = "",
    client_zip: str = "",
    engineer_key: str = "tim",
    contact_method: str = "conversation",
    proposal_date: str = "",
    tasks: list[dict],
    additional_exclusions: list[str] | None = None,
    template_id: str = "",
    folder_id: str = "",
) -> str:
    """Copy the proposal template and fill in placeholders.

    Uses Google Drive to copy the template doc, then Google Docs API
    replaceAllText to fill in each {placeholder}.

    Args:
        tasks: list of dicts with keys: name, description (optional), amount
    Returns:
        URL of the new Google Doc
    """
    drive = get_drive_service()
    docs = get_docs_service()

    src_template = template_id or settings.proposal_template_id
    dest_folder = folder_id or settings.proposal_drive_folder_id

    # 1. Copy the template
    doc_name = f"{project_name} Irrigation Design Proposal"
    copy_metadata = {"name": doc_name}
    if dest_folder:
        copy_metadata["parents"] = [dest_folder]

    copied = drive.files().copy(
        fileId=src_template,
        body=copy_metadata,
        supportsAllDrives=True,
    ).execute()
    doc_id = copied["id"]

    # 2. Build replacement map
    engineer = ENGINEERS.get(engineer_key, ENGINEERS["tim"])

    name_parts = client_name.strip().split(None, 1)
    client_first = name_parts[0] if name_parts else client_name

    # City/state/zip line
    city_state_zip_parts = []
    if client_city:
        city_state_zip_parts.append(client_city)
    if client_state:
        if city_state_zip_parts:
            city_state_zip_parts[-1] += ","
        city_state_zip_parts.append(client_state)
    if client_zip:
        city_state_zip_parts.append(client_zip)
    city_state_zip = " ".join(city_state_zip_parts)

    # Task sections text (for Exhibit A scope)
    task_sections_parts = []
    for i, task in enumerate(tasks, 1):
        section = f"Task {i}: {task['name']}"
        if task.get("description"):
            section += f"\n{task['description']}"
        task_sections_parts.append(section)
    task_sections = "\n\n".join(task_sections_parts)

    total_fee = sum(t["amount"] for t in tasks)

    # Additional exclusions
    excl_text = ""
    if additional_exclusions:
        excl_text = "\n".join(f"- {item}" for item in additional_exclusions)

    replacements = {
        "{project_name}": project_name,
        "{proposal_date}": proposal_date or "",
        "{client_name}": client_name,
        "{client_first_name}": client_first,
        "{client_company}": client_company or "",
        "{client_address}": client_address or "",
        "{client_city_state_zip}": city_state_zip,
        "{engineer_name}": engineer["name"],
        "{engineer_title}": engineer["title"],
        "{engineer_phone}": engineer.get("phone", ""),
        "{contact_method}": contact_method or "conversation",
        "{task_sections}": task_sections,
        "{fee_table_rows}": "",
        "{total_fee}": f"${total_fee:,.0f}",
        "{pe_rate}": str(RATES["pe"]["rate"]),
        "{tech_rate}": str(RATES["technician"]["rate"]),
        "{designer_rate}": str(RATES["designer"]["rate"]),
        "{additional_exclusions}": excl_text,
    }

    # 3. Build batchUpdate requests
    requests = []
    for placeholder, value in replacements.items():
        requests.append({
            "replaceAllText": {
                "containsText": {
                    "text": placeholder,
                    "matchCase": True,
                },
                "replaceText": value,
            }
        })

    docs.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()

    # 4. Format task sub-items with indentation and auto-numbering
    _format_task_sections(docs, doc_id, tasks)

    # 5. Populate fee table with proper column placement
    _populate_fee_table(docs, doc_id, tasks)

    # 6. Replace signature placeholder image
    sig_file_id = engineer.get("signature_file_id")
    if sig_file_id:
        _replace_signature_image(docs, drive, doc_id, sig_file_id)

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    logger.info("Created proposal doc '%s': %s", doc_name, doc_url)
    return doc_url


def _format_task_sections(docs_service, doc_id: str, tasks: list[dict]):
    """Apply indentation to task sub-items in Exhibit A."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body_content = doc.get("body", {}).get("content", [])

    in_task_section = False
    sub_item_ranges = []

    for block in body_content:
        if "paragraph" not in block:
            continue
        text = ""
        for elem in block["paragraph"].get("elements", []):
            text += elem.get("textRun", {}).get("content", "")
        text_stripped = text.strip()

        if re.match(r"^Task \d+:", text_stripped):
            in_task_section = True
            continue

        if in_task_section and text_stripped:
            start = block["paragraph"]["elements"][0]["startIndex"]
            end = block["paragraph"]["elements"][-1]["endIndex"]
            sub_item_ranges.append((start, end))
        elif in_task_section and not text_stripped:
            in_task_section = False

    if not sub_item_ranges:
        return

    style_requests = []
    for start, end in sub_item_ranges:
        style_requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {
                    "indentStart": {"magnitude": 36, "unit": "PT"},
                    "indentFirstLine": {"magnitude": 36, "unit": "PT"},
                },
                "fields": "indentStart,indentFirstLine",
            }
        })

    if style_requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": style_requests},
        ).execute()

    logger.info("Formatted %d task sub-items in doc %s", len(sub_item_ranges), doc_id)


def _populate_fee_table(docs_service, doc_id: str, tasks: list[dict]):
    """Populate the fee schedule table using Docs API table manipulation.

    Finds the table containing "Total:", deletes the placeholder row,
    inserts one row per task, and populates cells with proper column placement.
    """
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body_content = doc.get("body", {}).get("content", [])

    # Find the fee table (contains a cell with "Total:")
    fee_table = None
    total_row_idx = None
    for block in body_content:
        table = block.get("table")
        if not table:
            continue
        for row_idx, row in enumerate(table.get("tableRows", [])):
            for cell in row.get("tableCells", []):
                for para in cell.get("content", []):
                    for elem in para.get("paragraph", {}).get("elements", []):
                        text = elem.get("textRun", {}).get("content", "")
                        if "Total:" in text:
                            fee_table = block
                            total_row_idx = row_idx
                            break

    if not fee_table or total_row_idx is None:
        logger.warning("Could not find fee table with 'Total:' row in doc %s", doc_id)
        return

    # The placeholder row is the one just before Total
    placeholder_row_idx = total_row_idx - 1
    if placeholder_row_idx < 1:  # row 0 is the header
        logger.warning("No placeholder row found before Total row in fee table")
        return

    # Step 1: Delete the placeholder row
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [
            {"deleteTableRow": {
                "tableCellLocation": {
                    "tableStartLocation": {"index": fee_table["startIndex"]},
                    "rowIndex": placeholder_row_idx,
                    "columnIndex": 0,
                },
            }},
        ]},
    ).execute()

    # Step 2: Re-read doc, insert N rows above Total
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body_content = doc.get("body", {}).get("content", [])

    # Re-find the table and Total row
    for block in body_content:
        table = block.get("table")
        if not table:
            continue
        for row_idx, row in enumerate(table.get("tableRows", [])):
            for cell in row.get("tableCells", []):
                for para in cell.get("content", []):
                    for elem in para.get("paragraph", {}).get("elements", []):
                        text = elem.get("textRun", {}).get("content", "")
                        if "Total:" in text:
                            fee_table = block
                            total_row_idx = row_idx
                            break

    total_row = fee_table["table"]["tableRows"][total_row_idx]

    # Insert rows one at a time, each above the Total row
    for _ in tasks:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [
                {"insertTableRow": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": fee_table["startIndex"]},
                        "rowIndex": total_row_idx,
                        "columnIndex": 0,
                    },
                    "insertBelow": False,
                }},
            ]},
        ).execute()

        # Re-read to get updated indices
        doc = docs_service.documents().get(documentId=doc_id).execute()
        body_content = doc.get("body", {}).get("content", [])
        for block in body_content:
            table = block.get("table")
            if not table:
                continue
            for ri, row in enumerate(table.get("tableRows", [])):
                for cell in row.get("tableCells", []):
                    for para in cell.get("content", []):
                        for elem in para.get("paragraph", {}).get("elements", []):
                            text = elem.get("textRun", {}).get("content", "")
                            if "Total:" in text:
                                fee_table = block
                                total_row_idx = ri
                                total_row = row
                                break

    # Step 3: Re-read doc and populate cells
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body_content = doc.get("body", {}).get("content", [])

    # Find fee table one more time
    for block in body_content:
        table = block.get("table")
        if not table:
            continue
        for ri, row in enumerate(table.get("tableRows", [])):
            for cell in row.get("tableCells", []):
                for para in cell.get("content", []):
                    for elem in para.get("paragraph", {}).get("elements", []):
                        text = elem.get("textRun", {}).get("content", "")
                        if "Total:" in text:
                            fee_table = block
                            total_row_idx = ri
                            break

    table_obj = fee_table["table"]
    table_rows = table_obj["tableRows"]

    # The task rows are between header (row 0) and Total row
    # They were inserted in order, so row 1 = first task, row 2 = second task, etc.
    insert_requests = []

    for i, task in enumerate(tasks):
        row_idx = 1 + i  # row 0 is header
        if row_idx >= total_row_idx:
            break
        row = table_rows[row_idx]

        # Column 0: task name
        cell_0 = row["tableCells"][0]
        para_0 = cell_0["content"][0]
        idx_0 = para_0["paragraph"]["elements"][0]["startIndex"]
        insert_requests.append({
            "insertText": {
                "location": {"index": idx_0},
                "text": task["name"],
            }
        })

        # Column 1: fee amount
        cell_1 = row["tableCells"][1]
        para_1 = cell_1["content"][0]
        idx_1 = para_1["paragraph"]["elements"][0]["startIndex"]
        fee_text = f"${task['amount']:,.0f}"
        insert_requests.append({
            "insertText": {
                "location": {"index": idx_1},
                "text": fee_text,
            }
        })

    # Execute text inserts in one batch
    # Important: process inserts in reverse index order to avoid index shifting
    insert_requests.sort(key=lambda r: r["insertText"]["location"]["index"], reverse=True)

    if insert_requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": insert_requests},
        ).execute()

    # Step 4: Remove bold from task rows (inherited from template)
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body_content = doc.get("body", {}).get("content", [])
    for block in body_content:
        table = block.get("table")
        if not table:
            continue
        for ri, row in enumerate(table.get("tableRows", [])):
            for cell in row.get("tableCells", []):
                for para in cell.get("content", []):
                    for elem in para.get("paragraph", {}).get("elements", []):
                        text = elem.get("textRun", {}).get("content", "")
                        if "Total:" in text:
                            fee_table = block
                            total_row_idx = ri
                            break

    table_rows = fee_table["table"]["tableRows"]
    style_requests = []
    for i in range(len(tasks)):
        row_idx = 1 + i
        if row_idx >= total_row_idx:
            break
        row = table_rows[row_idx]
        for cell in row["tableCells"]:
            para = cell["content"][0]
            start = para["paragraph"]["elements"][0]["startIndex"]
            end = para["paragraph"]["elements"][-1]["endIndex"]
            style_requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "textStyle": {"bold": False},
                    "fields": "bold",
                }
            })

    if style_requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": style_requests},
        ).execute()

    logger.info("Populated fee table with %d task rows in doc %s", len(tasks), doc_id)


def _replace_signature_image(docs_service, drive_service, doc_id: str, signature_file_id: str):
    """Find the placeholder signature image, delete it, and insert the real one at correct size."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    inline_objects = doc.get("inlineObjects", {})
    body_content = doc.get("body", {}).get("content", [])

    # Walk the doc to find the signature placeholder image and its position
    target_id = None
    img_index = None
    last_id = None
    last_index = None

    for block in body_content:
        if "paragraph" not in block:
            continue
        for elem in block["paragraph"].get("elements", []):
            io_elem = elem.get("inlineObjectElement")
            if not io_elem:
                continue
            obj_id = io_elem.get("inlineObjectId")
            if not obj_id or obj_id not in inline_objects:
                continue

            obj = inline_objects[obj_id]
            props = obj.get("inlineObjectProperties", {}).get("embeddedObject", {})
            title = (props.get("title") or "").lower()
            description = (props.get("description") or "").lower()

            # Track last image as fallback
            last_id, last_index = obj_id, elem["startIndex"]

            if "signature" in title or "signature" in description:
                target_id = obj_id
                img_index = elem["startIndex"]
                break
        if target_id:
            break

    # Fall back to last image
    if not target_id:
        target_id = last_id
        img_index = last_index

    if not target_id or img_index is None:
        logger.warning("No inline image found in doc to replace with signature")
        return

    # Get placeholder height
    placeholder = inline_objects[target_id]["inlineObjectProperties"]["embeddedObject"]
    ph_height = placeholder.get("size", {}).get("height", {}).get("magnitude", 25)

    # Get signature aspect ratio to calculate width
    try:
        img_meta = drive_service.files().get(
            fileId=signature_file_id, fields="imageMediaMetadata", supportsAllDrives=True,
        ).execute()
        im = img_meta.get("imageMediaMetadata", {})
        height = im.get("height", 0)
        if not height:
            logger.warning("Signature image %s has zero height; skipping", signature_file_id)
            return
        aspect = im.get("width", 1) / height
    except Exception as e:
        logger.warning("Could not read signature image metadata for %s: %s", signature_file_id, e)
        return

    new_width = ph_height * aspect
    sig_uri = f"https://drive.google.com/uc?id={signature_file_id}&export=download"

    try:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [
                {"deleteContentRange": {"range": {"startIndex": img_index, "endIndex": img_index + 1}}},
                {"insertInlineImage": {
                    "uri": sig_uri,
                    "location": {"index": img_index},
                    "objectSize": {
                        "height": {"magnitude": ph_height, "unit": "PT"},
                        "width": {"magnitude": new_width, "unit": "PT"},
                    },
                }},
            ]},
        ).execute()
        logger.info("Inserted signature (%.0f x %.0f PT) in doc %s", new_width, ph_height, doc_id)
    except Exception as e:
        logger.warning("Failed to replace signature image: %s", e)




def export_google_doc_as_pdf(doc_id: str) -> bytes:
    """Export a Google Doc as PDF bytes."""
    creds = _get_credentials()
    session = AuthorizedSession(creds)
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"
    response = session.get(url)
    if response.status_code != 200:
        body_preview = response.text[:200] if response.text else "(empty)"
        logger.error("PDF export failed for doc %s: status=%d body=%s", doc_id, response.status_code, body_preview)
        raise RuntimeError(f"PDF export failed for document {doc_id} with status {response.status_code}")
    return response.content
