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
