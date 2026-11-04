import json
from copy import deepcopy

import httpx
import pytest
from pydantic import ValidationError

from app.evaluation.__main__ import evaluate
from app.evaluation.dataset import DEFAULT_DATASET, load_dataset
from app.evaluation.execution import Pricing
from app.extraction.assessment import assess_sources
from app.extraction.base import ExecutionMetadata
from app.extraction.llm import GeminiSettings, LLMExtractionError, LLMExtractor, normalize_claim
from app.extraction.llm_schema import LLMClaims


@pytest.fixture
def packet():
    return load_dataset().packets[0]


def empty_claims():
    return {name: [] for name in LLMClaims.model_fields}


def claim(packet, name="patient_name", value="Avery Morgan"):
    evidence = packet.expected[name].evidence[0].model_dump(mode="json")
    return {"source_value": value, "proposed_value": value, "evidence": [evidence]}


def response(claims, **extra):
    return {
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {
                    "parts": [{"text": json.dumps(claims)}],
                },
            }
        ],
        "modelVersion": "test-model-revision",
        "usageMetadata": {
            "promptTokenCount": 100,
            "candidatesTokenCount": 20,
            "thoughtsTokenCount": 10,
        },
        **extra,
    }


def adapter(raw, *, status=200, handler=None, **settings):
    def respond(request):
        if handler:
            handler(request)
        return httpx.Response(status, json=raw)

    return LLMExtractor(
        GeminiSettings(api_key="test-secret", model="test-model", **settings),
        transport=httpx.MockTransport(respond),
    )


def test_packet_request_schema_and_execution_are_separate_from_api_result(packet):
    claims = empty_claims()
    claims["patient_name"] = [claim(packet)]
    requests = []

    def inspect(request):
        requests.append(request)
        assert request.headers["x-goog-api-key"] == "test-secret"
        assert "test-secret" not in str(request.url)
        body = json.loads(request.content)
        assert body["generationConfig"]["responseJsonSchema"] == LLMClaims.model_json_schema()
        assert json.loads(body["contents"][0]["parts"][0]["text"])[0]["document_id"] == str(
            packet.sources[0].document_id,
        )
        assert "untrusted" in body["systemInstruction"]["parts"][0]["text"]

    raw = response(claims)
    result = assess_sources(adapter(raw, handler=inspect), packet.sources)
    assert len(requests) == 1
    assert result.fields["patient_name"].value == "Avery Morgan"
    assert result.findings[1].status == "missing"
    assert not result.complete
    assert result.execution.raw_response == raw
    assert result.execution.request_ms >= 0
    assert result.execution.model_version == "test-model-revision"
    assert "execution" not in result.model_dump()
    assert "raw_response" not in result.execution.model_dump()


def test_equivalent_claims_merge_evidence_and_conflicts_survive(packet):
    claims = empty_claims()
    first = claim(packet)
    claims["patient_name"] = [first, deepcopy(first)]
    result = assess_sources(adapter(response(claims)), packet.sources)
    assert len(result.fields["patient_name"].candidates) == 1
    assert len(result.fields["patient_name"].candidates[0].evidence) == 1
    assert result.findings[0].status == "found"
    # Both values appear on this synthetic page, and must remain alternatives.
    source = packet.sources[0].model_copy(deep=True)
    source.pages[0].text += "\nPatient: Blake Morgan"
    other = deepcopy(first)
    other.update(source_value="Blake Morgan", proposed_value="Blake Morgan")
    other["evidence"][0]["quote"] = "Patient: Blake Morgan"
    claims["patient_name"].append(other)
    result = assess_sources(adapter(response(claims)), [source])
    assert result.findings[0].status == "conflicting"
    assert result.fields["patient_name"].value is None


@pytest.mark.parametrize("change", ["document", "page", "quote", "value"])
def test_unsupported_claim_stays_visible_but_cannot_be_selected(packet, change):
    claims = empty_claims()
    item = claim(packet)
    if change == "document":
        item["evidence"][0]["document_id"] = "00000000-0000-0000-0000-000000000000"
    elif change == "page":
        item["evidence"][0]["page_number"] = 99
    elif change == "quote":
        item["evidence"][0]["quote"] = "Invented quote"
    else:
        item["source_value"] = "Invented Person"
    claims["patient_name"] = [item]
    result = assess_sources(adapter(response(claims)), packet.sources)
    assert result.findings[0].status == "invalid"
    assert result.fields["patient_name"].value is None
    assert result.fields["patient_name"].candidates[0].issue


@pytest.mark.parametrize("mutation", ["missing-key", "extra-key", "no-evidence", "wrong-type"])
def test_invalid_claim_schema_fails_packet(packet, mutation):
    claims = empty_claims()
    if mutation == "missing-key":
        del claims["date_of_birth"]
    elif mutation == "extra-key":
        claims["complete"] = True
    else:
        item = claim(packet)
        if mutation == "no-evidence":
            item["evidence"] = []
        else:
            item["evidence"][0]["page_number"] = "1"
        claims["patient_name"] = [item]
    with pytest.raises(LLMExtractionError, match="structured response"):
        adapter(response(claims)).extract(packet.sources)


