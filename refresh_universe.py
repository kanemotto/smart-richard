"""Build the searchable SGX share-counter directory.

The official SGX issuer directory includes old and non-trading records.  This
script keeps issuers whose SGX code still has sufficiently recent Singapore
price history, then preserves the nicer names and sectors already curated in
stocks.json.  It is intended for occasional directory maintenance; the hourly
workflow only refreshes prices and scores.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from update_scan import USER_AGENT, fetch_chart, secure_context


ROOT = Path(__file__).resolve().parent
DIRECTORY_FILE = ROOT / "stocks.json"
SGX_ISSUER_URL = "https://api.sgx.com/securities/v1.1/gtis"


def fetch_sgx_issuers():
    """Return the issuer/code records exposed by SGX, across every page."""
    records = []
    page = 0
    total_pages = 1
    while page < total_pages:
        query = urlencode({"start": page, "size": 250})
        request = Request(
            f"{SGX_ISSUER_URL}?{query}",
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        with urlopen(request, timeout=30, context=secure_context()) as response:
            payload = json.load(response)
        total_pages = int(payload.get("meta", {}).get("totalPages", 1))
        records.extend(payload.get("data", []))
        page += 1
    return records


def display_name(name):
    """Turn SGX's uppercase names into readable title case."""
    words = str(name or "").strip().title()
    replacements = {
        " Ltd": " Ltd",
        " Reit": " REIT",
        " Etf": " ETF",
        " S$": " S$",
        " Hk ": " HK ",
        " Inc.": " Inc.",
    }
    for source, replacement in replacements.items():
        words = words.replace(source, replacement)
    return words


def valid_listing(record):
    symbol = str(record.get("stockCode") or "").strip().upper()
    if not symbol:
        return None
    try:
        bars, _meta = fetch_chart(symbol, attempts=2)
        last_trade = datetime.fromtimestamp(bars[-1]["timestamp"], timezone.utc)
        if last_trade < datetime.now(timezone.utc) - timedelta(days=35):
            return None
        return symbol
    except Exception:
        return None


def main():
    existing = json.loads(DIRECTORY_FILE.read_text(encoding="utf-8"))
    existing_by_symbol = {item["symbol"].upper(): item for item in existing}
    issuers = fetch_sgx_issuers()

    by_symbol = {}
    for record in issuers:
        symbol = str(record.get("stockCode") or "").strip().upper()
        if symbol and symbol not in by_symbol:
            by_symbol[symbol] = record

    valid_symbols = set()
    print(f"Checking {len(by_symbol)} SGX issuer codes for current price history…")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(valid_listing, record): symbol for symbol, record in by_symbol.items()}
        for index, future in enumerate(as_completed(futures), start=1):
            symbol = future.result()
            if symbol:
                valid_symbols.add(symbol)
            if index % 50 == 0 or index == len(futures):
                print(f"Checked {index}/{len(futures)} · {len(valid_symbols)} active")

    # Keep the two useful broad-market ETFs from the existing curated directory.
    valid_symbols.update(symbol for symbol in ("ES3", "G3B") if symbol in existing_by_symbol)

    directory = []
    for symbol in sorted(valid_symbols):
        if symbol in existing_by_symbol:
            directory.append(existing_by_symbol[symbol])
            continue
        record = by_symbol[symbol]
        directory.append({
            "symbol": symbol,
            "name": display_name(record.get("companyName")) or symbol,
            "sector": "SGX-listed",
            "universe": "SGX share counter",
        })

    # Friendlier discovery: curated well-known counters first, then the rest by name.
    curated_order = {item["symbol"].upper(): index for index, item in enumerate(existing)}
    directory.sort(key=lambda item: (
        0 if item["symbol"] in curated_order else 1,
        curated_order.get(item["symbol"], 9999),
        item["name"].lower(),
    ))

    temporary = DIRECTORY_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(directory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(DIRECTORY_FILE)
    print(f"Wrote {len(directory)} active SGX share counters to {DIRECTORY_FILE.name}.")


if __name__ == "__main__":
    main()
