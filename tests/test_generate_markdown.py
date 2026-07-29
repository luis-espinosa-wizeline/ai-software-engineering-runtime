import json
from typing import Any

import httpx
import pytest

from app.capabilities import Artifact, CapabilityRequest
from app.capabilities.analyze_source_code import (
    AnalyzeSourceCodeOllamaImplementation,
    EngineeringFinding,
    EngineeringFindings,
    FindingSeverity,
)
from app.capabilities.generate_markdown import (
    GenerateMarkdownImplementation,
    MarkdownDocument,
)
from app.capabilities.merge_engineering_findings import (
    MergeEngineeringFindingsImplementation,
)


def findings_request(
    implementation: GenerateMarkdownImplementation,
    findings: EngineeringFindings,
) -> CapabilityRequest:
    return CapabilityRequest(
        capability=implementation.capability,
        artifacts=(
            Artifact(
                name="engineering_findings",
                payload=findings.model_dump(mode="json"),
            ),
        ),
    )


def test_generate_markdown_renders_every_finding_in_declared_order() -> None:
    findings = EngineeringFindings(
        findings=(
            EngineeringFinding(
                summary="Retry loop has no bound",
                source_file="retry.py",
                severity=FindingSeverity.HIGH,
                confidence=0.92,
                category="reliability",
                explanation="The loop can continue indefinitely.",
                recommendation="Add a maximum attempt count.",
            ),
            EngineeringFinding(
                summary="Unclear function name",
                source_file="names.py",
                severity=FindingSeverity.LOW,
                confidence=0.7,
                category="maintainability",
                explanation="The name does not describe the returned value.",
                recommendation="Rename the function to describe its result.",
            ),
        )
    )
    implementation = GenerateMarkdownImplementation()

    result = implementation.execute(findings_request(implementation, findings))

    assert len(result.artifacts) == 1
    assert result.artifacts[0].name == "markdown"
    document = MarkdownDocument.model_validate(result.artifacts[0].payload)
    assert document.content == (
        "## Engineering Analysis\n"
        "\n"
        "### Finding 1: Retry loop has no bound\n"
        "\n"
        "- **Source:** retry\\.py\n"
        "- **Severity:** high\n"
        "- **Confidence:** 0.92\n"
        "- **Category:** reliability\n"
        "\n"
        "The loop can continue indefinitely\\.\n"
        "\n"
        "**Recommendation**\n"
        "\n"
        "Add a maximum attempt count\\.\n"
        "\n"
        "### Finding 2: Unclear function name\n"
        "\n"
        "- **Source:** names\\.py\n"
        "- **Severity:** low\n"
        "- **Confidence:** 0.7\n"
        "- **Category:** maintainability\n"
        "\n"
        "The name does not describe the returned value\\.\n"
        "\n"
        "**Recommendation**\n"
        "\n"
        "Rename the function to describe its result\\.\n"
    )
    assert document.content.index("Finding 1") < document.content.index("Finding 2")


def test_empty_findings_produce_useful_markdown() -> None:
    implementation = GenerateMarkdownImplementation()

    result = implementation.execute(
        findings_request(implementation, EngineeringFindings())
    )

    assert result.artifacts == (
        Artifact(
            name="markdown",
            payload={
                "content": (
                    "## Engineering Analysis\n"
                    "\n"
                    "No engineering findings were identified.\n"
                )
            },
        ),
    )


def test_renderer_escapes_untrusted_markdown_without_dropping_content() -> None:
    findings = EngineeringFindings(
        findings=(
            EngineeringFinding(
                summary="# Injected heading\n[remote](https://example.test)",
                source_file="src/[unsafe].py",
                start_line=4,
                end_line=8,
                rule_id="unsafe.rule",
                severity=FindingSeverity.MEDIUM,
                confidence=0.8,
                category="security\n- fake category",
                explanation="First line\n## Fake heading\n<script>alert(1)</script>",
                recommendation="Use `safe_call()`.\n![remote](image.example/x)",
            ),
        )
    )
    implementation = GenerateMarkdownImplementation()

    result = implementation.execute(findings_request(implementation, findings))
    document = MarkdownDocument.model_validate(result.artifacts[0].payload)

    assert "### Finding 1: \\# Injected heading" in document.content
    assert "\n## Fake heading" not in document.content
    assert "\\<script\\>" in document.content
    assert "\\!\\[remote\\]" in document.content
    assert "safe\\_call" in document.content
    assert "- **Lines:** 4-8" in document.content
    assert "- **Rule:** unsafe\\.rule" in document.content
    assert document.content.count("### Finding ") == 1


