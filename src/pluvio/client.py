from __future__ import annotations

import os

import cdsapi

from pluvio.constants import _CDS_DEFAULT_URL
from pluvio.exceptions import CDSAuthError


class PluvioClient:
    """Thin wrapper around cdsapi.Client with explicit credential handling.

    Credentials priority:
      1. Constructor arguments (url, key)
      2. Environment variables CDS_URL / CDS_KEY
      3. ~/.cdsapirc (cdsapi default)
    """

    def __init__(self, url: str | None = None, key: str | None = None) -> None:
        resolved_url = url or os.getenv("CDS_URL", _CDS_DEFAULT_URL)
        resolved_key = key or os.getenv("CDS_KEY")

        try:
            if resolved_key:
                self._client = cdsapi.Client(url=resolved_url, key=resolved_key, quiet=True)
            else:
                self._client = cdsapi.Client(quiet=True)
        except Exception as exc:
            raise CDSAuthError(
                "Could not initialise CDS client. Set CDS_KEY env var or create ~/.cdsapirc."
            ) from exc

    @property
    def raw(self) -> cdsapi.Client:
        return self._client
