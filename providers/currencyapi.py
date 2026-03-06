import requests

from .base import BaseProvider, ProviderError

_BASE_URL = "https://api.currencyapi.com/v3/latest"


class CurrencyAPIProvider(BaseProvider):
    """
    CurrencyAPI (currencyapi.com) — free tier: 300 req/month.

    Supports any base currency and 170+ currencies.  Requires a free API key.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("CurrencyAPIProvider requires an API key")
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "CurrencyAPI"

    @classmethod
    def requires_api_key(cls) -> bool:
        return True

    def get_rates(self, base: str) -> dict:
        try:
            resp = requests.get(
                _BASE_URL,
                params={"apikey": self._api_key, "base_currency": base.upper()},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise ProviderError(f"CurrencyAPI request failed: {exc}") from exc
        except ValueError as exc:
            raise ProviderError(f"CurrencyAPI JSON parse error: {exc}") from exc

        if "errors" in data:
            raise ProviderError(f"CurrencyAPI error: {data['errors']}")

        raw = data.get("data", {})
        if not raw:
            raise ProviderError("CurrencyAPI returned empty data")

        # Response: {"data": {"EUR": {"code": "EUR", "value": 0.91}, ...}}
        return {
            code.upper(): float(entry["value"])
            for code, entry in raw.items()
            if code.upper() != base.upper()
        }
