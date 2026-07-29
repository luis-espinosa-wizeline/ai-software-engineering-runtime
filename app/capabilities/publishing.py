"""Provider-neutral Engineering Delivery domain and provider boundary."""

from typing import Protocol

from pydantic import model_validator

from app.capabilities.documents import MarkdownDocument
from app.shared import DomainModel


class PublicationResult(DomainModel):
    """Provider-neutral outcome of delivering an engineering document."""

    success: bool
    publication_id: str | None = None
    destination: str

    @model_validator(mode="after")
    def _validate_result(self) -> PublicationResult:
        if not self.destination.strip():
            raise ValueError("Publication destination must not be blank")
        if self.success and (
            self.publication_id is None or not self.publication_id.strip()
        ):
            raise ValueError("Successful publication requires an identifier")
        if self.publication_id is not None and not self.publication_id.strip():
            raise ValueError("Publication identifier must not be blank")
        return self


class PublicationError(Exception):
    """Base error for explicit Engineering Delivery failures."""


class PublicationAuthenticationError(PublicationError):
    """Raised when a publisher cannot authenticate."""


class PublicationAccessDenied(PublicationError):
    """Raised when a publisher cannot access the destination."""


class PublicationDestinationNotFound(PublicationError):
    """Raised when a publication destination does not exist."""


class PublicationTransportError(PublicationError):
    """Raised when a publisher cannot communicate with its destination."""


class InvalidPublicationResponse(PublicationError):
    """Raised when a publisher returns an unusable success response."""


class EngineeringPublisher(Protocol):
    """Deliver an immutable engineering document without changing it."""

    def publish(self, document: MarkdownDocument) -> PublicationResult:
        """Publish exactly one document and return a provider-neutral result."""
        ...
