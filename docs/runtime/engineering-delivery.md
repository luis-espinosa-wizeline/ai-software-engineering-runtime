# Engineering Delivery

Engineering Delivery sends a final Engineering Document to an external
engineering system. It does not create, analyze, enrich, reorder, or reformat
engineering knowledge.

```text
MarkdownDocument
        |
        v
PublishGitHubComment
        |
        v
publication_result
```

The Markdown document is final when it reaches Delivery. The publisher sends its
`content` exactly as received, including whitespace, and publishes exactly one
document per invocation.

## Provider-neutral boundary

`EngineeringPublisher` is the infrastructure boundary owned by the Capability
ecosystem:

```text
PublishGitHubCommentImplementation
        |
        v
EngineeringPublisher
        |
        v
GitHubCommentPublisher
        |
        v
GitHub API
```

The Capability Implementation depends only on `EngineeringPublisher.publish`.
Repository targeting, pull-request number, authentication token, HTTP headers,
API path, and transport belong to `GitHubCommentPublisher` construction and
behavior. None appears in the Capability request, Markdown artifact, execution
plan, context, resolver, or Runtime.

No reusable GitHub client or authentication implementation existed before this
epic. The adapter therefore contains the minimum token-based HTTP interaction
needed to create one pull-request comment; it does not introduce a general
GitHub SDK or authentication framework.

The adapter uses GitHub's documented
[issue-comment endpoint](https://docs.github.com/en/rest/issues/comments),
because pull-request conversation comments use that REST resource. It sends the
recommended media type and an explicit, supported
[REST API version](https://docs.github.com/en/rest/about-the-rest-api/api-versions).

## Contracts

`PublishGitHubComment` declares:

- input artifact: `markdown`, containing an immutable `MarkdownDocument`;
- output artifact: `publication_result`, containing `PublicationResult`;
- category: `publishing`; and
- contract: `PublishGitHubComment`.

`PublicationResult` contains:

- `success`;
- optional `publication_id`; and
- `destination`.

Successful results require a publication identifier. The model intentionally
contains no raw HTTP response, token, repository, pull-request payload, or
provider SDK object. A provider may return an unsuccessful result when it can
represent that outcome normally.

Explicit failures use delivery-domain errors:

- `PublicationAuthenticationError`;
- `PublicationAccessDenied`;
- `PublicationDestinationNotFound`;
- `PublicationTransportError`; and
- `InvalidPublicationResponse`.

The GitHub adapter maps HTTP and transport behavior into these errors so
transport details do not enter Runtime contracts.

## Complete refinement pipeline

```text
ReadFile
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
   |
   v
PublishGitHubComment
   |
   v
publication_result
```

Future publishers can implement `EngineeringPublisher` and consume the same
immutable `MarkdownDocument`. Slack, Jira, email, GitLab, dashboard, or other
delivery destinations require no change to Intelligence, Communication, or the
Runtime.
