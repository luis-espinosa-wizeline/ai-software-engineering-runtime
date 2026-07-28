"""Provider-neutral outputs produced by executable capabilities."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.shared import JsonValue, Metadata

type ArtifactName = Annotated[
    str,
    StringConstraints(
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]


class Artifact(BaseModel):
    """A named, provider-neutral piece of work produced by a workflow step."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: ArtifactName
    payload: JsonValue
    metadata: Metadata = Field(default_factory=dict)
