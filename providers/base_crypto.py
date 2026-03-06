from abc import ABC, abstractmethod


class CryptoProviderError(Exception):
    """Raised when a crypto provider fails to return usable data."""


class BaseCryptoProvider(ABC):
    """
    Abstract base class for cryptocurrency price providers.

    Crypto providers return a single price: how much one unit of
    *crypto_code* costs in *fiat_code*.  The concrete subclass handles
    all API-specific quirks (symbol mapping, response parsing, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    @abstractmethod
    def get_price_in_fiat(self, crypto_code: str, fiat_code: str) -> float:
        """
        Return the current price of one unit of *crypto_code* in *fiat_code*.

        Example: get_price_in_fiat("BTC", "USD") → 84327.15

        Raises CryptoProviderError on any network or parse failure.
        """

    @classmethod
    def requires_api_key(cls) -> bool:
        return False
