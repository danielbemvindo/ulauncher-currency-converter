import requests

from .base import BaseProvider, ProviderError

# Primary CDN; fallback used if primary fails within the same request attempt.
_PRIMARY_URL = (
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json"
)
_FALLBACK_URL = (
    "https://latest.currency-api.pages.dev/v1/currencies/{base}.json"
)


class FawazProvider(BaseProvider):
    """
    Fawaz Exchange API — free, no API key, CDN-hosted.

    Covers 200+ currencies including some crypto.  Currency codes are
    lowercase in the API response; this class normalises them to uppercase.
    """

    @property
    def name(self) -> str:
        return "Fawaz Exchange API"

    def get_rates(self, base: str) -> dict:
        base_lower = base.lower()
        data = self._fetch(base_lower)

        raw_rates = data.get(base_lower)
        if not isinstance(raw_rates, dict) or not raw_rates:
            raise ProviderError(f"Fawaz returned empty rates for base {base}")

        return {
            code.upper(): float(rate)
            for code, rate in raw_rates.items()
            if code.upper() != base.upper()
        }

    def _fetch(self, base_lower: str) -> dict:
        for url_template in (_PRIMARY_URL, _FALLBACK_URL):
            url = url_template.format(base=base_lower)
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException:
                continue
            except ValueError:
                continue
        raise ProviderError("Fawaz: both CDN endpoints failed")
