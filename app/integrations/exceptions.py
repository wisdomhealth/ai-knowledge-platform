class IntegrationError(RuntimeError):
    """Base integration error."""


class IntegrationNotConfigured(IntegrationError):
    """Raised when an optional provider is missing required configuration."""
