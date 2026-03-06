from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a provider fails to return usable data."""


class BaseProvider(ABC):
    """
    Abstract base class for all fiat currency rate providers.

    Each concrete subclass encapsulates one exchange-rate source and must
    implement get_rates().  The ProviderChain calls providers in order and
    stops at the first success.

    Cross-rate note: providers whose base is locked (ECB → EUR, OXR → USD)
    return raw rates against that fixed base.  CurrencyConverter performs the
    cross-rate division when the requested base differs.
    """

    # --- abstract interface --------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name shown in result descriptions."""

    @abstractmethod
    def get_rates(self, base: str) -> dict:
        """
        Fetch exchange rates relative to *base* currency code.

        Returns a dict mapping uppercase currency codes to float rates, e.g.:
            {"EUR": 0.91, "BRL": 4.97, "JPY": 148.5}

        The base currency itself is NOT included in the returned dict.

        Raises ProviderError on any network or parse failure so that
        ProviderChain can fall through to the next provider.
        """

    # --- optional / overridable ---------------------------------------------

    def supports_base(self, base: str) -> bool:
        """
        Return True if this provider can use *base* as the reference currency.

        ECBProvider and OpenExchangeRatesProvider override this to return
        False for any currency other than EUR or USD respectively.  The
        converter then applies cross-rate math instead of requesting a
        non-supported base directly.
        """
        return True

    @classmethod
    def requires_api_key(cls) -> bool:
        """Return True for providers that need an API key in preferences."""
        return False
