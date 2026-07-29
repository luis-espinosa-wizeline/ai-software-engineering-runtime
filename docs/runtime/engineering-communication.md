# Engineering Communication

Engineering Communication transforms structured engineering knowledge into
human-readable representations. It does not analyze source code or publish the
result.

```text
EngineeringFindings
        |
        v
GenerateMarkdown
        |
        v
MarkdownDocument
```

`EngineeringFindings` remains the source of truth. Markdown is one deterministic
representation that can be consumed by engineers or passed to a later
publishing Capability. Other representations can be added without changing
analysis.

## GenerateMarkdown

`GenerateMarkdown` is a provider-neutral Transformation Capability:

- input artifact: `engineering_findings`, containing a validated
  `EngineeringFindings` value;
- output artifact: `markdown`, containing a `MarkdownDocument`; and
- implementation: `GenerateMarkdownImplementation`.

`MarkdownDocument` contains one required `content` string. It deliberately has
no repository, pull-request, GitHub comment, destination, or publication
metadata.

The implementation is a pure deterministic renderer. It performs no network
access, invokes no model, creates no findings, changes no severity or
confidence, and adds no recommendations. It preserves the input order and emits
one section for every finding.

An empty findings collection renders as:

```markdown
## Engineering Analysis

No engineering findings were identified.
```

## Rendering and safety

Each finding section includes its summary, source file, severity, confidence,
category, explanation, and recommendation. Optional line ranges and rule
identifiers are rendered when present. Inline fields remain inside their
assigned heading or list item. Markdown control characters in finding content
are escaped, including controls that could introduce headings, links, images,
raw HTML, emphasis, or list structure. Multiline explanation and recommendation
text retains its line order.

Escaping affects representation only; the renderer does not reinterpret the
finding. Severity and confidence are rendered from their validated domain
values, and findings are never sorted.

## Composition

The artifact refinement pipeline is:

```text
Raw file
   |
   v
SourceCode
   |
   v
AnalyzeSourceCode
   |
   v
engineering_findings
   |
   v
GenerateMarkdown
   |
   v
markdown
```

The `markdown` artifact payload is:

```json
{
  "content": "## Engineering Analysis\n..."
}
```

`PublishGitHubComment` or another delivery Capability can consume this artifact.
Publishing remains outside Engineering Communication; see
[Engineering Delivery](engineering-delivery.md).
