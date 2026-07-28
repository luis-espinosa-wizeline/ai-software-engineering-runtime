"""Provider-agnostic capability request and result models."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from app.shared import CapabilityId, DomainModel, JsonValue, Metadata, RuntimeId


class CapabilityStatus(StrEnum):
    """Outcome state of a capability invocation."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CapabilityMetadata(DomainModel):
    """Observable facts about a capability invocation."""

    provider: str | None = None
    model: str | None = None
    duration_ms: int | None = None
    attributes: Metadata = Field(default_factory=dict)


class CapabilityRequest(DomainModel):
    """A workflow's provider-neutral request for a capability."""

    capability_id: CapabilityId
    inputs: dict[str, JsonValue] = Field(default_factory=dict)
    request_id: RuntimeId = Field(default_factory=uuid4)
    requested_at: datetime
    metadata: Metadata = Field(default_factory=dict)


class CapabilityResult(DomainModel):
    """The recorded result of fulfilling a capability request."""

    request_id: RuntimeId
    status: CapabilityStatus
    completed_at: datetime
    outputs: dict[str, JsonValue] = Field(default_factory=dict)
    error: str | None = None
    metadata: CapabilityMetadata = Field(default_factory=CapabilityMetadata)
