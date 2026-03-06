import xml.etree.ElementTree as ET

import requests

from .base import BaseProvider, ProviderError

_FEED_URL = (
    "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
)
_NS = "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"

# ECB only publishes rates vs EUR.
_FIXED_BASE = "EUR"


class ECBProvider(BaseProvider):
    """
    European Central Bank daily XML feed — free, no API key.

    Base is always EUR.  CurrencyConverter applies cross-rate math when the
    requested base is a different currency:
        rate(from→to) = eur_rates[to] / eur_rates[from]

    Covers 30 currencies; updates once per ECB business day ~16:00 CET.
    """

    @property
    def name(self) -> str:
        return "European Central Bank"

    def supports_base(self, base: str) -> bool:
        # Native base is EUR; cross-rate is handled externally.
        return base.upper() == _FIXED_BASE

    def get_rates(self, base: str) -> dict:
        """
        Always fetches EUR-based rates from ECB.

        If base != "EUR" the caller (CurrencyConverter / ProviderChain) must
        apply the cross-rate conversion.  We return EUR-based rates regardless
        so the chain can decide what to do with them.
        """
        try:
            resp = requests.get(_FEED_URL, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except requests.RequestException as exc:
            raise ProviderError(f"ECB request failed: {exc}") from exc
        except ET.ParseError as exc:
            raise ProviderError(f"ECB XML parse error: {exc}") from exc

        rates: dict[str, float] = {}
        for cube in root.iter(f"{{{_NS}}}Cube"):
            currency = cube.get("currency")
            rate = cube.get("rate")
            if currency and rate:
                try:
                    rates[currency.upper()] = float(rate)
                except ValueError:
                    pass

        if not rates:
            raise ProviderError("ECB feed contained no rate data")

        # If caller requested EUR base, return as-is.
        if base.upper() == _FIXED_BASE:
            return rates

        # Cross-rate: convert EUR-based rates to requested base.
        if base.upper() not in rates:
            raise ProviderError(
                f"ECB does not publish {base}/EUR rate; cross-rate impossible"
            )
        base_rate = rates[base.upper()]
        result = {code: r / base_rate for code, r in rates.items() if code != base.upper()}
        result[_FIXED_BASE] = 1.0 / base_rate
        return result
