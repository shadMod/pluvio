class PluvioError(Exception):
    """Base exception for pluvio."""


class DataNotAvailableError(PluvioError):
    """Requested a date range is outside the available ERA5 archive."""


class CDSAuthError(PluvioError):
    """CDS credentials missing or invalid."""


class MissingExtraError(PluvioError):
    """An optional dependency is required but not installed."""

    def __init__(self, extra: str, package: str) -> None:
        super().__init__(
            f"Install pluvio[{extra}] to use this feature: pip install pluvio[{extra}]\n"
            f"Missing package: {package}"
        )
