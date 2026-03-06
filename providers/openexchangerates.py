import requests

from .base import BaseProvider, ProviderError

_BASE_URL = "https://openexchangerates.org/api/latest.json"
_FIXED_BASE = "USD"


class OpenExchangeRatesProvider(BaseProvider):
    """
    Open Exchange Rates (openexchangerates.org) — free tier: 1,000 req/month.

    On the free plan the base is locked to USD.  Cross-rate math is applied
    here for non-USD bases.  Covers 170+ currencies.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenExchangeRatesProvider requires an API key")
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "Open Exchange Rates"

    @classmethod
    def requires_api_key(cls) -> bool:
        return True

    def supports_base(self, base: str) -> bool:
        return base.upper() == _FIXED_BASE

    def get_rates(self, base: str) -> dict:
        try:
            resp = requests.get(
                _BASE_URL, params={"app_id": self._api_key}, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise ProviderError(f"Open Exchange Rates request failed: {exc}") from exc
        except ValueError as exc:
            raise ProviderError(f"Open Exchange Rates JSON parse error: {exc}") from exc

        if "error" in data:
            raise ProviderError(
                f"Open Exchange Rates API error: {data.get('description', data['error'])}"
            )

        usd_rates: dict[str, float] = {
            code.upper(): float(rate)
            for code, rate in data.get("rates", {}).items()
        }
        if not usd_rates:
            raise ProviderError("Open Exchange Rates returned empty rates")

        if base.upper() == _FIXED_BASE:
            usd_rates.pop("USD", None)
            return usd_rates

        # Cross-rate: convert USD-based rates to requested base.
        if base.upper() not in usd_rates:
            raise ProviderError(
                f"Open Exchange Rates does not include {base}; cross-rate impossible"
            )
        base_rate = usd_rates[base.upper()]
        result = {
            code: r / base_rate
            for code, r in usd_rates.items()
            if code != base.upper()
        }
        result[_FIXED_BASE] = 1.0 / base_rate
        return result
