"""Policy evaluation domain models."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from app.shared import DomainModel, Metadata, RuntimeId


class PolicyOutcome(StrEnum):
    """The disposition produced by a policy evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_REVIEW = "require_review"


class PolicyViolation(DomainModel):
    """A concrete policy constraint that was not satisfied."""

    policy_id: str
    message: str
    code: str | None = None
    path: str | None = None
    metadata: Metadata = Field(default_factory=dict)


class PolicyDecision(DomainModel):
    """An observable policy evaluation made during an execution."""

    policy_id: str
    outcome: PolicyOutcome
    evaluated_at: datetime
    decision_id: RuntimeId = Field(default_factory=uuid4)
    reason: str | None = None
    violations: tuple[PolicyViolation, ...] = ()
    metadata: Metadata = Field(default_factory=dict)
