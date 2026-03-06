import requests

from .base import BaseProvider, ProviderError

_BASE_URL = "https://v6.exchangerate-api.com/v6/{key}/latest/{base}"


class ExchangeRateAPIProvider(BaseProvider):
    """
    ExchangeRate-API (exchangerate-api.com) — free tier: 1,500 req/month.

    Supports any base currency.  Requires a free API key (no credit card).
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ExchangeRateAPIProvider requires an API key")
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "ExchangeRate-API"

    @classmethod
    def requires_api_key(cls) -> bool:
        return True

    def get_rates(self, base: str) -> dict:
        url = _BASE_URL.format(key=self._api_key, base=base.upper())
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise ProviderError(f"ExchangeRate-API request failed: {exc}") from exc
        except ValueError as exc:
            raise ProviderError(f"ExchangeRate-API JSON parse error: {exc}") from exc

        if data.get("result") != "success":
            raise ProviderError(
                f"ExchangeRate-API error: {data.get('error-type', 'unknown')}"
            )

        rates = data.get("conversion_rates", {})
        if not rates:
            raise ProviderError("ExchangeRate-API returned empty rates")

        return {
            code.upper(): float(rate)
            for code, rate in rates.items()
            if code.upper() != base.upper()
        }
