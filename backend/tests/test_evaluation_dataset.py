import pytest
from pydantic import ValidationError

from app.evaluation.dataset import Dataset, load_dataset


def test_versioned_corpus_contains_thirty_independently_annotated_packets():
    dataset = load_dataset()
    assert dataset.version == "synthetic-referrals/1"
    assert len(dataset.packets) == 30
    assert {packet.document_type for packet in dataset.packets} >= {
        "labeled", "narrative", "conflicting", "partial", "alternate_format", "missing",
    }
    narrative = next(packet for packet in dataset.packets if packet.id == "narrative-letter")
    assert narrative.complete
    assert narrative.expected["date_of_birth"].value == "1974-03-12"


@pytest.mark.parametrize("mutation", [
    "duplicate_id", "missing_annotation", "wrong_page", "wrong_quote", "wrong_document",
    "false_completeness", "missing_value", "wrong_coverage", "duplicate_page",
])
def test_dataset_rejects_inconsistent_ground_truth(mutation):
    raw = load_dataset().model_dump(mode="json")
    packet = raw["packets"][0]
    annotation = packet["expected"]["patient_name"]
    if mutation == "duplicate_id":
        raw["packets"][1]["id"] = packet["id"]
    elif mutation == "missing_annotation":
        del packet["expected"]["patient_name"]
    elif mutation == "wrong_page":
        annotation["evidence"][0]["page_number"] = 99
    elif mutation == "wrong_quote":
        annotation["evidence"][0]["quote"] = "Not in the packet"
    elif mutation == "wrong_document":
        annotation["evidence"][0]["document_id"] = "00000000-0000-0000-0000-000000000001"
    elif mutation == "false_completeness":
        packet["complete"] = False
    elif mutation == "missing_value":
        annotation["value"] = None
    elif mutation == "wrong_coverage":
        packet["sources"][0]["parse_status"] = "partial"
    else:
        packet["sources"][0]["pages"].append(packet["sources"][0]["pages"][0])
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)
