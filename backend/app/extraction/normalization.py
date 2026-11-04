import re
from datetime import date, datetime, timezone

from app.schemas.extraction import FieldName


def normalize(field: FieldName, raw: str) -> tuple[str | None, str | None]:
    value = " ".join(raw.split())
    if not value:
        return None, "Empty value"
    if field == "date_of_birth":
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError
            parsed = date.fromisoformat(value)
            if parsed > datetime.now(timezone.utc).date():
                raise ValueError
            return parsed.isoformat(), None
        except ValueError:
            return None, "Expected a valid, non-future ISO date"
    if field == "requested_specialty":
        if value.casefold() in {"cardiology", "cardiology consultation"}:
            return "cardiology", None
        return None, "Unsupported specialty"
    return value, None


def normalize_claim(field: FieldName, raw: str, proposed: str | None):
    """Dates gain explicit formats; ordinary text cannot be rewritten by the model."""
    value, issue = normalize(field, raw)
    if field != "date_of_birth":
        return value, issue
    if value is not None:
        return value, None
    compact = " ".join(raw.split())
    # Numeric month/day formats are accepted only when day > 12 removes ambiguity.
    numeric = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", compact)
    formats = ["%B %d, %Y", "%b %d, %Y"]
    if numeric and int(numeric[2]) > 12:
        formats.append("%m/%d/%Y")
    for fmt in formats:
        try:
            canonical = datetime.strptime(compact, fmt).date().isoformat()
        except ValueError:
            continue
        value, issue = normalize(field, canonical)
        if value is not None and proposed == value:
            return value, None
    return None, issue or "Unsupported or ambiguous date"
