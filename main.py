#!/usr/bin/env /home/daniel/Code/python/currencyConverter/.venv/bin/python

import json
import logging
import os
import threading

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import (
    KeywordQueryEvent,
    PreferencesEvent,
    PreferencesUpdateEvent,
    ItemEnterEvent,
)
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

from cache import CacheManager
from formatter import CurrencyFormatter
from query_parser import QueryParser
from provider_chain import ProviderChain, CryptoProviderChain, AllProvidersFailedError
from converter import CurrencyConverter, CryptoConverter, ConversionError
from providers import (
    FIAT_PROVIDER_MAP,
    CRYPTO_PROVIDER_MAP,
    FREE_FIAT_PROVIDERS,
    FREE_CRYPTO_PROVIDERS,
    FrankfurterProvider,
    ECBProvider,
    FawazProvider,
    CoinGeckoProvider,
    BinanceProvider,
    KrakenProvider,
)

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_CURRENCIES_PATH = os.path.join(_DATA_DIR, "ulauncher-currencies.json")
_CRYPTOS_PATH = os.path.join(_DATA_DIR, "ulauncher-cryptocurrencies.json")
_ICON = "images/currency-converter.svg"


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class CurrencyConverterExtension(Extension):

    def __init__(self):
        super().__init__()
        # Static data — loaded once at startup.
        self.currencies: dict = _load_json(_CURRENCIES_PATH)
        self.cryptos: dict = _load_json(_CRYPTOS_PATH)

        self.cache = CacheManager()

        # These are populated by PreferencesEventListener on first load.
        self.provider_key: str = "frankfurter"
        self.fiat_chain: ProviderChain | None = None
        self.crypto_chain: CryptoProviderChain | None = None
        self.fiat_converter: CurrencyConverter | None = None
        self.crypto_converter: CryptoConverter | None = None
        self.query_parser: QueryParser | None = None

        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def build_from_preferences(self, prefs: dict) -> None:
        """(Re)build provider chains and converters from a preferences dict."""
        provider_key = prefs.get("provider", "frankfurter")
        api_key = prefs.get("api_key", "").strip()
        crypto_key = prefs.get("crypto_provider", "coingecko")
        crypto_api_key = prefs.get("crypto_api_key", "").strip()
        display_locale = prefs.get("display_locale", "").strip()
        default_from = prefs.get("default_from", "USD").strip().upper() or "USD"
        default_to = prefs.get("default_to", "EUR").strip().upper() or "EUR"

        self.provider_key = provider_key

        # ── Fiat provider chain ────────────────────────────────────────
        primary_cls = FIAT_PROVIDER_MAP.get(provider_key, FrankfurterProvider)
        if primary_cls.requires_api_key():
            try:
                primary = primary_cls(api_key)
            except ValueError:
                # Key missing or invalid — fall back silently to Frankfurter.
                logger.warning(
                    "API key missing for %s; falling back to Frankfurter.", provider_key
                )
                primary = FrankfurterProvider()
            fallbacks = [FrankfurterProvider(), ECBProvider(), FawazProvider()]
        else:
            primary = primary_cls()
            # Free providers: put the others as fallbacks in a sensible order.
            free_order = [FrankfurterProvider, ECBProvider, FawazProvider]
            fallbacks = [cls() for cls in free_order if cls is not primary_cls]

        self.fiat_chain = ProviderChain([primary] + fallbacks)

        # ── Crypto provider chain ──────────────────────────────────────
        crypto_cls = CRYPTO_PROVIDER_MAP.get(crypto_key, CoinGeckoProvider)
        crypto_all = [CoinGeckoProvider, BinanceProvider, KrakenProvider]
        crypto_order = [crypto_cls] + [c for c in crypto_all if c is not crypto_cls]
        crypto_providers = []
        for cls in crypto_order:
            if cls is CoinGeckoProvider:
                crypto_providers.append(CoinGeckoProvider(crypto_api_key))
            else:
                crypto_providers.append(cls())
        self.crypto_chain = CryptoProviderChain(crypto_providers)

        # ── Formatter ──────────────────────────────────────────────────
        formatter = CurrencyFormatter(self.currencies, display_locale)

        # ── Converters ─────────────────────────────────────────────────
        self.fiat_converter = CurrencyConverter(self.fiat_chain, self.cache, formatter)
        self.crypto_converter = CryptoConverter(
            self.crypto_chain, self.fiat_converter, formatter
        )
        self.crypto_converter.set_crypto_codes(set(self.cryptos.keys()))

        # ── Parser ─────────────────────────────────────────────────────
        self.query_parser = QueryParser(
            fiat_codes=set(self.currencies.keys()),
            crypto_codes=set(self.cryptos.keys()),
            default_from=default_from,
            default_to=default_to,
        )
        self.query_parser._fiat_data = self.currencies
        self.query_parser._crypto_data = self.cryptos


