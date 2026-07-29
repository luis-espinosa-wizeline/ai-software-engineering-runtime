"""Provider-neutral events accepted by a Runtime Host."""

from pydantic import Field, model_validator

from app.shared import DomainModel, JsonValue, Metadata


class HostEvent(DomainModel):
    """Normalized external intent sufficient to route and start one workflow."""

    event_kind: str
    inputs: dict[str, JsonValue]
    event_id: str | None = None
    metadata: Metadata = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_identifiers(self) -> HostEvent:
        if not self.event_kind.strip():
            raise ValueError("Host event kind must not be blank")
        if self.event_id is not None and not self.event_id.strip():
            raise ValueError("Host event identifier must not be blank")
        return self
