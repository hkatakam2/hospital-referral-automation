"""Versioned requirements over assessed source findings, independent of extraction."""
from collections.abc import Sequence
from pathlib import Path

from app.schemas.extraction import (
    Finding,
    PolicyAssessment,
    PolicyRequirementResult,
    ReferralPolicy,
    SourceDocument,
)

# Immutable baseline for the existing evaluation corpus, independent of app configuration.
BASELINE_POLICY = ReferralPolicy(
    id="five-required-fields", version="2", name="Demo referral intake",
    required_fields=("patient_name", "date_of_birth", "referring_organization",
                     "requested_specialty", "referral_reason"),
)
DEFAULT_POLICY_PATH = Path(__file__).with_name("policies") / "default.json"


def load_policy(path: Path) -> ReferralPolicy:
    try:
        return ReferralPolicy.model_validate_json(path.read_text())
    except (OSError, ValueError) as error:
        raise ValueError(f"Invalid referral policy configuration: {path}") from error


def evaluate_policy(
    policy: ReferralPolicy, findings: Sequence[Finding], sources: Sequence[SourceDocument],
) -> PolicyAssessment:
    statuses = {finding.field: finding.status for finding in findings}
    return PolicyAssessment(
        policy=policy,
        requirements=[PolicyRequirementResult(
            field=field, satisfied=statuses[field] == "found", finding=statuses[field],
        ) for field in policy.required_fields],
        source_coverage_satisfied=bool(sources) and all(
            source.parse_status == "parsed" and bool(source.pages)
            and all(page.text.strip() for page in source.pages) for source in sources
        ),
    )
