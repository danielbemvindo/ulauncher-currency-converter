from babel.numbers import format_currency as babel_format_currency
from babel import UnknownLocaleError


_FALLBACK_LOCALE = "en_US"


def _crypto_number(amount: float, digits: int) -> str:
    """Format a crypto quantity to *digits* decimal places, stripping trailing zeros."""
    if amount == int(amount):
        return str(int(amount))
    formatted = f"{amount:.{digits}f}".rstrip("0")
    if formatted.endswith("."):
        formatted += "0"
    return formatted


class CurrencyFormatter:
    """
    Locale-aware currency formatter backed by Babel.

    Locale resolution order for a given fiat currency code:
      1. User's display_locale preference (if non-empty) — applied uniformly.
      2. Per-currency "locale" field from ulauncher-currencies.json.
      3. Fallback: en_US.

    Crypto formatting uses the symbol and digits from ulauncher-cryptocurrencies.json
    rather than Babel, since crypto is not part of the CLDR data set.

    Never uses locale.setlocale() — Babel ships its own CLDR data.
    """

    def __init__(self, currencies_data: dict, display_locale: str = ""):
        self._currencies = currencies_data
        self._override = display_locale.strip()

    def format(self, amount: float, currency_code: str) -> str:
        """
        Locale-formatted fiat string with symbol for Alt+Enter clipboard.

        Examples:  "$5,200.00"  /  "10,00 €"  /  "R$ 5.200,00"  /  "¥1,000"
        """
        locale = self._resolve_locale(currency_code)
        try:
            return babel_format_currency(amount, currency_code.upper(), locale=locale)
        except (ValueError, UnknownLocaleError):
            return f"{amount:,.2f} {currency_code.upper()}"

    def format_crypto(self, amount: float, crypto_code: str, crypto_data: dict) -> str:
        """
        Symbol + full-precision crypto amount for Alt+Enter clipboard.

        Examples:  "₿ 0.00118765"  /  "Ξ 0.05231400"  /  "Ð 1234.56789012"
        """
        entry = crypto_data.get(crypto_code.upper(), {})
        digits = entry.get("digits", 8)
        symbol = entry.get("symbol", crypto_code.upper())
        return f"{symbol} {_crypto_number(amount, digits)}"

    def format_crypto_plain(self, amount: float, crypto_code: str, crypto_data: dict) -> str:
        """
        Plain number string to full crypto precision for Enter clipboard.

        Examples:  "0.00118765"  /  "1234.567891"
        """
        entry = crypto_data.get(crypto_code.upper(), {})
        digits = entry.get("digits", 8)
        return _crypto_number(amount, digits)

    def format_crypto_amount(self, amount: float, crypto_code: str, crypto_data: dict) -> str:
        """
        Symbol + full-precision label for the result title (from-side display).

        Examples:  "₿ 1"  /  "Ξ 0.5"  /  "Ð 1000"
        """
        entry = crypto_data.get(crypto_code.upper(), {})
        digits = entry.get("digits", 8)
        symbol = entry.get("symbol", crypto_code.upper())
        return f"{symbol} {_crypto_number(amount, digits)}"

    def _resolve_locale(self, currency_code: str) -> str:
        if self._override:
            return self._override
        entry = self._currencies.get(currency_code.upper(), {})
        return entry.get("locale") or _FALLBACK_LOCALE
