import requests

from .base import BaseProvider, ProviderError

_BASE_URL = "https://api.frankfurter.dev/v1"


class FrankfurterProvider(BaseProvider):
    """
    Frankfurter (api.frankfurter.dev) — free, no API key.

    Backed by ECB reference rates; supports any of its 31 currencies as base.
    Rates update daily around 16:00 CET on ECB business days.
    """

    @property
    def name(self) -> str:
        return "Frankfurter"

    def get_rates(self, base: str) -> dict:
        url = f"{_BASE_URL}/latest"
        try:
            resp = requests.get(url, params={"base": base.upper()}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise ProviderError(f"Frankfurter request failed: {exc}") from exc
        except ValueError as exc:
            raise ProviderError(f"Frankfurter JSON parse error: {exc}") from exc

        rates = data.get("rates")
        if not isinstance(rates, dict) or not rates:
            raise ProviderError("Frankfurter returned empty rates")

        return {code.upper(): float(rate) for code, rate in rates.items()}
