from app.schemas.extraction import Candidate, FieldResult


def add_candidate(
    result: FieldResult, incoming: Candidate, *, deduplicate_evidence: bool = False,
) -> None:
    """Merge equivalent claims before assessment interprets alternatives as conflicts."""
    existing = next((candidate for candidate in result.candidates if (
        candidate.value == incoming.value and candidate.issue == incoming.issue
        and (incoming.value is not None or candidate.raw_value == incoming.raw_value)
    )), None)
    if existing is None:
        existing = incoming.model_copy(deep=True)
        existing.evidence = []
        result.candidates.append(existing)
    for evidence in incoming.evidence:
        if not deduplicate_evidence or evidence not in existing.evidence:
            existing.evidence.append(evidence.model_copy(deep=True))