# ── Event Listeners ────────────────────────────────────────────────────────────


class PreferencesEventListener(EventListener):
    """Fires once on extension startup with the current saved preferences."""

    def on_event(self, event, extension: CurrencyConverterExtension):
        extension.build_from_preferences(event.preferences)


class PreferencesUpdateEventListener(EventListener):
    """Fires when the user changes a preference in the Ulauncher settings UI."""

    def on_event(self, event, extension: CurrencyConverterExtension):
        # Rebuild everything — preferences are lightweight objects.
        if event.id in (
            "provider", "api_key",
            "crypto_provider", "crypto_api_key",
            "display_locale", "default_from", "default_to",
        ):
            # extension.preferences is already a dict[str, str] in API v2.
            prefs = dict(extension.preferences)
            prefs[event.id] = event.new_value
            extension.build_from_preferences(prefs)
        # cache_duration is read dynamically on each query; no rebuild needed.


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension: CurrencyConverterExtension):
        query_text = (event.get_argument() or "").strip()
        parsed = extension.query_parser.parse(query_text)

        if parsed.mode == "hint":
            return RenderResultListAction([_hint_item()])

        if parsed.mode == "search":
            return self._handle_search(parsed.search_term, query_text, extension)

        # convert or crypto
        return self._handle_convert(parsed, query_text, extension)

    # ------------------------------------------------------------------

    def _handle_search(
        self, term: str, raw_query: str, extension: CurrencyConverterExtension
    ):
        results = extension.query_parser.search(term)
        if not results:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon=_ICON,
                    name=f'No currencies matching "{term}"',
                    description="Try a different code or name",
                    on_enter=DoNothingAction(),
                )
            ])

        items = []
        for code, name, is_crypto in results:
            label = f"{'₿ ' if is_crypto else ''}{code} — {name}"
            # Build a replacement query by substituting the ? search with the code.
            new_query = _build_replacement_query(raw_query, code, extension)
            items.append(
                ExtensionResultItem(
                    icon=_ICON,
                    name=label,
                    description="Press Enter to use this currency",
                    on_enter=SetUserQueryAction(
                        f"{extension.preferences['kw']} {new_query}"
                    ),
                )
            )
        return RenderResultListAction(items)

    def _handle_convert(self, parsed, raw_query, extension: CurrencyConverterExtension):
        amount = parsed.amount if parsed.amount is not None else 1.0
        from_cc = parsed.from_cc
        to_cc = parsed.to_cc
        ttl = int(extension.preferences.get("cache_duration", 3600))

        try:
            if parsed.is_crypto:
                result = extension.crypto_converter.convert(
                    amount, from_cc, to_cc, ttl, extension.provider_key
                )
            else:
                result = extension.fiat_converter.convert(
                    amount, from_cc, to_cc, ttl, extension.provider_key
                )
        except ConversionError as exc:
            return RenderResultListAction([_error_item(str(exc))])

        # If stale, kick off a background refresh so the next query is fast.
        if result.is_stale and not parsed.is_crypto:
            threading.Thread(
                target=_background_refresh,
                args=(extension, from_cc, extension.provider_key),
                daemon=True,
            ).start()

        formatter = (
            extension.crypto_converter.formatter
            if parsed.is_crypto
            else extension.fiat_converter.formatter
        )

        to_is_crypto = to_cc in extension.cryptos
        if to_is_crypto:
            plain_value = formatter.format_crypto_plain(result.converted, to_cc, extension.cryptos)
            formatted_value = formatter.format_crypto(result.converted, to_cc, extension.cryptos)
        else:
            plain_value = _format_plain(result.converted)
            formatted_value = formatter.format(result.converted, to_cc)

        # Display amount: show "₿ 1" or "520.00 USD"
        from_label = (
            formatter.format_crypto_amount(amount, from_cc, extension.cryptos)
            if parsed.is_crypto and from_cc in extension.cryptos
            else f"{amount:,.2f} {from_cc}"
        )

        name = f"{from_label}  →  {_fmt_display(result.converted, to_cc, extension.cryptos)}"
        if result.is_stale:
            name += "  (stale)"

        reversed_note = " · (reversed defaults)" if parsed.is_reversed else ""
        stale_note = " · fetching fresh data…" if result.is_stale else ""
        description = (
            f"via {result.provider_name} · {result.age_label()}{reversed_note}{stale_note}"
        )

        return RenderResultListAction([
            ExtensionResultItem(
                icon=_ICON,
                name=name,
                description=description,
                on_enter=CopyToClipboardAction(plain_value),
                on_alt_enter=CopyToClipboardAction(formatted_value),
            )
        ])


