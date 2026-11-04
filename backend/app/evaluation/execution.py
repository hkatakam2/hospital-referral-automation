"""Execution artifacts and explicit pricing assumptions, separate from quality scoring."""
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.extraction.base import ExecutionMetadata


class Pricing(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)
    cached_input_per_million: float | None = Field(default=None, ge=0)
    currency: str = "USD"

    def estimate(self, execution: ExecutionMetadata) -> float | None:
        usage = execution.usage
        if "promptTokenCount" not in usage or "candidatesTokenCount" not in usage:
            return None
        cached = usage.get("cachedContentTokenCount", 0)
        prompt = usage["promptTokenCount"]
        if cached > prompt or (cached and self.cached_input_per_million is None):
            return None
        output = usage["candidatesTokenCount"] + usage.get("thoughtsTokenCount", 0)
        return ((prompt - cached) * self.input_per_million
                + cached * (self.cached_input_per_million or 0)
                + output * self.output_per_million) / 1_000_000


def execution_record(execution: ExecutionMetadata, pricing: Pricing | None) -> dict:
    return {
        **execution.model_dump(),
        "estimated_cost": pricing.estimate(execution) if pricing else None,
    }


def write_artifact(
    directory: Path | None, index: int, packet_id: str, execution: ExecutionMetadata,
    *, error: str | None = None,
) -> None:
    if directory is None:
        return
    # Index filenames cannot escape the directory through dataset-controlled packet IDs.
    artifact = {
        "packet_id": packet_id, "execution": execution.model_dump(),
        "raw_response": execution.raw_response, "error": error,
    }
    (directory / f"{index:04d}.json").write_text(json.dumps(artifact, indent=2) + "\n")
