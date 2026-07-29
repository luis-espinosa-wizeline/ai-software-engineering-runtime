import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.capabilities import Artifact, CapabilityRequest
from app.capabilities.analyze_source_code import (
    AnalyzeSourceCodeOllamaImplementation,
    EngineeringFinding,
    EngineeringFindings,
    FindingSeverity,
)
from app.capabilities.analyze_source_code.implementation import OllamaAnalysisError
from app.capabilities.read_file import ReadFileImplementation


def ollama_client(
    content: dict[str, Any],
    observed_requests: list[dict[str, Any]] | None = None,
) -> httpx.Client:
    def respond(request: httpx.Request) -> httpx.Response:
        if observed_requests is not None:
            observed_requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "test-code-model",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(content),
                },
                "done": True,
            },
        )

    return httpx.Client(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(respond),
    )


def source_request(
    implementation: AnalyzeSourceCodeOllamaImplementation,
    source: Artifact,
) -> CapabilityRequest:
    return CapabilityRequest(
        capability=implementation.capability,
        artifacts=(source,),
    )


def valid_findings() -> dict[str, Any]:
    return {
        "findings": [
            {
                "summary": "Unbounded retry loop",
                "source_file": "model-supplied.py",
                "start_line": 10,
                "end_line": 12,
                "rule_id": "reliability.unbounded-retry",
                "severity": "high",
                "confidence": 0.91,
                "category": "reliability",
                "explanation": "The loop retries without a termination condition.",
                "recommendation": "Add a maximum attempt count and surface failure.",
            }
        ]
    }


def test_engineering_findings_are_structured_and_provider_neutral() -> None:
    findings = EngineeringFindings(
        findings=(
            EngineeringFinding(
                summary="Unsafe command construction",
                source_file="commands.py",
                start_line=20,
                end_line=21,
                rule_id="security.shell-injection",
                severity=FindingSeverity.CRITICAL,
                confidence=0.98,
                category="security",
                explanation="User input is interpolated into a shell command.",
                recommendation="Pass arguments without invoking a shell.",
            ),
        )
    )

    assert findings.findings[0].severity is FindingSeverity.CRITICAL
    assert "markdown" not in findings.model_dump()
    assert "github" not in findings.model_dump()
    with pytest.raises(ValidationError):
        EngineeringFinding(
            summary="Invalid confidence",
            source_file="service.py",
            severity=FindingSeverity.LOW,
            confidence=1.1,
            category="quality",
            explanation="Invalid.",
            recommendation="Invalid.",
        )


@pytest.mark.parametrize(
    ("context", "message"),
    [
        ({"source_file": " "}, "source_file"),
        ({"source_file": "service.py", "start_line": 0}, "start_line"),
        ({"source_file": "service.py", "end_line": 4}, "requires start_line"),
        (
            {"source_file": "service.py", "start_line": 5, "end_line": 4},
            "precede start_line",
        ),
        ({"source_file": "service.py", "rule_id": " "}, "rule_id"),
    ],
)
def test_engineering_finding_rejects_invalid_source_context(
    context: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        EngineeringFinding(
            summary="Finding",
            severity=FindingSeverity.LOW,
            confidence=0.5,
            category="quality",
            explanation="Explanation.",
            recommendation="Recommendation.",
            **context,
        )


def test_ollama_implementation_requests_and_validates_structured_output() -> None:
    observed: list[dict[str, Any]] = []
    client = ollama_client(valid_findings(), observed)
    implementation = AnalyzeSourceCodeOllamaImplementation(
        "test-code-model",
        client=client,
    )
    source = Artifact(
        name="SourceCode",
        payload={"path": "service.py", "content": "while True:\n    retry()\n"},
    )

    result = implementation.execute(source_request(implementation, source))

    assert result.artifacts[0].name == "engineering_findings"
    expected = valid_findings()
    expected["findings"][0]["source_file"] = "service.py"
    assert result.artifacts[0].payload == expected
    assert len(observed) == 1
    request = observed[0]
    assert request["model"] == "test-code-model"
    assert request["stream"] is False
    assert request["options"] == {"temperature": 0}
    assert request["format"]["properties"]["findings"]["type"] == "array"
    assert "while True" in request["messages"][1]["content"]
    assert "'service.py'" in request["messages"][1]["content"]
    assert "Markdown" in request["messages"][0]["content"]


def test_read_file_output_composes_with_source_analysis(tmp_path: Path) -> None:
    source_path = tmp_path / "service.py"
    source_path.write_text("def answer():\n    return 42\n", encoding="utf-8")
    read_file = ReadFileImplementation()
    source_result = read_file.execute(
        CapabilityRequest(
            capability=read_file.capability,
            artifacts=(Artifact(name="path", payload=str(source_path)),),
        )
    )
    analyzer = AnalyzeSourceCodeOllamaImplementation(
        "test-code-model",
        client=ollama_client({"findings": []}),
    )

    analysis_result = analyzer.execute(
        source_request(analyzer, source_result.artifacts[0])
    )

    assert source_result.artifacts[0].name == "SourceCode"
    assert analysis_result.artifacts == (
        Artifact(name="engineering_findings", payload={"findings": []}),
    )


@pytest.mark.parametrize(
    "payload",
    [
        "plain source",
        {"path": "service.py"},
        {"content": "pass"},
        {"content": 42},
    ],
)
def test_ollama_implementation_rejects_invalid_source_artifact(payload: Any) -> None:
    implementation = AnalyzeSourceCodeOllamaImplementation(
        "test-code-model",
        client=ollama_client({"findings": []}),
    )

    with pytest.raises(ValueError, match="SourceCode artifact"):
        implementation.execute(
            source_request(
                implementation,
                Artifact(name="SourceCode", payload=payload),
            )
        )


def test_ollama_implementation_rejects_malformed_findings() -> None:
    implementation = AnalyzeSourceCodeOllamaImplementation(
        "test-code-model",
        client=ollama_client(
            {
                "findings": [
                    {
                        "summary": "Missing required fields",
                        "severity": "unknown",
                    }
                ]
            }
        ),
    )

    with pytest.raises(OllamaAnalysisError, match="valid EngineeringFindings"):
        implementation.execute(
            source_request(
                implementation,
                Artifact(
                    name="SourceCode",
                    payload={"path": "service.py", "content": "pass\n"},
                ),
            )
        )


def test_ollama_transport_failures_are_isolated_from_runtime() -> None:
    client = httpx.Client(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, json={"error": "model unavailable"})
        ),
    )
    implementation = AnalyzeSourceCodeOllamaImplementation(
        "test-code-model",
        client=client,
    )

    with pytest.raises(OllamaAnalysisError, match="Ollama request failed"):
        implementation.execute(
            source_request(
                implementation,
                Artifact(
                    name="SourceCode",
                    payload={"path": "service.py", "content": "pass\n"},
                ),
            )
        )
