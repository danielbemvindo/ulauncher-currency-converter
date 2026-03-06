import time

from cache import CacheManager
from formatter import CurrencyFormatter
from provider_chain import ProviderChain, CryptoProviderChain, AllProvidersFailedError


class ConversionResult:
    """Holds everything needed to render a conversion result item."""

    __slots__ = (
        "amount", "from_cc", "to_cc",
        "converted", "provider_name",
        "timestamp", "is_stale",
    )

    def __init__(
        self,
        amount: float,
        from_cc: str,
        to_cc: str,
        converted: float,
        provider_name: str,
        timestamp: float,
        is_stale: bool = False,
    ):
        self.amount = amount
        self.from_cc = from_cc
        self.to_cc = to_cc
        self.converted = converted
        self.provider_name = provider_name
        self.timestamp = timestamp
        self.is_stale = is_stale

    def age_label(self) -> str:
        """Human-readable string for how old the data is."""
        seconds = time.time() - self.timestamp
        if seconds < 90:
            return "just now"
        if seconds < 3600:
            return f"{int(seconds // 60)} min ago"
        if seconds < 86400:
            return f"{int(seconds // 3600)}h ago"
        return f"{int(seconds // 86400)}d ago"


class ConversionError(Exception):
    """Raised when a conversion cannot be completed."""


class CurrencyConverter:
    """
    Fiat currency conversion context.

    Delegates rate fetching to the ProviderChain (which handles fallback).
    Applies cross-rate math when the provider's native base does not match
    the requested from_cc (e.g. ECB returns EUR-based rates but user wants
    USD→BRL).

    Cache look-up flow:
      1. cache.get(ttl)    → fresh hit  → return immediately
      2. cache.get_stale() → stale hit  → return stale result (is_stale=True)
                             and let the caller optionally trigger a refresh
      3. No cache          → fetch live → cache.set() → return fresh result
    """

    def __init__(
        self,
        provider_chain: ProviderChain,
        cache: CacheManager,
        formatter: CurrencyFormatter,
    ):
        self._chain = provider_chain
        self._cache = cache
        self._formatter = formatter

    def convert(
        self,
        amount: float,
        from_cc: str,
        to_cc: str,
        ttl: int,
        provider_key: str,
    ) -> ConversionResult:
        """
        Convert *amount* from *from_cc* to *to_cc*.

        Parameters
        ----------
        ttl:
            Cache TTL in seconds from user preferences.
        provider_key:
            The user's chosen provider ID (e.g. "frankfurter") used as the
            cache key so switching providers invalidates old entries.
        """
        from_upper = from_cc.upper()
        to_upper = to_cc.upper()

        # 1. Try fresh cache.
        cached = self._cache.get(provider_key, from_upper, ttl)
        if cached:
            rate = self._extract_rate(cached["rates"], from_upper, to_upper)
            converted = amount * rate
            return ConversionResult(
                amount=amount,
                from_cc=from_upper,
                to_cc=to_upper,
                converted=converted,
                provider_name=cached.get("provider", provider_key),
                timestamp=cached["timestamp"],
                is_stale=False,
            )

        # 2. Try stale cache (return immediately; caller may background-refresh).
        stale = self._cache.get_stale(from_upper)
        if stale:
            try:
                rate = self._extract_rate(stale["rates"], from_upper, to_upper)
                converted = amount * rate
                return ConversionResult(
                    amount=amount,
                    from_cc=from_upper,
                    to_cc=to_upper,
                    converted=converted,
                    provider_name=stale.get("provider", provider_key),
                    timestamp=stale["timestamp"],
                    is_stale=True,
                )
            except ConversionError:
                pass  # Stale cache doesn't have the pair; fall through to live fetch.

        # 3. Live fetch via provider chain.
        try:
            rates, provider_name = self._chain.get_rates(from_upper)
        except AllProvidersFailedError as exc:
            # Last resort: return stale data from any base if available.
            if stale and stale.get("rates"):
                try:
                    rate = self._extract_rate(
                        stale["rates"], from_upper, to_upper,
                        stale_base=stale.get("base", "").upper(),
                    )
                    converted = amount * rate
                    return ConversionResult(
                        amount=amount,
                        from_cc=from_upper,
                        to_cc=to_upper,
                        converted=converted,
                        provider_name=stale.get("provider", "cache"),
                        timestamp=stale["timestamp"],
                        is_stale=True,
                    )
                except ConversionError:
                    pass
            raise ConversionError(str(exc)) from exc

        self._cache.set(provider_key, from_upper, rates)
        rate = self._extract_rate(rates, from_upper, to_upper)
        converted = amount * rate
        return ConversionResult(
            amount=amount,
            from_cc=from_upper,
            to_cc=to_upper,
            converted=converted,
            provider_name=provider_name,
            timestamp=time.time(),
            is_stale=False,
        )

    @property
    def formatter(self) -> CurrencyFormatter:
        return self._formatter

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_rate(
        rates: dict,
        from_cc: str,
        to_cc: str,
        stale_base: str | None = None,
    ) -> float:
        """
        Extract the rate for *from_cc* → *to_cc* from a rates dict.

        The dict is assumed to be keyed relative to *from_cc* (i.e. the
        provider was queried with base=from_cc).  If the provider returned
        a different base (stale_base), apply cross-rate math.
        """
        if from_cc == to_cc:
            return 1.0

        # Normal case: rates are from_cc-based.
        if stale_base is None or stale_base == from_cc:
            if to_cc not in rates:
                raise ConversionError(
                    f"Currency {to_cc} not available in current rate set"
                )
            return rates[to_cc]

        # Cross-rate from a different base.
        base = stale_base
        from_rate = 1.0 if from_cc == base else rates.get(from_cc)
        to_rate = 1.0 if to_cc == base else rates.get(to_cc)
        if from_rate is None or to_rate is None:
            raise ConversionError(
                f"Cannot compute cross-rate {from_cc}→{to_cc} from base {base}"
            )
        return to_rate / from_rate


