import logging

from providers.base import BaseProvider, ProviderError
from providers.base_crypto import BaseCryptoProvider, CryptoProviderError

logger = logging.getLogger(__name__)


class AllProvidersFailedError(Exception):
    """Raised when every provider in a chain has failed."""


class ProviderChain:
    """
    Tries a list of fiat providers in order with a 10-second timeout each.

    Returns the first successful (rates_dict, provider_name) pair.
    Raises AllProvidersFailedError if every provider fails.

    The timeout is enforced at the HTTP level by passing timeout=10 to
    requests.get() inside each provider — there is no separate thread.
    """

    def __init__(self, providers: list[BaseProvider]):
        if not providers:
            raise ValueError("ProviderChain requires at least one provider")
        self._providers = providers

    def get_rates(self, base: str) -> tuple[dict, str]:
        """
        Attempt each provider in order.

        Returns:
            (rates_dict, provider_name_that_succeeded)

        Raises:
            AllProvidersFailedError
        """
        errors: list[str] = []
        for provider in self._providers:
            try:
                rates = provider.get_rates(base)
                logger.debug("ProviderChain: %s succeeded for base=%s", provider.name, base)
                return rates, provider.name
            except ProviderError as exc:
                logger.warning("ProviderChain: %s failed: %s", provider.name, exc)
                errors.append(f"{provider.name}: {exc}")

        raise AllProvidersFailedError(
            "All fiat providers failed:\n" + "\n".join(errors)
        )


class CryptoProviderChain:
    """
    Same pattern as ProviderChain but for BaseCryptoProvider instances.
    """

    def __init__(self, providers: list[BaseCryptoProvider]):
        if not providers:
            raise ValueError("CryptoProviderChain requires at least one provider")
        self._providers = providers

    def get_price_in_fiat(self, crypto_code: str, fiat_code: str) -> tuple[float, str]:
        """
        Returns:
            (price_float, provider_name_that_succeeded)

        Raises:
            AllProvidersFailedError
        """
        errors: list[str] = []
        for provider in self._providers:
            try:
                price = provider.get_price_in_fiat(crypto_code, fiat_code)
                logger.debug(
                    "CryptoProviderChain: %s succeeded for %s/%s",
                    provider.name, crypto_code, fiat_code,
                )
                return price, provider.name
            except CryptoProviderError as exc:
                logger.warning(
                    "CryptoProviderChain: %s failed: %s", provider.name, exc
                )
                errors.append(f"{provider.name}: {exc}")

        raise AllProvidersFailedError(
            f"All crypto providers failed for {crypto_code}/{fiat_code}:\n"
            + "\n".join(errors)
        )
