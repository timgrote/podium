"""Lightweight vCard (.vcf) parser.

Handles the common vCard 2.1/3.0/4.0 cases we see from phones and address
books: line folding, property parameters, and quoted-printable values. Not a
full RFC 6350 implementation — just enough to pull name/email/phone/role/org/
note out of contact cards.
"""

import quopri


def _unfold(text: str) -> list[str]:
    """Join folded lines (continuation lines begin with a space or tab)."""
    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines: list[str] = []
    for line in raw_lines:
        if line[:1] in (" ", "\t") and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def _split_property(line: str) -> tuple[str, dict[str, str], str] | None:
    """Split a vCard line into (name, params, value)."""
    if ":" not in line:
        return None
    head, value = line.split(":", 1)
    parts = head.split(";")
    name = parts[0].split(".")[-1].upper()  # drop group prefix like "item1.EMAIL"
    params: dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.upper()] = v.upper()
        else:
            params[p.upper()] = ""
    return name, params, value


def _decode(value: str, params: dict[str, str]) -> str:
    if params.get("ENCODING") in ("QUOTED-PRINTABLE", "QUOTED_PRINTABLE"):
        try:
            value = quopri.decodestring(value.encode("utf-8")).decode("utf-8", "replace")
        except Exception:
            pass
    return value.strip()


def _name_from_n(value: str) -> str:
    # N is structured: Family;Given;Additional;Prefix;Suffix
    fields = [f.strip() for f in value.split(";")]
    given = fields[1] if len(fields) > 1 else ""
    family = fields[0] if fields else ""
    return " ".join(p for p in (given, family) if p).strip()


def _format_adr(value: str) -> str:
    # ADR is structured: PO Box;Extended;Street;City;Region;Postal;Country
    fields = [f.strip() for f in value.split(";")]
    fields += [""] * (7 - len(fields))
    pobox, ext, street, city, region, postal, country = fields[:7]
    street_full = " ".join(p for p in (pobox, ext, street) if p)
    locality = ", ".join(p for p in (city, region) if p)
    if postal:
        locality = f"{locality} {postal}".strip()
    return ", ".join(p for p in (street_full, locality, country) if p)


def parse_vcards(text: str) -> list[dict]:
    """Parse VCF text into a list of contact dicts.

    Each dict has: name, email, phone, role, notes, org (any may be None/empty).
    """
    contacts: list[dict] = []
    current: dict | None = None
    fn = n = ""

    for line in _unfold(text):
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        if upper.startswith("BEGIN:VCARD"):
            current = {"email": None, "phone": None, "role": None, "notes": None, "org": None, "address": None}
            fn = n = ""
            continue
        if upper.startswith("END:VCARD"):
            if current is not None:
                current["name"] = fn or n or current.get("email") or "Unknown"
                contacts.append(current)
            current = None
            continue
        if current is None:
            continue

        parsed = _split_property(stripped)
        if not parsed:
            continue
        name, params, raw = parsed
        value = _decode(raw, params)

        if name == "FN":
            fn = value
        elif name == "N" and not fn:
            n = _name_from_n(value)
        elif name == "EMAIL" and not current["email"] and value:
            current["email"] = value
        elif name == "TEL" and not current["phone"] and value:
            current["phone"] = value
        elif name == "TITLE" and not current["role"] and value:
            current["role"] = value
        elif name == "ORG" and not current["org"] and value:
            current["org"] = value.split(";")[0].strip()
        elif name == "ADR" and not current["address"] and value:
            current["address"] = _format_adr(value)
        elif name == "NOTE" and not current["notes"] and value:
            current["notes"] = value

    return contacts
