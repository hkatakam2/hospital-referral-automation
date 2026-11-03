from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.referrals import get_referral_repository
from app.main import app
from app.repositories.referrals import InMemoryReferralRepository


@pytest.fixture
def client():
    repository = InMemoryReferralRepository()
    app.dependency_overrides[get_referral_repository] = lambda: repository
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_referral_repository, None)


@pytest.fixture
def referral_data():
    # Values transcribed from fixtures/referrals/complete.txt.
    return {
        "patient_name": "Avery Morgan",
        "date_of_birth": "1974-03-12",
        "referring_organization": "Lakeside Primary Care",
        "requested_specialty": "cardiology",
        "referral_reason": "Recurrent palpitations",
    }


def test_create_and_retrieve_referral(client, referral_data):
    before = datetime.now(timezone.utc)
    response = client.post("/api/referrals", json=referral_data)
    after = datetime.now(timezone.utc)

    assert response.status_code == 201
    created = response.json()
    assert {field: created[field] for field in referral_data} == referral_data
    assert UUID(created["id"]).version == 4
    created_at = datetime.fromisoformat(created["created_at"].replace("Z", "+00:00"))
    assert created_at.utcoffset() == timedelta(0)
    assert before <= created_at <= after

    retrieved = client.get(f"/api/referrals/{created['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json() == created


def test_referrals_have_unique_ids_and_preserve_independent_records(client, referral_data):
    first = client.post("/api/referrals", json=referral_data).json()
    second_data = {**referral_data, "patient_name": "Jordan Ellis"}
    second = client.post("/api/referrals", json=second_data).json()

    assert first["id"] != second["id"]
    assert client.get(f"/api/referrals/{first['id']}").json() == first
    assert client.get(f"/api/referrals/{second['id']}").json() == second


@pytest.mark.parametrize("field", [
    "patient_name", "date_of_birth", "referring_organization",
    "requested_specialty", "referral_reason",
])
def test_missing_required_field_is_rejected(client, referral_data, field):
    del referral_data[field]
    response = client.post("/api/referrals", json=referral_data)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])


@pytest.mark.parametrize("field", [
    "patient_name", "referring_organization", "referral_reason",
])
@pytest.mark.parametrize("value", ["", " \t\n", None])
def test_empty_required_text_is_rejected(client, referral_data, field, value):
    referral_data[field] = value
    assert client.post("/api/referrals", json=referral_data).status_code == 422


def test_surrounding_whitespace_is_trimmed(client, referral_data):
    for field in ["patient_name", "referring_organization", "referral_reason"]:
        referral_data[field] = f"  {referral_data[field]}\n"
    response = client.post("/api/referrals", json=referral_data)
    assert response.status_code == 201
    created = response.json()
    assert created["patient_name"] == "Avery Morgan"
    assert created["referring_organization"] == "Lakeside Primary Care"
    assert created["referral_reason"] == "Recurrent palpitations"
    assert client.get(f"/api/referrals/{created['id']}").json() == created


@pytest.mark.parametrize("value", ["not-a-date", "1974-02-30", None])
def test_invalid_date_is_rejected(client, referral_data, value):
    referral_data["date_of_birth"] = value
    assert client.post("/api/referrals", json=referral_data).status_code == 422


def test_future_date_is_rejected(client, referral_data):
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    referral_data["date_of_birth"] = tomorrow.isoformat()
    assert client.post("/api/referrals", json=referral_data).status_code == 422


@pytest.mark.parametrize("value", ["neurology", "", None])
def test_unsupported_specialty_is_rejected(client, referral_data, value):
    referral_data["requested_specialty"] = value
    assert client.post("/api/referrals", json=referral_data).status_code == 422


@pytest.mark.parametrize("field,value", [
    ("patient_nmae", "Typo"),
    ("id", str(uuid4())),
    ("created_at", "2000-01-01T00:00:00Z"),
])
def test_unknown_and_server_managed_fields_are_rejected(client, referral_data, field, value):
    referral_data[field] = value
    assert client.post("/api/referrals", json=referral_data).status_code == 422


def test_unknown_referral_returns_not_found(client):
    response = client.get(f"/api/referrals/{uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Referral not found"}


def test_malformed_id_is_rejected(client):
    assert client.get("/api/referrals/not-a-uuid").status_code == 422


