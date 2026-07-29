"""Structured engineering knowledge produced by source-code analysis."""

from enum import StrEnum

from pydantic import Field, model_validator

from app.shared import DomainModel


class FindingSeverity(StrEnum):
    """Impact level assigned to an engineering finding."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EngineeringFinding(DomainModel):
    """One actionable observation about source code."""

    summary: str
    source_file: str
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    rule_id: str | None = None
    severity: FindingSeverity
    confidence: float = Field(ge=0, le=1)
    category: str
    explanation: str
    recommendation: str

    @model_validator(mode="after")
    def _validate_text(self) -> EngineeringFinding:
        for field_name in (
            "summary",
            "source_file",
            "category",
            "explanation",
            "recommendation",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"Finding {field_name} must not be blank")
        if self.rule_id is not None and not self.rule_id.strip():
            raise ValueError("Finding rule_id must not be blank")
        if self.end_line is not None and self.start_line is None:
            raise ValueError("Finding end_line requires start_line")
        if (
            self.start_line is not None
            and self.end_line is not None
            and self.end_line < self.start_line
        ):
            raise ValueError("Finding end_line must not precede start_line")
        return self


class EngineeringFindings(DomainModel):
    """Provider-neutral engineering knowledge produced by analysis."""

    findings: tuple[EngineeringFinding, ...] = ()
