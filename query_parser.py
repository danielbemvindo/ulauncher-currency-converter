import re
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ParsedQuery:
    mode: Literal["convert", "crypto", "search", "hint"]
    amount: float | None = None
    from_cc: str | None = None       # uppercased currency/crypto code
    to_cc: str | None = None         # uppercased currency/crypto code
    search_term: str | None = None   # raw string after '?'
    is_crypto: bool = False          # True if from_cc or to_cc is a crypto code
    is_reversed: bool = False        # True when single-code input matched default_to


_FILLER_WORDS = {"to", "in", "from"}

# Matches integers and decimals with either . or , as decimal separator.
_FLOAT_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")

# Matches 3–4 uppercase/lowercase letter tokens (currency and crypto codes).
_CODE_RE = re.compile(r"\b([A-Za-z]{3,4})\b")


class QueryParser:
    """
    Parses a raw Ulauncher keyword query string into a ParsedQuery.

    Accepts the part of the query *after* the keyword (i.e. event.get_argument()).

    Supported formats (case-insensitive):
        "520 usd brl"       → convert 520 USD → BRL
        "usd 520 brl"       → convert 520 USD → BRL
        "10 usd to brl"     → convert 10 USD → BRL   (filler word stripped)
        "10 usd in brl"     → convert 10 USD → BRL
        "520"               → convert 520 default_from → default_to
        "10 usd"            → convert 10 USD → default_to
        "1 btc usd"         → crypto convert 1 BTC → USD
        "?"                 → hint
        "?U"                → hint (< 2 chars)
        "?US"               → code search
        "?dollar"           → name search (≥ 4 chars)
    """

    def __init__(
        self,
        fiat_codes: set[str],
        crypto_codes: set[str],
        default_from: str = "USD",
        default_to: str = "EUR",
    ):
        self._fiat = fiat_codes          # set of uppercase ISO codes
        self._crypto = crypto_codes      # set of uppercase crypto codes (3–4 chars)
        self._default_from = default_from.upper()
        self._default_to = default_to.upper()

    def parse(self, raw: str) -> ParsedQuery:
        text = (raw or "").strip()

        # ── Search mode ────────────────────────────────────────────────
        if text.startswith("?"):
            term = text[1:].strip()
            if len(term) < 2:
                return ParsedQuery(mode="hint", search_term=term)
            return ParsedQuery(mode="search", search_term=term)

        # ── Convert / crypto mode ──────────────────────────────────────
        return self._parse_convert(text)

    def _parse_convert(self, text: str) -> ParsedQuery:
        # Tokenise: split on whitespace, then normalise.
        tokens = text.split()
        # Strip standalone filler words (case-insensitive).
        tokens = [t for t in tokens if t.lower() not in _FILLER_WORDS]

        amounts: list[float] = []
        codes: list[str] = []

        for token in tokens:
            # Try as a number first (handles "1,000" and "1.5").
            num = self._try_parse_number(token)
            if num is not None:
                amounts.append(num)
                continue
            # Try as a currency/crypto code.
            if _CODE_RE.fullmatch(token):
                code = token.upper()
                if self._is_known_code(code):
                    codes.append(code)

        amount = amounts[0] if amounts else None
        from_cc: str | None = None
        to_cc: str | None = None
        is_reversed = False

        if len(codes) >= 2:
            from_cc, to_cc = codes[0], codes[1]
        elif len(codes) == 1:
            single = codes[0]
            # If the only code given matches the default To currency, the user
            # almost certainly wants the reverse direction (e.g. "cc 500 eur"
            # when defaults are USD→EUR should mean EUR→USD, not EUR→EUR).
            if single == self._default_to and single != self._default_from:
                from_cc = single
                to_cc = self._default_from
                is_reversed = True
            else:
                from_cc = single

        # Apply defaults.
        if from_cc is None:
            from_cc = self._default_from
        if to_cc is None:
            to_cc = self._default_to

        # Detect crypto involvement.
        is_crypto = (
            from_cc in self._crypto or to_cc in self._crypto
        )

        mode: Literal["convert", "crypto"] = "crypto" if is_crypto else "convert"
        return ParsedQuery(
            mode=mode,
            amount=amount,
            from_cc=from_cc,
            to_cc=to_cc,
            is_crypto=is_crypto,
            is_reversed=is_reversed,
        )

    # ------------------------------------------------------------------

    def _is_known_code(self, code: str) -> bool:
        return code in self._fiat or code in self._crypto

    @staticmethod
    def _try_parse_number(token: str) -> float | None:
        """
        Accept "520", "1.5", "1,5", "1,000", "1.000,50", "1,000.50".
        Returns None if the token is not a number.
        """
        # Normalise: if both . and , present, the one before the last 3
        # digits is the thousands separator.
        cleaned = token.replace(" ", "")
        # Detect European-style "1.234,56" → swap separators.
        if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", cleaned):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        # Detect "1,234.56" or "1,234" (comma as thousands).
        elif re.match(r"^\d{1,3}(,\d{3})+(\.\d+)?$", cleaned):
            cleaned = cleaned.replace(",", "")
        # Simple comma-as-decimal "1,5".
        elif re.match(r"^\d+,\d+$", cleaned):
            cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def search(self, term: str) -> list[tuple[str, str, bool]]:
        """
        Search currencies and crypto by *term*.

        Returns list of (code, name, is_crypto) tuples, max 8 results.
        Fiat entries precede crypto entries.

        Rules:
          2–3 chars → fuzzy match by code prefix/substring
          4+ chars  → case-insensitive substring match against full name
        """
        results: list[tuple[str, str, bool]] = []
        term_upper = term.upper()
        term_lower = term.lower()
        by_name = len(term) >= 4

        if by_name:
            # Name search: fiat first, then crypto.
            for code in sorted(self._fiat):
                name = self._fiat_name(code)
                if term_lower in name.lower():
                    results.append((code, name, False))
                    if len(results) >= 8:
                        return results
            for code in sorted(self._crypto):
                name = self._crypto_name(code)
                if term_lower in name.lower():
                    results.append((code, name, True))
                    if len(results) >= 8:
                        return results
        else:
            # Code search: prefix match first, then substring.
            fiat_matches = [
                c for c in sorted(self._fiat) if c.startswith(term_upper)
            ] + [
                c for c in sorted(self._fiat)
                if term_upper in c and not c.startswith(term_upper)
            ]
            for code in fiat_matches:
                if (code, self._fiat_name(code), False) not in results:
                    results.append((code, self._fiat_name(code), False))
                if len(results) >= 8:
                    return results

            crypto_matches = [
                c for c in sorted(self._crypto) if c.startswith(term_upper)
            ] + [
                c for c in sorted(self._crypto)
                if term_upper in c and not c.startswith(term_upper)
            ]
            for code in crypto_matches:
                if len(results) >= 8:
                    break
                results.append((code, self._crypto_name(code), True))

        return results[:8]

    # These will be populated by the Extension after loading static data.
    _fiat_data: dict = {}
    _crypto_data: dict = {}

    def _fiat_name(self, code: str) -> str:
        return self._fiat_data.get(code, {}).get("name", code)

    def _crypto_name(self, code: str) -> str:
        return self._crypto_data.get(code, {}).get("name", code)
