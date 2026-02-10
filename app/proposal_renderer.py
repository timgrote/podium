"""Generate proposal Google Docs by copying a template and replacing placeholders."""

import logging

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
    doc_name = f"{project_name}-Proposal"
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

    # Fee table rows text
    fee_rows = []
    for task in tasks:
        fee_rows.append(f"{task['name']}\t${task['amount']:,.0f}")
    fee_table_rows = "\n".join(fee_rows)

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
        "{fee_table_rows}": fee_table_rows,
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

    # 4. Replace signature placeholder image
    sig_file_id = engineer.get("signature_file_id")
    if sig_file_id:
        _replace_signature_image(docs, drive, doc_id, sig_file_id)

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    logger.info("Created proposal doc '%s': %s", doc_name, doc_url)
    return doc_url


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