def test_new_repository_does_not_contain_previous_records(client, referral_data):
    created = client.post("/api/referrals", json=referral_data).json()
    fresh_repository = InMemoryReferralRepository()
    app.dependency_overrides[get_referral_repository] = lambda: fresh_repository
    assert client.get(f"/api/referrals/{created['id']}").status_code == 404


def test_list_starts_empty(client):
    response = client.get("/api/referrals")
    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_created_records_in_creation_order(client, referral_data):
    first = client.post("/api/referrals", json=referral_data).json()
    second = client.post(
        "/api/referrals", json={**referral_data, "patient_name": "Jordan Ellis"},
    ).json()

    response = client.get("/api/referrals")
    assert response.status_code == 200
    assert response.json() == [first, second]


def test_correct_referral_preserves_other_fields_and_records(client, referral_data):
    first = client.post("/api/referrals", json=referral_data).json()
    second = client.post("/api/referrals", json=referral_data).json()
    changes = {"date_of_birth": "1974-03-21"}

    response = client.patch(f"/api/referrals/{first['id']}", json=changes)
    expected = {**first, **changes}
    assert response.status_code == 200
    assert response.json() == expected
    assert client.get(f"/api/referrals/{first['id']}").json() == expected
    assert client.get(f"/api/referrals/{second['id']}").json() == second
    assert client.get("/api/referrals").json() == [expected, second]


def test_correct_all_fields_trims_text_and_preserves_server_fields(client, referral_data):
    created = client.post("/api/referrals", json=referral_data).json()
    changes = {
        "patient_name": "  Jordan Ellis\n",
        "date_of_birth": "1980-01-02",
        "referring_organization": "  Pine Clinic\t",
        "requested_specialty": "cardiology",
        "referral_reason": "  Follow-up consultation  ",
    }
    expected = {**created, **{key: value.strip() for key, value in changes.items()}}
    response = client.patch(f"/api/referrals/{created['id']}", json=changes)
    assert response.status_code == 200
    assert response.json() == expected
    assert client.get(f"/api/referrals/{created['id']}").json() == expected


def test_empty_correction_is_a_no_op(client, referral_data):
    created = client.post("/api/referrals", json=referral_data).json()
    response = client.patch(f"/api/referrals/{created['id']}", json={})
    assert response.status_code == 200
    assert response.json() == created
    assert client.get(f"/api/referrals/{created['id']}").json() == created


@pytest.mark.parametrize("field", [
    "patient_name", "date_of_birth", "referring_organization",
    "requested_specialty", "referral_reason",
])
def test_correction_cannot_clear_required_fields(client, referral_data, field):
    created = client.post("/api/referrals", json=referral_data).json()
    response = client.patch(f"/api/referrals/{created['id']}", json={field: None})
    assert response.status_code == 422
    assert client.get(f"/api/referrals/{created['id']}").json() == created


@pytest.mark.parametrize("changes", [
    {"patient_name": ""},
    {"patient_name": " \t\n"},
    {"referring_organization": ""},
    {"referring_organization": " \t\n"},
    {"referral_reason": ""},
    {"referral_reason": " \t\n"},
    {"date_of_birth": "not-a-date"},
    {"date_of_birth": "1974-02-30"},
    {"date_of_birth": "9999-12-31"},
    {"requested_specialty": "neurology"},
    {"requested_specialty": ""},
    {"patient_nmae": "Typo"},
    {"id": str(uuid4())},
    {"created_at": "2000-01-01T00:00:00Z"},
])
def test_invalid_correction_leaves_record_unchanged(client, referral_data, changes):
    created = client.post("/api/referrals", json=referral_data).json()
    # Include a valid change to prove that mixed updates never apply partially.
    response = client.patch(
        f"/api/referrals/{created['id']}", json={"patient_name": "Jordan Ellis", **changes},
    )
    assert response.status_code == 422
    assert client.get(f"/api/referrals/{created['id']}").json() == created
    assert client.get("/api/referrals").json() == [created]


def test_correct_unknown_referral_returns_not_found(client):
    response = client.patch(
        f"/api/referrals/{uuid4()}", json={"patient_name": "Jordan Ellis"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Referral not found"}
    assert client.get("/api/referrals").json() == []


def test_correct_malformed_id_is_rejected(client):
    response = client.patch(
        "/api/referrals/not-a-uuid", json={"patient_name": "Jordan Ellis"},
    )
    assert response.status_code == 422
