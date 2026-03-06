import requests

from .base_crypto import BaseCryptoProvider, CryptoProviderError

_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"

# Binance quotes crypto in USDT (≈ USD).  For non-USD fiat targets the
# converter composes: crypto_usdt_price × (1 / usd_fiat_rate) using the
# active fiat provider.  This class returns the USDT price only.
_BINANCE_SYMBOLS: dict[str, str] = {
    "BTC":  "BTCUSDT",
    "ETH":  "ETHUSDT",
    "USDT": "USDTUSDC",   # approx 1:1; meaningful for completeness
    "BNB":  "BNBUSDT",
    "XRP":  "XRPUSDT",
    "USDC": "USDCUSDT",   # approx 1:1
    "SOL":  "SOLUSDT",
    "TRX":  "TRXUSDT",
    "DOGE": "DOGEUSDT",
    "ADA":  "ADAUSDT",
}

# Fiat currencies that Binance has direct pairs for (vs BUSD / USDT via
# fiat gateways).  For most users the USDT≈USD approximation is sufficient.
_NATIVE_FIAT = {"USD"}


class BinanceProvider(BaseCryptoProvider):
    """
    Binance public REST API — no API key required for market data.

    Returns the USDT price of a cryptocurrency (~= USD price).
    For non-USD fiat targets the CryptoConverter in converter.py
    applies: result = usdt_price / usd_to_fiat_rate.

    Weight cost: 2 per single-symbol request (1,200 weight/min limit).
    """

    @property
    def name(self) -> str:
        return "Binance"

    def get_price_in_fiat(self, crypto_code: str, fiat_code: str) -> float:
        symbol = _BINANCE_SYMBOLS.get(crypto_code.upper())
        if not symbol:
            raise CryptoProviderError(
                f"Binance: no trading pair for '{crypto_code}'"
            )

        try:
            resp = requests.get(_TICKER_URL, params={"symbol": symbol}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise CryptoProviderError(
                f"Binance request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise CryptoProviderError(
                f"Binance JSON parse error: {exc}"
            ) from exc

        try:
            # Price is returned as a string by Binance.
            usdt_price = float(data["price"])
        except (KeyError, ValueError) as exc:
            raise CryptoProviderError(
                f"Binance: unexpected response format for {symbol}"
            ) from exc

        # If fiat target is USD (or USDT ≈ USD), return directly.
        if fiat_code.upper() in _NATIVE_FIAT:
            return usdt_price

        # For other fiat currencies, signal to the caller that they must
        # apply a USD→fiat conversion.  We raise so CryptoConverter can
        # intercept and compose, or fall back to the next crypto provider.
        raise CryptoProviderError(
            f"Binance does not natively support {fiat_code} pairs; "
            "use CoinGecko or Kraken for multi-fiat crypto conversion"
        )
