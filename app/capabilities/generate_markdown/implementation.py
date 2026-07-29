"""Deterministic rendering of EngineeringFindings as Markdown."""

import re

from pydantic import ValidationError

from app.capabilities import (
    Artifact,
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
)
from app.capabilities.documents import MarkdownDocument
from app.capabilities.findings import (
    EngineeringFinding,
    EngineeringFindings,
)

GENERATE_MARKDOWN = Capability(
    name="GenerateMarkdown",
    description=(
        "Transform structured engineering findings into a human-readable "
        "Markdown document."
    ),
    category=CapabilityCategory.TRANSFORMATION,
    contract="GenerateMarkdown",
    version="1",
    input_artifacts=(
        ArtifactDefinition(
            name="engineering_findings",
            description="Validated, structured engineering findings.",
        ),
    ),
    output_artifacts=(
        ArtifactDefinition(
            name="markdown", description="Rendered Markdown document."
        ),
    ),
    tags=("transformation", "markdown", "engineering-communication"),
)

_MARKDOWN_CONTROL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>])")


class GenerateMarkdownImplementation:
    """Render findings without analyzing, reordering, or expanding them."""

    @property
    def capability(self) -> Capability:
        return GENERATE_MARKDOWN

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        findings = self._findings(request.artifact("engineering_findings"))
        document = MarkdownDocument(content=self._render(findings))
        return CapabilityResult(
            artifacts=(
                Artifact(name="markdown", payload=document.model_dump(mode="json")),
            )
        )

    @staticmethod
    def _findings(artifact: Artifact) -> EngineeringFindings:
        try:
            return EngineeringFindings.model_validate(artifact.payload)
        except ValidationError as error:
            raise ValueError(
                "engineering_findings artifact must contain valid EngineeringFindings"
            ) from error

    @staticmethod
    def _render(findings: EngineeringFindings) -> str:
        lines = ["## Engineering Analysis", ""]
        if not findings.findings:
            lines.extend(("No engineering findings were identified.", ""))
            return "\n".join(lines)

        for index, finding in enumerate(findings.findings, start=1):
            lines.extend(GenerateMarkdownImplementation._render_finding(index, finding))
        return "\n".join(lines)

    @staticmethod
    def _render_finding(index: int, finding: EngineeringFinding) -> list[str]:
        escape = GenerateMarkdownImplementation._escape
        escape_inline = GenerateMarkdownImplementation._escape_inline
        metadata = [
            f"### Finding {index}: {escape_inline(finding.summary)}",
            "",
            f"- **Source:** {escape_inline(finding.source_file)}",
            f"- **Severity:** {finding.severity.value}",
            f"- **Confidence:** {finding.confidence}",
            f"- **Category:** {escape_inline(finding.category)}",
        ]
        if finding.start_line is not None:
            lines = str(finding.start_line)
            if finding.end_line is not None:
                lines = f"{lines}-{finding.end_line}"
            metadata.append(f"- **Lines:** {lines}")
        if finding.rule_id is not None:
            metadata.append(f"- **Rule:** {escape_inline(finding.rule_id)}")
        return metadata + [
            "",
            escape(finding.explanation),
            "",
            "**Recommendation**",
            "",
            escape(finding.recommendation),
            "",
        ]

    @staticmethod
    def _escape(value: str) -> str:
        """Escape Markdown controls while preserving text and line order."""
        return _MARKDOWN_CONTROL.sub(r"\\\1", value)

    @staticmethod
    def _escape_inline(value: str) -> str:
        """Keep untrusted text inside the heading or list item that owns it."""
        return GenerateMarkdownImplementation._escape(" ".join(value.splitlines()))
