class IntegrationError(RuntimeError):
    """Base integration error."""


class IntegrationNotConfigured(IntegrationError):
    """Raised when an optional provider is missing required configuration."""


class IndexIncompatible(IntegrationError):
    """Stored embeddings cannot safely be used with the configured model."""


class ToolNotFound(ValueError):
    """Requested tool is not registered."""
