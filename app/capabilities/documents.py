"""Provider-neutral engineering document values."""

from pydantic import model_validator

from app.shared import DomainModel


class MarkdownDocument(DomainModel):
    """A rendered Markdown document suitable for downstream publishing."""

    content: str

    @model_validator(mode="after")
    def _validate_content(self) -> MarkdownDocument:
        if not self.content.strip():
            raise ValueError("Markdown content must not be blank")
        return self
