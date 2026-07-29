"""Ollama implementation of the provider-neutral AnalyzeSourceCode Capability."""

from typing import Any

import httpx
from pydantic import ValidationError

from app.capabilities import (
    Artifact,
    ArtifactDefinition,
    Capability,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
)
from app.capabilities.findings import EngineeringFindings

ANALYZE_SOURCE_CODE = Capability(
    name="AnalyzeSourceCode",
    description="Analyze source code and produce provider-neutral engineering findings.",
    category=CapabilityCategory.ANALYSIS,
    contract="AnalyzeSourceCode",
    version="1",
    input_artifacts=(
        ArtifactDefinition(
            name="SourceCode", description="Source path and UTF-8 text content."
        ),
    ),
    output_artifacts=(
        ArtifactDefinition(
            name="engineering_findings",
            description="Structured, provider-neutral engineering findings.",
        ),
    ),
    tags=("analysis", "source-code", "engineering-intelligence"),
)


class OllamaAnalysisError(Exception):
    """Raised when Ollama cannot produce valid EngineeringFindings."""


class AnalyzeSourceCodeOllamaImplementation:
    """Generate structured engineering findings through Ollama."""

    def __init__(
        self,
        model: str,
        *,
        client: httpx.Client | None = None,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ) -> None:
        if not model.strip():
            raise ValueError("Ollama model must be a non-empty string")
        self._model = model
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def capability(self) -> Capability:
        return ANALYZE_SOURCE_CODE

    def execute(self, request: CapabilityRequest) -> CapabilityResult:
        source_file, source = self._source_code(request.artifact("SourceCode"))
        response = self._chat(self._request_body(source_file, source))
        findings = self._parse_findings(response)
        contextualized = EngineeringFindings(
            findings=tuple(
                finding.model_copy(update={"source_file": source_file})
                for finding in findings.findings
            )
        )
        return CapabilityResult(
            artifacts=(
                Artifact(
                    name="engineering_findings",
                    payload=contextualized.model_dump(mode="json"),
                ),
            )
        )

    def _chat(self, body: dict[str, Any]) -> httpx.Response:
        try:
            if self._client is not None:
                response = self._client.post("/api/chat", json=body)
            else:
                response = httpx.post(
                    f"{self._base_url}/api/chat",
                    json=body,
                    timeout=self._timeout,
                )
            response.raise_for_status()
            return response
        except httpx.HTTPError as error:
            raise OllamaAnalysisError(f"Ollama request failed: {error}") from error

    def _request_body(self, source_file: str, source: str) -> dict[str, Any]:
        schema = EngineeringFindings.model_json_schema()
        return {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Analyze source code as a software engineer. Return only "
                        "structured engineering findings matching the supplied schema. "
                        "Do not generate Markdown or presentation content."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Analyze this source code for correctness, maintainability, "
                        "security, reliability, and design concerns. Set source_file "
                        f"to {source_file!r} for every finding.\n\n{source}"
                    ),
                },
            ],
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
        }

    @staticmethod
    def _source_code(artifact: Artifact) -> tuple[str, str]:
        payload = artifact.payload
        if not isinstance(payload, dict):
            raise ValueError("SourceCode artifact must contain a mapping")
        content = payload.get("content")
        if not isinstance(content, str):
            raise ValueError("SourceCode artifact content must be a string")
        source_file = payload.get("path")
        if not isinstance(source_file, str) or not source_file:
            raise ValueError("SourceCode artifact path must be a non-empty string")
        return source_file, content

    @staticmethod
    def _parse_findings(response: httpx.Response) -> EngineeringFindings:
        try:
            payload = response.json()
            message = payload["message"]
            content = message["content"]
            if not isinstance(content, str):
                raise TypeError("message content is not a string")
            return EngineeringFindings.model_validate_json(content)
        except (
            KeyError,
            TypeError,
            ValueError,
            ValidationError,
        ) as error:
            raise OllamaAnalysisError(
                "Ollama response did not contain valid EngineeringFindings"
            ) from error
