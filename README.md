<div align="center">
  <img src="images/currency-converter.svg" width="128" height="128" alt="Currency Converter icon">
  <h1>Currency Converter</h1>
  <p>A <a href="https://ulauncher.io">Ulauncher</a> extension for instant fiat and cryptocurrency conversions.</p>
</div>

---

Convert between 170+ fiat currencies and the top 10 cryptocurrencies without leaving your keyboard. Rates are fetched from multiple free providers with automatic fallback, cached locally so repeated queries are instant, and formatted according to each currency's native locale or your own.

## Screenshots

**Regular conversion** — `cc 520.12 usd eur`

![Regular conversion](https://github.com/user-attachments/assets/65f67b37-0cf0-417c-85cf-ac75e91eb93e)

**Using defaults** — just type an amount, defaults set in preferences are used

![Using defaults](https://github.com/user-attachments/assets/781b48e0-c24f-4ad1-816b-d03ccd44c27f)

**Reversed defaults shorthand** — typing the "To" currency alone (set in preferences) flips the direction

![Reversed defaults](https://github.com/user-attachments/assets/8d102d0e-f3da-48fb-b1b0-f95e15899d20)

**Cryptocurrency** — `cc 0.5 btc usd`

![Bitcoin conversion](https://github.com/user-attachments/assets/623802dc-3c8e-481a-ba36-aedd2a100047)

**Search by code** — `cc ?us`

![Search by code](https://github.com/user-attachments/assets/f785e112-30b6-4adc-b034-23b6f9b4aede)

**Search by name** — `cc ?dollar`

![Search by name](https://github.com/user-attachments/assets/3d6a6b4e-07cd-4fd5-aa62-04bfdc8cb161)

**Preferences**

![Preferences](https://github.com/user-attachments/assets/d0d3058a-65e1-4a5a-b0ba-4f5b6cf6bef2)

## Features

- **170+ fiat currencies** — full ISO 4217 coverage
- **Top 10 cryptocurrencies** — BTC, ETH, USDT, BNB, XRP, USDC, SOL, TRX, DOGE, ADA with proper symbols (₿, Ξ, Ð, ₳…) and satoshi-level precision, or add your own
- **Multiple providers** — 3 free (no API key needed) + 3 with optional API keys; automatic fallback if a provider times out
- **Smart caching** — rates cached per currency pair, configurable TTL (30 s to 24 h), stale results shown instantly while a fresh fetch runs in the background
- **Reversed conversion detection** — typing `cc 500 eur` when your defaults are USD → EUR automatically runs EUR → USD and says so
- **Currency search** — `?US` searches by code, `?dollar` searches by name
- **Two clipboard modes** — Enter copies a plain number (`2875.44`), Alt+Enter copies a locale-formatted string with symbol (`R$ 2.875,44`)
- **Locale-aware formatting** — uses each currency's native locale by default (e.g. EUR formatted as `10,00 €`), overridable in preferences

## Installation

1. Open Ulauncher preferences → **Extensions** → **Add extension**
2. Paste the URL of this repository
3. Click **Add**

Dependencies (`requests` and `babel`) are installed automatically by Ulauncher.

## Usage

The default keyword is **`cc`** (configurable).

| Query | Result |
|---|---|
| `cc 520 usd eur` | Convert 520 USD → EUR |
| `cc 520` | Convert using your default From/To currencies |
| `cc usd 520 eur` | Amount can go anywhere |
| `cc 10 usd to eur` | Filler words `to` / `in` are ignored |
| `cc 500 eur` | If EUR is your default To, runs EUR → USD (reversed) |
| `cc 1 btc usd` | Crypto conversion: 1 BTC → USD |
| `cc 1000 usd btc` | Fiat → crypto: how much BTC does $1000 buy? |
| `cc ?us` | Search currencies with code containing "US" |
| `cc ?dollar` | Search currencies with "dollar" in the name |

**Keyboard shortcuts:**

| Key | Action |
|---|---|
| Enter | Copy plain number to clipboard (`2875.44`) |
| Alt+Enter | Copy locale-formatted value with symbol (`R$ 2.875,44`) |

## Providers

### Fiat — Free, no API key

| Provider | Currencies | Notes |
|---|---|---|
| **Frankfurter** *(default)* | 31 | ECB reference rates, clean REST API |
| **European Central Bank** | 30 | Official ECB XML feed, EUR base |
| **Fawaz Exchange API** | 200+ | CDN-hosted, widest free coverage |

### Fiat — Free tier with API key

| Provider | Free quota | Notes |
|---|---|---|
| **ExchangeRate-API** | 1,500 req/mo | Any base currency, 160+ currencies |
| **Open Exchange Rates** | 1,000 req/mo | USD base on free tier, 170+ currencies |
| **CurrencyAPI** | 300 req/mo | Any base currency, 170+ currencies |

### Cryptocurrency — Free

| Provider | Notes |
|---|---|
| **CoinGecko** *(default)* | 100+ fiat targets; free Demo key recommended for stable rate limits |
| **Binance** | No key required; USD prices via USDT pairs |
| **Kraken** | No key required; native USD, EUR, GBP, JPY, CAD, CHF, AUD pairs |

If the selected provider fails or times out (10 s), the extension automatically falls back through the remaining providers. If all fail, the last cached rates are shown with a stale indicator.

## Configuration

Open **Ulauncher Preferences → Extensions → Currency Converter**.

| Setting | Default | Description |
|---|---|---|
| Keyword | `cc` | Activation keyword |
| Fiat Provider | Frankfurter | Primary exchange rate source |
| Fiat API Key | *(empty)* | Required only for the three keyed providers |
| Crypto Provider | CoinGecko | Primary crypto price source |
| CoinGecko API Key | *(empty)* | Free Demo key from coingecko.com — no credit card needed; improves rate-limit stability |
| Default From | `USD` | Currency used when none is typed |
| Default To | `EUR` | Currency used when none is typed |
| Cache Duration | 1 hour | How long rates are reused before a fresh fetch; options: 24 h / 1 h / 5 min / 30 s |
| Display Locale | *(empty)* | Babel locale for Alt+Enter output (e.g. `pt_BR`). Leave blank to use each currency's native locale |

## License

[MIT](LICENSE)

---

*Built mostly with [Claude Code](https://claude.ai/claude-code) — Claude Sonnet 4.6*
