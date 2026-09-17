"""Refresh scan.json from delayed daily market prices using only Python's standard library.

The browser still performs no analysis: this separate scanner writes the same JSON
presentation contract consumed by app.js. It is a rules-based aid, not advice.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from statistics import fmean
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json
import math
import ssl
import time

ROOT = Path(__file__).resolve().parent
DIRECTORY_FILE = ROOT / "stocks.json"
SCAN_FILE = ROOT / "scan.json"
SOURCE = "Yahoo Finance delayed market data"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15"


def secure_context():
    """Use the Mac system certificate bundle when python.org Python cannot find it."""
    candidates = [
        ssl.get_default_verify_paths().cafile,
        "/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
    ]
    certificate_file = next((path for path in candidates if path and Path(path).is_file()), None)
    return ssl.create_default_context(cafile=certificate_file)


def fetch_chart(symbol, attempts=3):
    """Return six months of valid daily bars from Yahoo's public chart response."""
    provider_symbol = "^STI" if symbol == "STI" else f"{symbol}.SI"
    encoded = quote(provider_symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=6mo&interval=1d"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})

    last_error = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=18, context=secure_context()) as response:
                payload = json.load(response)
            result = payload["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            quotes = result["indicators"]["quote"][0]
            bars = []
            for index, timestamp in enumerate(timestamps):
                close = quotes["close"][index]
                high = quotes["high"][index]
                low = quotes["low"][index]
                if close is None or high is None or low is None:
                    continue
                bars.append({
                    "timestamp": timestamp,
                    "close": float(close),
                    "high": float(high),
                    "low": float(low),
                    "volume": float(quotes["volume"][index] or 0),
                })
            if len(bars) < 55:
                raise ValueError("Not enough price history")
            return bars, result.get("meta", {})
        except Exception as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(str(last_error))


def rsi(closes, days=14):
    changes = [closes[index] - closes[index - 1] for index in range(len(closes) - days, len(closes))]
    gains = fmean(max(change, 0) for change in changes)
    losses = fmean(max(-change, 0) for change in changes)
    if losses == 0:
        return 100.0
    return 100 - (100 / (1 + gains / losses))


def atr(bars, days=14):
    ranges = []
    for index in range(len(bars) - days, len(bars)):
        previous_close = bars[index - 1]["close"]
        ranges.append(max(
            bars[index]["high"] - bars[index]["low"],
            abs(bars[index]["high"] - previous_close),
            abs(bars[index]["low"] - previous_close),
        ))
    return fmean(ranges)


def metrics_for(bars):
    closes = [bar["close"] for bar in bars]
    volumes = [bar["volume"] for bar in bars]
    average_volume = fmean(volumes[-21:-1]) or 1
    return {
        "close": closes[-1],
        "previous_close": closes[-2],
        "sma20": fmean(closes[-20:]),
        "sma20_previous": fmean(closes[-25:-5]),
        "sma50": fmean(closes[-50:]),
        "sma50_previous": fmean(closes[-55:-5]),
        "close_5_days_ago": closes[-6],
        "rsi": rsi(closes),
        "volume_ratio": volumes[-1] / average_volume,
        "prior_high": max(bar["high"] for bar in bars[-21:-1]),
        "atr": atr(bars),
    }


def score_market(metrics):
    score = 0
    score += 20 if metrics["close"] > metrics["sma20"] else 0
    score += 20 if metrics["sma20"] > metrics["sma50"] else 0
    score += 15 if metrics["sma20"] > metrics["sma20_previous"] else 0
    score += 15 if metrics["close"] > metrics["close_5_days_ago"] else 0
    score += 15 if 45 <= metrics["rsi"] <= 70 else 7 if 38 <= metrics["rsi"] <= 78 else 0
    score += 10 if metrics["volume_ratio"] >= 1 else 5
    score += 5 if metrics["close"] >= metrics["prior_high"] * 0.97 else 0
    return score


def price_text(value):
    digits = 3 if value < 1 else 2
    return f"{value:.{digits}f}"


def stock_decision(stock, bars, meta, market_score):
    metrics = metrics_for(bars)
    positives = []
    cautions = []
    score = 0

    if metrics["close"] > metrics["sma20"]:
        score += 15
        positives.append("The price is holding above its recent average")
    else:
        cautions.append("The price is still below its recent average")

    if metrics["sma20"] > metrics["sma50"]:
        score += 15
        positives.append("The bigger direction is healthy")
    else:
        cautions.append("The bigger direction is still weak")

    if metrics["sma20"] > metrics["sma20_previous"]:
        score += 10
        positives.append("The trend is getting better")
    else:
        cautions.append("The trend has not turned up yet")

    if metrics["close"] > metrics["close_5_days_ago"]:
        score += 10
        positives.append("The price improved this week")
    else:
        cautions.append("The price lost ground this week")

    if 48 <= metrics["rsi"] <= 68:
        score += 15
        positives.append("The price still has room to move")
    elif 40 <= metrics["rsi"] <= 75:
        score += 8
    elif metrics["rsi"] > 75:
        cautions.append("The price may have run too far too quickly")
    else:
        cautions.append("Buyers are not showing enough strength")

    if metrics["volume_ratio"] >= 1.2:
        score += 10
        positives.append("More buyers are showing interest")
    elif metrics["volume_ratio"] >= 0.8:
        score += 5
    else:
        cautions.append("Not enough buyers showed up today")

    if metrics["close"] >= metrics["prior_high"]:
        score += 15
        positives.append("The price cleared its recent ceiling")
    elif metrics["close"] >= metrics["prior_high"] * 0.97:
        score += 8
        positives.append("The price is close to its next step up")
        cautions.append("The next step up is not confirmed")
    else:
        cautions.append("The price is still below its next ceiling")

    if market_score >= 65:
        score += 10
        positives.append("The wider Singapore market is supportive")
    elif market_score >= 45:
        score += 5
    else:
        cautions.append("The wider Singapore market is not helping")

    score = max(0, min(100, round(score)))
    signal = "BUY WATCH" if score >= 75 else "WAIT" if score >= 55 else "AVOID"

    # This is intentionally separate from BUY WATCH.  It looks for an early
    # improvement after a weak phase; it does not claim that an uptrend is
    # established or that the reversal will succeed.
    was_in_downtrend = (
        metrics["sma20_previous"] < metrics["sma50_previous"]
        and metrics["close_5_days_ago"] < metrics["sma20_previous"]
    )
    short_trend_improving = metrics["sma20"] > metrics["sma20_previous"]
    weekly_price_improving = metrics["close"] > metrics["close_5_days_ago"]
    near_or_above_short_trend = metrics["close"] >= metrics["sma20"] * 0.99
    momentum_recovering = 42 <= metrics["rsi"] <= 68
    turnaround = all((
        was_in_downtrend,
        short_trend_improving,
        weekly_price_improving,
        near_or_above_short_trend,
        momentum_recovering,
    ))
    turnaround_reasons = [
        "It was recently trading below its longer trend",
        "Its 20-day trend has started to improve",
        "The price is stronger than it was one week ago",
        "Momentum has recovered into a healthier range",
    ] if turnaround else []

    caution_fallbacks = [
        "Wait for a clearer entry",
        "Do not chase a sudden jump",
        "Keep the stop level in mind",
    ]
    chosen_positives = positives[:3]
    chosen_cautions = (cautions + caution_fallbacks)[:5 - len(chosen_positives)]

    latest = metrics["close"]
    movement = metrics["atr"]
    if signal != "BUY WATCH" or not math.isfinite(movement) or movement <= 0:
        buy_zone, stop, target, risk_reward = "—", "—", "—", "—"
    else:
        # Prefer a pullback toward the rising 20-day trend instead of suggesting
        # that someone chase the current price. ATR keeps the zone proportional
        # to how much this particular counter normally moves.
        entry_low = max(metrics["sma20"], latest - (0.50 * movement))
        entry_high = min(latest, max(entry_low, latest - (0.10 * movement)))
        stop_value = max(0, entry_low - (1.25 * movement))
        entry_midpoint = (entry_low + entry_high) / 2
        target_value = entry_midpoint + (2 * (entry_midpoint - stop_value))
        buy_zone = f"{price_text(entry_low)}–{price_text(entry_high)}"
        stop = price_text(stop_value)
        target = price_text(target_value)
        risk_reward = "2.0"

    if signal == "BUY WATCH":
        eli5 = "The direction and buying interest are supportive. This is one to watch closely, but enter only near the planned price and keep the stop."
    elif signal == "WAIT":
        eli5 = "Some pieces look promising, but the picture is not complete. Keep watching and wait for a clearer move before entering."
    else:
        eli5 = "The setup is not strong enough today. There is no need to force a trade. Leave it alone until the picture improves."

    previous = metrics["previous_close"]
    change_percent = ((latest - previous) / previous * 100) if previous else 0
    currency = meta.get("currency") or "SGD"
    data_time = datetime.fromtimestamp(bars[-1]["timestamp"], ZoneInfo("Asia/Singapore"))

    return {
        "symbol": stock["symbol"],
        "name": stock["name"],
        "score": score,
        "stars": max(1, min(5, round(score / 20))),
        "signal": signal,
        "turnaround": turnaround,
        "turnaroundReasons": turnaround_reasons,
        "price": round(latest, 4),
        "changePercent": round(change_percent, 2),
        "currency": currency,
        "priceDate": data_time.strftime("%d %b %Y"),
        "sparkline": [round(bar["close"], 4) for bar in bars[-42:]],
        "buyZone": buy_zone,
        "stop": stop,
        "target": target,
        "rr": risk_reward,
        "bullets": chosen_positives + chosen_cautions,
        "bulletSentiments": ([True] * len(chosen_positives)) + ([False] * len(chosen_cautions)),
        "eli5": eli5,
    }


def main():
    directory = json.loads(DIRECTORY_FILE.read_text(encoding="utf-8"))
    previous_scan = json.loads(SCAN_FILE.read_text(encoding="utf-8")) if SCAN_FILE.exists() else {"stocks": []}
    previous_by_symbol = {stock["symbol"]: stock for stock in previous_scan.get("stocks", [])}

    print("Refreshing delayed STI market data…")
    market_bars, _market_meta = fetch_chart("STI")
    market_metrics = metrics_for(market_bars)
    market_score_100 = score_market(market_metrics)
    market_score = round(market_score_100 / 10, 1)
    market_signal = "Bullish" if market_score >= 6.5 else "Mixed" if market_score >= 4.5 else "Bearish"

    decisions_by_symbol = {}
    failures = []

    def refresh_one(stock):
        bars, meta = fetch_chart(stock["symbol"])
        return stock_decision(stock, bars, meta, market_score_100)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(refresh_one, stock): stock for stock in directory}
        for index, future in enumerate(as_completed(futures), start=1):
            stock = futures[future]
            print(f"[{index:03d}/{len(directory)}] {stock['name']}")
            try:
                decisions_by_symbol[stock["symbol"]] = future.result()
            except Exception as error:
                failures.append({"symbol": stock["symbol"], "reason": str(error)})
                if stock["symbol"] in previous_by_symbol:
                    decisions_by_symbol[stock["symbol"]] = previous_by_symbol[stock["symbol"]]

    decisions = [decisions_by_symbol[stock["symbol"]] for stock in directory if stock["symbol"] in decisions_by_symbol]

    if not decisions:
        raise RuntimeError("No market data could be refreshed; the previous scan was kept.")

    counts = {
        "buy": sum(stock["signal"] == "BUY WATCH" for stock in decisions),
        "wait": sum(stock["signal"] == "WAIT" for stock in decisions),
        "avoid": sum(stock["signal"] == "AVOID" for stock in decisions),
        "turnaround": sum(bool(stock.get("turnaround")) for stock in decisions),
    }
    now = datetime.now(ZoneInfo("Asia/Singapore"))
    result = {
        "updated": now.strftime("%d %b %Y %-I:%M %p"),
        "mode": "Delayed market data",
        "source": SOURCE,
        "sourceUrl": "https://finance.yahoo.com/",
        "dataDate": datetime.fromtimestamp(market_bars[-1]["timestamp"], ZoneInfo("Asia/Singapore")).strftime("%d %b %Y"),
        "market": {"score": market_score, "signal": market_signal, **counts},
        "stocks": decisions,
        "refreshFailures": failures,
        "method": "Rules based on daily price direction, momentum, trading activity and the wider STI trend. Possible turnaround is a separate early-warning flag, not a forecast."
    }

    temporary = SCAN_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(SCAN_FILE)
    print(f"Updated {len(decisions)} stocks. {len(failures)} could not be refreshed.")


if __name__ == "__main__":
    main()
