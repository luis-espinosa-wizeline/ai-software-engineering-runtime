"""Result publication domain models."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from app.shared import DomainModel, JsonValue, Metadata, RuntimeId


class PublicationStatus(StrEnum):
    """Outcome state of a publication attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PublicationRequest(DomainModel):
    """A provider-neutral request to publish a workflow result."""

    execution_id: RuntimeId
    destination: str
    content: dict[str, JsonValue] = Field(default_factory=dict)
    request_id: RuntimeId = Field(default_factory=uuid4)
    requested_at: datetime
    metadata: Metadata = Field(default_factory=dict)


class PublicationResult(DomainModel):
    """The recorded outcome of a publication request."""

    request_id: RuntimeId
    status: PublicationStatus
    completed_at: datetime
    external_reference: str | None = None
    error: str | None = None
    metadata: Metadata = Field(default_factory=dict)
