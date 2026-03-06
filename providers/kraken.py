import requests

from .base_crypto import BaseCryptoProvider, CryptoProviderError

_BASE_URL = "https://api.kraken.com/0/public/Ticker"

# Kraken calls Bitcoin "XBT" internally.  All other symbols match standard.
_KRAKEN_SYMBOL_MAP: dict[str, str] = {
    "BTC": "XBT",
}

# Fiat currencies that Kraken has direct pairs for.
_KRAKEN_FIAT = {"USD", "EUR", "GBP", "JPY", "CAD", "CHF", "AUD"}

# Pair suffix used by Kraken for each fiat.
_FIAT_SUFFIX: dict[str, str] = {
    "USD": "USD",
    "EUR": "EUR",
    "GBP": "GBP",
    "JPY": "JPY",
    "CAD": "CAD",
    "CHF": "CHF",
    "AUD": "AUD",
}

# Known Kraken pairs (from ulauncher-cryptocurrencies.json).
_KRAKEN_PAIRS: dict[str, dict[str, str]] = {
    "BTC":  {"USD": "XBTUSD",  "EUR": "XBTEUR",  "GBP": "XBTGBP",
             "JPY": "XBTJPY",  "CAD": "XBTCAD",  "CHF": "XBTCHF",  "AUD": "XBTAUD"},
    "ETH":  {"USD": "ETHUSD",  "EUR": "ETHEUR",  "GBP": "ETHGBP",
             "JPY": "ETHJPY",  "CAD": "ETHCAD",  "CHF": "ETHCHF",  "AUD": "ETHAUD"},
    "XRP":  {"USD": "XRPUSD",  "EUR": "XRPEUR",  "GBP": "XRPGBP",
             "JPY": "XRPJPY",  "CAD": "XRPCAD",  "AUD": "XRPAUD"},
    "SOL":  {"USD": "SOLUSD",  "EUR": "SOLEUR",  "GBP": "SOLGBP",
             "JPY": "SOLJPY",  "CAD": "SOLCAD",  "AUD": "SOLAUD"},
    "DOGE": {"USD": "DOGEUSD", "EUR": "DOGEEUR", "GBP": "DOGEGBP",
             "CAD": "DOGECAD", "AUD": "DOGEAUD"},
    "ADA":  {"USD": "ADAUSD",  "EUR": "ADAEUR",  "GBP": "ADAGBP",
             "JPY": "ADAJPY",  "CAD": "ADACAD",  "AUD": "ADAAUD"},
}


class KrakenProvider(BaseCryptoProvider):
    """
    Kraken public REST API — no API key required.

    Natively supports USD, EUR, GBP, JPY, CAD, CHF, AUD pairs.
    BTC is mapped to Kraken's internal symbol 'XBT'.

    Response field 'c' = last trade closed: [price, lot_volume].
    Use c[0] for the current price.
    """

    @property
    def name(self) -> str:
        return "Kraken"

    def get_price_in_fiat(self, crypto_code: str, fiat_code: str) -> float:
        crypto_upper = crypto_code.upper()
        fiat_upper = fiat_code.upper()

        if fiat_upper not in _KRAKEN_FIAT:
            raise CryptoProviderError(
                f"Kraken does not have a direct pair for {crypto_upper}/{fiat_upper}"
            )

        pairs_for_crypto = _KRAKEN_PAIRS.get(crypto_upper, {})
        pair = pairs_for_crypto.get(fiat_upper)
        if not pair:
            raise CryptoProviderError(
                f"Kraken: no known pair for {crypto_upper}/{fiat_upper}"
            )

        try:
            resp = requests.get(_BASE_URL, params={"pair": pair}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise CryptoProviderError(
                f"Kraken request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise CryptoProviderError(
                f"Kraken JSON parse error: {exc}"
            ) from exc

        errors = data.get("error", [])
        if errors:
            raise CryptoProviderError(f"Kraken API error: {errors}")

        result = data.get("result", {})
        if not result:
            raise CryptoProviderError("Kraken returned empty result")

        # Kraken result key may differ from the requested pair alias.
        ticker = next(iter(result.values()))
        try:
            price = float(ticker["c"][0])
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise CryptoProviderError(
                f"Kraken: unexpected ticker format for {pair}"
            ) from exc

        return price
