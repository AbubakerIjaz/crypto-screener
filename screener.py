import os
import requests
import ccxt
import pandas as pd

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

# Using KuCoin to avoid US server geo-blocks on GitHub Actions
exchange = ccxt.kucoin({"enableRateLimit": True})
markets = exchange.load_markets()

usdt_pairs = [
    symbol for symbol, market in markets.items()
    if symbol.endswith("/USDT") and market.get("active") and market.get("spot")
]

buy_signals = []
sell_signals = []

for symbol in usdt_pairs:
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1d", limit=200)
        if len(ohlcv) < 55:
            continue

        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "volume"])
        df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

        today = df.iloc[-1]
        yesterday = df.iloc[-2]

        # Buy: Above EMA 50 + sweeps previous day's low (wick or body)
        if today["close"] > today["ema50"] and today["low"] < yesterday["low"]:
            buy_signals.append(symbol.replace("/USDT", ""))

        # Sell: Below EMA 50 + sweeps previous day's high (wick or body)
        elif today["close"] < today["ema50"] and today["high"] > yesterday["high"]:
            sell_signals.append(symbol.replace("/USDT", ""))

    except Exception:
        continue

msg = "**📊 1D EMA 50 + Prev Day Sweep Screener**\n\n"
msg += f"**🟢 BUY SWEEPS ({len(buy_signals)}):**\n"
msg += (", ".join(buy_signals[:40]) if buy_signals else "None") + "\n\n"
msg += f"**🔴 SELL SWEEPS ({len(sell_signals)}):**\n"
msg += (", ".join(sell_signals[:40]) if sell_signals else "None")

# Send message to Discord Webhook (capped at 2000 chars)
requests.post(
    DISCORD_WEBHOOK_URL,
    json={"content": msg[:2000]}
)