@pytest.mark.parametrize(
    "payload",
    [
        "not structured findings",
        {"findings": "not a list"},
        {"findings": [{"summary": "incomplete"}]},
    ],
)
def test_generate_markdown_rejects_invalid_findings(payload: Any) -> None:
    implementation = GenerateMarkdownImplementation()
    request = CapabilityRequest(
        capability=implementation.capability,
        artifacts=(Artifact(name="engineering_findings", payload=payload),),
    )

    with pytest.raises(ValueError, match="valid EngineeringFindings"):
        implementation.execute(request)


def test_analyze_source_code_output_composes_directly_into_markdown() -> None:
    ollama_findings = {
        "findings": [
            {
                "summary": "Broad exception handler",
                "source_file": "model.py",
                "severity": "medium",
                "confidence": 0.85,
                "category": "reliability",
                "explanation": "The handler obscures unexpected failures.",
                "recommendation": "Catch only the expected exception types.",
            }
        ]
    }

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(ollama_findings),
                },
                "done": True,
            },
        )

    analyzer = AnalyzeSourceCodeOllamaImplementation(
        "test-model",
        client=httpx.Client(
            base_url="http://ollama.test",
            transport=httpx.MockTransport(respond),
        ),
    )
    analysis = analyzer.execute(
        CapabilityRequest(
            capability=analyzer.capability,
            artifacts=(
                Artifact(
                    name="SourceCode",
                    payload={"path": "service.py", "content": "try:\n    work()\n"},
                ),
            ),
        )
    )
    generator = GenerateMarkdownImplementation()

    result = generator.execute(
        CapabilityRequest(
            capability=generator.capability,
            artifacts=analysis.artifacts,
        )
    )

    document = MarkdownDocument.model_validate(result.artifacts[0].payload)
    assert "Broad exception handler" in document.content
    assert "medium" in document.content
    assert "0.85" in document.content
    assert "Catch only the expected exception types" in document.content
    assert "github" not in document.content.lower()


def test_source_context_survives_analysis_aggregation_and_rendering() -> None:
    response_findings = {
        "findings": [
            {
                "summary": "Unchecked result",
                "source_file": "untrusted-model-value.py",
                "start_line": 7,
                "end_line": 9,
                "rule_id": "reliability.unchecked-result",
                "severity": "high",
                "confidence": 0.9,
                "category": "reliability",
                "explanation": "The result is used without checking for failure.",
                "recommendation": "Check the result before using its value.",
            }
        ]
    }

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(response_findings),
                },
                "done": True,
            },
        )

    analyzer = AnalyzeSourceCodeOllamaImplementation(
        "test-model",
        client=httpx.Client(
            base_url="http://ollama.test",
            transport=httpx.MockTransport(respond),
        ),
    )
    analyzed = analyzer.execute(
        CapabilityRequest(
            capability=analyzer.capability,
            artifacts=(
                Artifact(
                    name="SourceCode",
                    payload={"path": "src/service.py", "content": "result = work()\n"},
                ),
            ),
        )
    )
    merger = MergeEngineeringFindingsImplementation()
    merged = merger.execute(
        CapabilityRequest(
            capability=merger.capability,
            artifacts=(
                Artifact(
                    name="engineering_findings",
                    payload=[analyzed.artifacts[0].payload],
                ),
            ),
        )
    )
    generator = GenerateMarkdownImplementation()
    rendered = generator.execute(
        CapabilityRequest(
            capability=generator.capability,
            artifacts=merged.artifacts,
        )
    )

    finding = EngineeringFindings.model_validate(
        merged.artifacts[0].payload
    ).findings[0]
    assert finding.source_file == "src/service.py"
    assert finding.start_line == 7
    assert finding.end_line == 9
    assert finding.rule_id == "reliability.unchecked-result"
    markdown = MarkdownDocument.model_validate(rendered.artifacts[0].payload).content
    assert "- **Source:** src/service\\.py" in markdown
    assert "- **Lines:** 7-9" in markdown
    assert "- **Rule:** reliability\\.unchecked\\-result" in markdown