class CryptoConverter:
    """
    Cryptocurrency → fiat (or fiat → crypto) conversion context.

    Delegates to CryptoProviderChain.  No caching (crypto prices are highly
    volatile; the fiat provider's cache is irrelevant here).
    """

    def __init__(
        self,
        provider_chain: CryptoProviderChain,
        fiat_converter: CurrencyConverter,
        formatter: CurrencyFormatter,
    ):
        self._chain = provider_chain
        self._fiat = fiat_converter
        self._formatter = formatter

    def convert(
        self,
        amount: float,
        from_cc: str,
        to_cc: str,
        ttl: int,
        fiat_provider_key: str,
    ) -> ConversionResult:
        """
        Convert *amount* from *from_cc* to *to_cc* where at least one is crypto.

        Handles:
          crypto → fiat   (e.g. 1 BTC → USD)
          fiat → crypto   (e.g. 1000 USD → BTC)
          crypto → crypto (not supported; raise ConversionError)
        """
        from_upper = from_cc.upper()
        to_upper = to_cc.upper()

        # Fiat → crypto: invert the crypto→fiat price.
        if self._is_crypto(to_upper) and not self._is_crypto(from_upper):
            price, pname = self._chain.get_price_in_fiat(to_upper, from_upper)
            converted = amount / price
            return ConversionResult(
                amount=amount,
                from_cc=from_upper,
                to_cc=to_upper,
                converted=converted,
                provider_name=pname,
                timestamp=time.time(),
            )

        # Crypto → fiat.
        if self._is_crypto(from_upper):
            try:
                price, pname = self._chain.get_price_in_fiat(from_upper, to_upper)
                converted = amount * price
                return ConversionResult(
                    amount=amount,
                    from_cc=from_upper,
                    to_cc=to_upper,
                    converted=converted,
                    provider_name=pname,
                    timestamp=time.time(),
                )
            except AllProvidersFailedError:
                # Fallback: get crypto price in USD, then fiat-convert USD→to_cc.
                price_usd, pname = self._chain.get_price_in_fiat(from_upper, "USD")
                fiat_result = self._fiat.convert(
                    price_usd * amount, "USD", to_upper, ttl, fiat_provider_key
                )
                fiat_result.from_cc = from_upper
                fiat_result.provider_name = f"{pname} + {fiat_result.provider_name}"
                return fiat_result

        raise ConversionError("crypto→crypto conversions are not supported")

    @property
    def formatter(self) -> CurrencyFormatter:
        return self._formatter

    def _is_crypto(self, code: str) -> bool:
        # Determined externally; inject via constructor or set directly.
        return code in (self._crypto_codes if hasattr(self, "_crypto_codes") else set())

    def set_crypto_codes(self, codes: set[str]) -> None:
        self._crypto_codes = codes
