from .base import BaseProvider, ProviderError
from .base_crypto import BaseCryptoProvider, CryptoProviderError
from .frankfurter import FrankfurterProvider
from .ecb import ECBProvider
from .fawaz import FawazProvider
from .exchangerate_api import ExchangeRateAPIProvider
from .openexchangerates import OpenExchangeRatesProvider
from .currencyapi import CurrencyAPIProvider
from .coingecko import CoinGeckoProvider
from .binance import BinanceProvider
from .kraken import KrakenProvider

__all__ = [
    "BaseProvider",
    "ProviderError",
    "BaseCryptoProvider",
    "CryptoProviderError",
    "FrankfurterProvider",
    "ECBProvider",
    "FawazProvider",
    "ExchangeRateAPIProvider",
    "OpenExchangeRatesProvider",
    "CurrencyAPIProvider",
    "CoinGeckoProvider",
    "BinanceProvider",
    "KrakenProvider",
]

# Maps manifest preference values to provider classes (fiat).
FIAT_PROVIDER_MAP: dict[str, type] = {
    "frankfurter":      FrankfurterProvider,
    "ecb":              ECBProvider,
    "fawaz":            FawazProvider,
    "exchangerate_api": ExchangeRateAPIProvider,
    "openexchangerates": OpenExchangeRatesProvider,
    "currencyapi":      CurrencyAPIProvider,
}

# Maps manifest preference values to provider classes (crypto).
CRYPTO_PROVIDER_MAP: dict[str, type] = {
    "coingecko": CoinGeckoProvider,
    "binance":   BinanceProvider,
    "kraken":    KrakenProvider,
}

# Ordered free fiat fallback list (used by ProviderChain).
FREE_FIAT_PROVIDERS = [FrankfurterProvider, ECBProvider, FawazProvider]

# Ordered crypto fallback list.
FREE_CRYPTO_PROVIDERS = [CoinGeckoProvider, BinanceProvider, KrakenProvider]
