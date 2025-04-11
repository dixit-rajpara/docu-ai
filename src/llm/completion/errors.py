class CompletionError(Exception):
    """Base class for completion related errors."""

    pass


class CompletionConfigurationError(CompletionError):
    """Error related to completion client configuration."""

    pass


class CompletionGenerationError(CompletionError):
    """Error during the completion generation process."""

    pass
