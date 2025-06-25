"""Custom exceptions for the Abyssal Tome project."""


class AbyssalTomeError(Exception):
    """Base class for exceptions in this project."""


class DataProcessingError(AbyssalTomeError):
    """Exception raised for errors in the data processing pipeline."""

    def __init__(self, message: str, underlying_error: Exception | None = None) -> None:
        super().__init__(message)
        self.underlying_error = underlying_error

    def __str__(self) -> str:
        if self.underlying_error:
            return f"{super().__str__()} (Caused by: {self.underlying_error})"
        return super().__str__()


class AIEnrichmentError(AbyssalTomeError):
    """Exception raised for errors during AI enrichment steps."""


class ConfigurationError(AbyssalTomeError):
    """Exception raised for configuration-related problems."""


class ScraperError(AbyssalTomeError):
    """Exception raised for errors during scraping."""
