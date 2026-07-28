"""Top-level Runtime and trigger domain models."""

from datetime import datetime
from uuid import uuid4

from pydantic import Field

from app.shared import DomainModel, JsonValue, Metadata, RuntimeId


class Runtime(DomainModel):
    """Identity and descriptive information for a Runtime installation."""

    name: str
    version: str
    runtime_id: RuntimeId = Field(default_factory=uuid4)
    metadata: Metadata = Field(default_factory=dict)


class TriggerMetadata(DomainModel):
    """Provider-neutral facts describing a trigger source."""

    source: str
    event_type: str
    subject: str | None = None
    attributes: Metadata = Field(default_factory=dict)


class Trigger(DomainModel):
    """A configured source capable of initiating runtime work."""

    name: str
    kind: str
    trigger_id: RuntimeId = Field(default_factory=uuid4)
    description: str | None = None
    metadata: Metadata = Field(default_factory=dict)


class TriggerEvent(DomainModel):
    """An occurrence emitted by a trigger."""

    trigger: Trigger
    metadata: TriggerMetadata
    event_id: RuntimeId = Field(default_factory=uuid4)
    occurred_at: datetime
    payload: dict[str, JsonValue] = Field(default_factory=dict)
