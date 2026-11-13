class ProviderUnavailable(RuntimeError):
    """Sanitized provider failure; never expose remote bodies or credentials."""
