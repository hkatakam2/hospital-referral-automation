"""Server-controlled extraction methods; discovery never makes provider requests."""
from pydantic import ValidationError

from app.config import settings
from app.extraction.base import Extractor
from app.extraction.llm import GeminiSettings, LLMExtractor
from app.extraction.rule_based import RuleBasedExtractor
from app.schemas.extraction import ExtractionMethod, ExtractorChoice


class ExtractionUnavailableError(Exception):
    pass


def configured_gemini() -> GeminiSettings:
    if not settings.gemini_enabled:
        raise ExtractionUnavailableError("Gemini extraction is disabled on this server")
    try:
        return GeminiSettings()
    except ValidationError:
        # Validation errors can contain settings inputs. Never send them to callers.
        raise ExtractionUnavailableError(
            "Gemini extraction is not configured on this server"
        ) from None


def extraction_methods() -> list[ExtractionMethod]:
    try:
        configured_gemini()
        gemini = ExtractionMethod(extractor="gemini", available=True)
    except ExtractionUnavailableError as error:
        gemini = ExtractionMethod(extractor="gemini", available=False, reason=str(error))
    return [ExtractionMethod(extractor="rules", available=True), gemini]


def select_extractor(choice: ExtractorChoice) -> Extractor:
    if choice == "rules":
        return RuleBasedExtractor()
    return LLMExtractor(configured_gemini())
