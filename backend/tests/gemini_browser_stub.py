"""Deterministic provider HTTP for browser tests; never loaded by the application."""
import json

import httpx

from app.config import settings
from app.extraction import selection
from app.extraction.llm import GeminiSettings, LLMExtractor

VALUES = {
    "patient_name": "Avery Morgan", "date_of_birth": "1974-03-12",
    "referring_organization": "Lakeside", "requested_specialty": "cardiology",
    "referral_reason": "Palpitations",
}


def provider_response(request):
    body = json.loads(request.content)
    sources = json.loads(body["contents"][0]["parts"][0]["text"])
    claims = {field: [] for field in VALUES}
    for field, value in VALUES.items():
        for source in sources:
            for page in source["pages"]:
                if value in page["text"]:
                    claims[field].append({
                        "source_value": value, "proposed_value": value,
                        "evidence": [{"document_id": source["document_id"],
                                      "page_number": page["page_number"], "quote": value}],
                    })
    return httpx.Response(200, json={
        "candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": json.dumps(claims)}],
        }}], "modelVersion": "browser-stub-revision",
    })


def enable():
    settings.gemini_enabled = True
    selection.GeminiSettings = lambda: GeminiSettings(
        api_key="browser-stub-key", model="browser-stub-model", _env_file=None,
    )
    selection.LLMExtractor = lambda config: LLMExtractor(
        config, transport=httpx.MockTransport(provider_response),
    )