@pytest.mark.parametrize(
    "raw",
    [
        {},
        [],
        {"promptFeedback": {"blockReason": "SAFETY"}},
        response({}, candidates=[{"finishReason": "MAX_TOKENS"}]),
        response({}, candidates=[{"finishReason": "STOP", "content": {"parts": [{"text": "{"}]}}]),
    ],
)
def test_blocked_truncated_and_malformed_responses_fail(packet, raw):
    with pytest.raises(LLMExtractionError):
        adapter(raw).extract(packet.sources)


@pytest.mark.parametrize("status", [400, 401, 429, 500, 302])
def test_http_errors_do_not_retry_or_leak_response_body(packet, status):
    calls = []
    with pytest.raises(LLMExtractionError, match=f"HTTP {status}") as caught:
        adapter({"error": "test-secret"}, status=status, handler=calls.append).extract(
            packet.sources
        )
    assert "test-secret" not in str(caught.value)
    assert len(calls) == 1


def test_transport_timeout_is_explicit_and_has_no_retry(packet):
    calls = []

    def fail(request):
        calls.append(request)
        raise httpx.ReadTimeout("sensitive provider detail", request=request)

    with pytest.raises(LLMExtractionError, match="transport failure") as caught:
        adapter({}, handler=fail).extract(packet.sources)
    assert "sensitive" not in str(caught.value)
    assert len(calls) == 1


def test_packet_input_limit_prevents_network_call(packet):
    calls = []
    with pytest.raises(LLMExtractionError, match="character limit"):
        adapter({}, max_input_chars=1, handler=calls.append).extract(packet.sources)
    assert not calls


@pytest.mark.parametrize(
    "raw,proposed,expected",
    [
        ("March 12, 1974", "1974-03-12", "1974-03-12"),
        ("Mar 12, 1974", "1974-03-12", "1974-03-12"),
        ("03/21/1974", "1974-03-21", "1974-03-21"),
        ("03/12/1974", "1974-03-12", None),
        ("March 12, 1974", "1974-03-21", None),
        ("February 30, 1974", "1974-02-28", None),
        ("March 12, 2999", "2999-03-12", None),
    ],
)
def test_date_normalization_is_deterministic_and_conservative(raw, proposed, expected):
    assert normalize_claim("date_of_birth", raw, proposed)[0] == expected


def test_non_date_claim_cannot_rewrite_source_text():
    assert normalize_claim("patient_name", "Avery Morgan", "Invented Person") == (
        "Avery Morgan",
        None,
    )
    assert normalize_claim("requested_specialty", "neurology", "cardiology")[0] is None


def test_usage_cost_thinking_cache_and_unknowns():
    pricing = Pricing(input_per_million=1, output_per_million=2)
    usage = ExecutionMetadata(
        usage={
            "promptTokenCount": 100,
            "candidatesTokenCount": 20,
            "thoughtsTokenCount": 10,
        }
    )
    assert pricing.estimate(usage) == pytest.approx(0.00016)
    usage.usage["cachedContentTokenCount"] = 10
    assert pricing.estimate(usage) is None
    pricing.cached_input_per_million = 0.5
    assert pricing.estimate(usage) == pytest.approx(0.000155)
    assert pricing.estimate(ExecutionMetadata()) is None
    for value in [float("nan"), float("inf"), -1]:
        with pytest.raises(ValidationError):
            Pricing(input_per_million=value, output_per_million=1)


def test_evaluation_retains_all_packet_artifacts_and_model_metadata(tmp_path):
    raw = response(empty_claims())
    report = evaluate(DEFAULT_DATASET, adapter(raw), artifact_dir=tmp_path / "artifacts")
    assert report["packet_count"] == 30
    assert len(list((tmp_path / "artifacts").iterdir())) == 30
    saved = json.loads((tmp_path / "artifacts/0000.json").read_text())
    assert saved["raw_response"] == raw
    assert "raw_response" not in report["packets"][0]["execution"]
    assert report["packets"][0]["execution"]["prompt_version"] == "referral-claims/1"
    assert report["execution"]["estimated_total_cost"] is None
    assert "test-secret" not in json.dumps(report)


def test_failed_evaluation_retains_response_without_publishing_quality_report(tmp_path):
    raw = response({}, candidates=[{"finishReason": "MAX_TOKENS"}])
    with pytest.raises(LLMExtractionError):
        evaluate(DEFAULT_DATASET, adapter(raw), artifact_dir=tmp_path / "artifacts")
    saved = json.loads((tmp_path / "artifacts/0000.json").read_text())
    assert saved["raw_response"] == raw
    assert saved["error"]
    assert not (tmp_path / "report.json").exists()


def test_rule_quality_remains_identical_to_committed_baseline():
    from pathlib import Path

    baseline = json.loads(
        (Path(__file__).parents[1] / "reports/extraction-baseline-v1/report.json").read_text()
    )
    actual = evaluate(DEFAULT_DATASET)
    for key in ["overall", "by_field", "by_document_type", "dataset_sha256"]:
        assert actual[key] == baseline[key]