class ItemEnterEventListener(EventListener):
    """Handles ExtensionCustomAction payloads (currently unused; reserved)."""

    def on_event(self, event, extension: CurrencyConverterExtension):
        pass


# ── Helpers ────────────────────────────────────────────────────────────────────


def _hint_item() -> ExtensionResultItem:
    return ExtensionResultItem(
        icon=_ICON,
        name="Type at least 2 characters to search",
        description="e.g. ?US for codes  ·  ?Dollar for names",
        on_enter=DoNothingAction(),
    )


def _error_item(message: str) -> ExtensionResultItem:
    return ExtensionResultItem(
        icon=_ICON,
        name="Could not fetch exchange rates",
        description=message or "All providers timed out. Check your connection.",
        on_enter=DoNothingAction(),
    )


def _format_plain(value: float) -> str:
    """Plain fiat numeric string for clipboard (Enter key)."""
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


def _fmt_display(value: float, code: str, crypto_data: dict) -> str:
    """Compact display value for the result title."""
    entry = crypto_data.get(code.upper(), {})
    if entry:
        # Crypto target: use symbol and correct digit count.
        digits = entry.get("digits", 8)
        symbol = entry.get("symbol", code.upper())
        if value == int(value):
            return f"{symbol} {int(value)}"
        formatted = f"{value:.{digits}f}".rstrip("0")
        if formatted.endswith("."):
            formatted += "0"
        return f"{symbol} {formatted}"
    # Fiat target.
    if value >= 1:
        return f"{value:,.2f} {code}"
    return f"{value:.8f}".rstrip("0") + f" {code}"


def _build_replacement_query(raw_query: str, chosen_code: str, extension) -> str:
    """
    Replace the ?... search term in *raw_query* with *chosen_code*.
    E.g. "100 ? brl" → "100 usd brl" when user picks USD.
    """
    return raw_query.replace(raw_query[raw_query.find("?"):].split()[0], chosen_code.lower())


def _background_refresh(
    extension: CurrencyConverterExtension, base: str, provider_key: str
) -> None:
    """Run in a daemon thread to warm the cache without blocking the UI."""
    try:
        rates, provider_name = extension.fiat_chain.get_rates(base)
        extension.cache.set(provider_key, base, rates)
        logger.debug("Background refresh complete: %s/%s", provider_name, base)
    except AllProvidersFailedError:
        logger.debug("Background refresh failed for base=%s", base)


if __name__ == "__main__":
    CurrencyConverterExtension().run()
