import json
import os
import tempfile
import time

_CACHE_PATH = os.path.expanduser("~/.cache/ulauncher-currency.json")


class CacheManager:
    """
    Multi-entry JSON cache for exchange rates.

    Each (provider, base) pair is stored independently so switching between
    e.g. USD and BRL as the base currency does not evict the other entry.

    Disk format:
    {
        "frankfurter:USD": {
            "provider":  "frankfurter",
            "base":      "USD",
            "timestamp": 1709500000,
            "rates":     { "EUR": 0.91, "BRL": 4.97, ... }
        },
        "frankfurter:BRL": {
            "provider":  "frankfurter",
            "base":      "BRL",
            "timestamp": 1709500001,
            "rates":     { "USD": 0.19, "EUR": 0.17, ... }
        }
    }
    """

    def __init__(self, cache_path: str = _CACHE_PATH):
        self._path = cache_path
        self._data: dict | None = None  # full in-memory store (all entries)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, provider: str, base: str, ttl: int) -> dict | None:
        """
        Return the cached entry for *provider* + *base* if it is fresh
        (within *ttl* seconds).  Returns None on any miss or expiry.
        """
        store = self._load()
        if store is None:
            return None
        entry = store.get(self._key(provider, base))
        if entry is None:
            return None
        if time.time() - entry.get("timestamp", 0) > ttl:
            return None
        return entry

    def get_stale(self, base: str) -> dict | None:
        """
        Return any cached entry for *base* regardless of provider or TTL.
        Used to show last-known rates while a fresh fetch runs in the background.
        When multiple providers have entries for the same base, the most recent
        one is returned.
        """
        store = self._load()
        if not store:
            return None
        base_upper = base.upper()
        candidates = [
            entry for entry in store.values()
            if isinstance(entry, dict) and entry.get("base", "").upper() == base_upper
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.get("timestamp", 0))

    def set(self, provider: str, base: str, rates: dict) -> None:
        """
        Store *rates* for *provider* + *base*.  Does not touch entries for
        other bases.  Writes the full store to disk atomically.
        """
        store = self._load() or {}
        entry = {
            "provider":  provider,
            "base":      base.upper(),
            "timestamp": time.time(),
            "rates":     rates,
        }
        store[self._key(provider, base)] = entry

        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        dir_name = os.path.dirname(self._path) or "."
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(store, f)
            os.replace(tmp_path, self._path)
        except OSError:
            pass
        else:
            self._data = store

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _key(provider: str, base: str) -> str:
        return f"{provider.lower()}:{base.upper()}"

    def _load(self) -> dict | None:
        if self._data is not None:
            return self._data
        try:
            with open(self._path) as f:
                self._data = json.load(f)
            return self._data
        except (OSError, json.JSONDecodeError, ValueError):
            return None
