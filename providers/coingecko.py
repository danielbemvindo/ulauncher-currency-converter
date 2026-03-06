import requests

from .base_crypto import BaseCryptoProvider, CryptoProviderError

_BASE_URL = "https://api.coingecko.com/api/v3/simple/price"

# Maps our uppercase ticker → CoinGecko coin ID slug.
# Populated from ulauncher-cryptocurrencies.json at build time; hardcoded
# here as a fast lookup to avoid a file read on every query.
_COINGECKO_IDS: dict[str, str] = {
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "USDT": "tether",
    "BNB":  "binancecoin",
    "XRP":  "ripple",
    "USDC": "usd-coin",
    "SOL":  "solana",
    "TRX":  "tron",
    "DOGE": "dogecoin",
    "ADA":  "cardano",
}


class CoinGeckoProvider(BaseCryptoProvider):
    """
    CoinGecko simple/price API — free Demo key optional but recommended.

    Without a key: 5–15 req/min (variable, unreliable).
    With a free Demo key (coingecko.com, no credit card): stable 30 req/min.

    Natively supports 100+ fiat vs_currencies in a single call.
    """

    def __init__(self, api_key: str = ""):
        self._api_key = api_key.strip()

    @property
    def name(self) -> str:
        return "CoinGecko"

    @classmethod
    def requires_api_key(cls) -> bool:
        return False  # Key is optional (but improves stability)

    def get_price_in_fiat(self, crypto_code: str, fiat_code: str) -> float:
        coin_id = _COINGECKO_IDS.get(crypto_code.upper())
        if not coin_id:
            raise CryptoProviderError(
                f"CoinGecko: unknown crypto code '{crypto_code}'"
            )

        params: dict = {
            "ids": coin_id,
            "vs_currencies": fiat_code.lower(),
        }
        headers: dict = {}
        if self._api_key:
            headers["x-cg-demo-api-key"] = self._api_key

        try:
            resp = requests.get(_BASE_URL, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise CryptoProviderError(
                f"CoinGecko request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise CryptoProviderError(
                f"CoinGecko JSON parse error: {exc}"
            ) from exc

        try:
            price = data[coin_id][fiat_code.lower()]
            return float(price)
        except (KeyError, TypeError, ValueError) as exc:
            raise CryptoProviderError(
                f"CoinGecko: could not extract {crypto_code}/{fiat_code} from response"
            ) from exc
