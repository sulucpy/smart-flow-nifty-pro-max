from __future__ import annotations

import os
from datetime import datetime, date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from upstox_adapter import UpstoxClient, UpstoxError, option_chain_to_frame

APP_NAME = "Smart Flow NIFTY Pro Max"
st.set_page_config(page_title=APP_NAME, page_icon="📈", layout="wide")

# Keep the Gold source as a separate, untouched reference module in this project.
# This NIFTY app intentionally does not import the Gold app: the latter contains
# Gold-specific feed assumptions and top-level Streamlit UI execution.

def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.getenv(name, default).strip()

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = up / down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = df.copy()
    for col in ("open", "high", "low", "close", "volume"):
        if col not in x:
            x[col] = 0.0
        x[col] = pd.to_numeric(x[col], errors="coerce")
    x["ema20"] = ema(x["close"], 20)
    x["ema50"] = ema(x["close"], 50)
    x["rsi14"] = rsi(x["close"])
    x["atr14"] = atr(x)
    x["vwap"] = (
        ((x["high"] + x["low"] + x["close"]) / 3 * x["volume"]).cumsum()
        / x["volume"].replace(0, np.nan).cumsum()
    )
    return x

def structure_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or len(df) < 30:
        return {"status": "INSUFFICIENT DATA", "bias": "WAIT", "reasons": ["Need at least 30 candles"]}
    x = enrich(df).dropna(subset=["close"])
    last = x.iloc[-1]
    prior = x.iloc[-21:-1]
    swing_high = float(prior["high"].max())
    swing_low = float(prior["low"].min())
    bull_bos = float(last["close"]) > swing_high
    bear_bos = float(last["close"]) < swing_low
    bull_trend = float(last["ema20"]) > float(last["ema50"])
    bear_trend = float(last["ema20"]) < float(last["ema50"])
    above_vwap = pd.notna(last["vwap"]) and float(last["close"]) > float(last["vwap"])
    below_vwap = pd.notna(last["vwap"]) and float(last["close"]) < float(last["vwap"])
    buy_score = int(bull_trend) * 25 + int(above_vwap) * 15 + int(bull_bos) * 35 + int(float(last["rsi14"]) > 50) * 15
    sell_score = int(bear_trend) * 25 + int(below_vwap) * 15 + int(bear_bos) * 35 + int(float(last["rsi14"]) < 50) * 15
    if buy_score >= 60 and buy_score > sell_score:
        bias = "BULLISH"
    elif sell_score >= 60 and sell_score > buy_score:
        bias = "BEARISH"
    else:
        bias = "WAIT / RANGE"
    return {
        "status": "PROVISIONAL — validate in paper trading",
        "bias": bias, "buy_score": buy_score, "sell_score": sell_score,
        "close": float(last["close"]), "ema20": float(last["ema20"]),
        "ema50": float(last["ema50"]), "vwap": float(last["vwap"]) if pd.notna(last["vwap"]) else None,
        "rsi": float(last["rsi14"]) if pd.notna(last["rsi14"]) else None,
        "atr": float(last["atr14"]) if pd.notna(last["atr14"]) else None,
        "swing_high": swing_high, "swing_low": swing_low,
        "reasons": [
            "EMA20/EMA50 trend filter", "VWAP position", "20-candle range break",
            "RSI momentum filter"
        ]
    }

def option_risk_plan(entry: float, stop_pct: float, reward_risks: list[float], lot_size: int, lots: int, account_value: float) -> dict[str, Any]:
    """Paper-planning levels for an option premium; never submits broker orders."""
    if not np.isfinite(entry) or entry <= 0:
        raise ValueError("Option LTP must be a positive real value.")
    if not 0 < stop_pct < 50:
        raise ValueError("Stop-loss percentage must be between 0 and 50.")
    if lot_size < 1 or lots < 1:
        raise ValueError("Lot size and number of lots must be at least 1.")
    risk_per_unit = entry * stop_pct / 100
    stop = max(0.05, entry - risk_per_unit)
    qty = lot_size * lots
    risk_amount = (entry - stop) * qty
    targets = [round(entry + (entry - stop) * rr, 2) for rr in reward_risks]
    return {
        "entry": round(entry, 2), "stop_loss": round(stop, 2), "targets": targets,
        "quantity": qty, "lot_size": lot_size, "lots": lots,
        "risk_amount": round(risk_amount, 2),
        "risk_pct_of_account": round(risk_amount / account_value * 100, 3) if account_value > 0 else None,
        "reward_risks": reward_risks,
    }

def make_demo_candles(n: int = 180) -> pd.DataFrame:
    # Clearly labelled synthetic data; never presented as live market data.
    rng = np.random.default_rng(42)
    changes = rng.normal(0.0, 10.0, n)
    close = 25000 + np.cumsum(changes)
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) + rng.uniform(1, 9, n)
    low = np.minimum(open_, close) - rng.uniform(1, 9, n)
    volume = rng.integers(1000, 100000, n)
    times = pd.date_range(end=pd.Timestamp.now(tz="Asia/Kolkata"), periods=n, freq="5min")
    return pd.DataFrame({"time": times, "open": open_, "high": high, "low": low, "close": close, "volume": volume})

st.title("📈 Smart Flow NIFTY Pro Max")
st.caption("Upstox-powered NIFTY Options research workspace • development/staging build • not a broker execution system")

with st.sidebar:
    st.header("Connection & Mode")
    mode = st.radio("Data mode", ["Demo / synthetic (clearly labelled)", "Upstox API"], index=0)
    st.caption("Demo candles are synthetic and must never be used as real trade signals.")
    st.divider()
    st.header("Analysis settings")
    timeframe = st.selectbox("Analysis timeframe", ["5 minutes", "15 minutes", "1 hour"], index=0)
    risk_pct = st.slider("Risk budget (% of account)", 0.1, 1.0, 0.5, 0.1)
    account_value = st.number_input("Paper account value (₹)", min_value=1000, value=100000, step=5000)
    st.caption("Position sizing is a planning estimate only. Verify lot size, brokerage, taxes, slippage and broker rules.")
    option_stop_pct = st.slider("Option premium stop (%)", 5, 40, 20, 5)
    option_lot_size = st.number_input("Lot size (verify current contract specs)", min_value=1, value=65, step=1)
    option_lots = st.number_input("Lots for paper plan", min_value=1, value=1, step=1)

st.info("Implementation phase 1: provider adapter, data-health checks, option-chain view, and a provisional NIFTY structure panel. Gold feature parity is tracked separately and is not yet claimed complete.")

access_token = get_secret("UPSTOX_ACCESS_TOKEN")
nifty_key = get_secret("UPSTOX_NIFTY_INSTRUMENT_KEY", "NSE_INDEX|Nifty 50")
expiry_default = date.today() + timedelta(days=7)

left, right = st.columns([1.2, 1])
with left:
    st.subheader("NIFTY index context")
    if mode.startswith("Demo"):
        candles = make_demo_candles()
        st.warning("DEMO DATA — generated synthetic candles, not live NSE data.")
        freshness_text = "Synthetic data — no live feed"
    else:
        if not access_token:
            st.error("Upstox access token not configured. Add UPSTOX_ACCESS_TOKEN to Streamlit Secrets. Do not paste it into chat or commit it to GitHub.")
            candles = pd.DataFrame()
            freshness_text = "NOT CONNECTED — missing secret"
        else:
            try:
                client = UpstoxClient(access_token)
                candles = client.intraday_candles(nifty_key, unit="minutes", interval=5)
                freshness_text = "Historical/intraday REST data fetched; WebSocket streaming not yet connected in this scaffold."
            except UpstoxError as exc:
                candles = pd.DataFrame()
                freshness_text = f"DATA ERROR: {exc}"
                st.error(f"Upstox data request failed: {exc}")
    st.caption(f"Data health: {freshness_text}")
    if not candles.empty:
        result = structure_summary(candles)
        m1, m2, m3 = st.columns(3)
        m1.metric("NIFTY bias", result["bias"])
        m2.metric("Buy score", f'{result.get("buy_score", 0)}/90')
        m3.metric("Sell score", f'{result.get("sell_score", 0)}/90')
        st.write("**Current close:**", f'{result.get("close", 0):,.2f}')
        st.write("**EMA20 / EMA50:**", f'{result.get("ema20", 0):,.2f} / {result.get("ema50", 0):,.2f}')
        st.write("**VWAP:**", f'{result.get("vwap", 0):,.2f}' if result.get("vwap") else "Unavailable")
        st.write("**RSI(14) / ATR(14):**", f'{result.get("rsi", 0):.1f} / {result.get("atr", 0):.2f}' if result.get("rsi") is not None and result.get("atr") is not None else "Unavailable")
        st.write("**Prior 20-candle range:**", f'{result.get("swing_low", 0):,.2f} – {result.get("swing_high", 0):,.2f}')
        st.caption(result["status"])
        st.dataframe(candles.tail(12), use_container_width=True, hide_index=True)
    else:
        st.warning("No candles available. No signal will be generated.")

with right:
    st.subheader("NIFTY Options chain")
    expiry = st.date_input("Expiry date", value=expiry_default)
    if mode.startswith("Demo"):
        st.info("Option-chain panel is disabled in demo mode because synthetic option contracts would be misleading.")
    elif not access_token:
        st.warning("Configure Upstox token to fetch the real option chain.")
    else:
        if st.button("Fetch option chain", type="primary"):
            try:
                client = UpstoxClient(access_token)
                chain = client.option_chain(nifty_key, expiry.isoformat())
                chain_df = option_chain_to_frame(chain)
                if chain_df.empty:
                    st.warning("Upstox returned no option contracts for this expiry. Check the index key, expiry, API permissions and market status.")
                else:
                    st.session_state["nifty_option_chain"] = chain_df
                    st.session_state["nifty_option_chain_time"] = datetime.now().isoformat(timespec="seconds")
            except UpstoxError as exc:
                st.error(f"Option-chain request failed: {exc}")
        chain_df = st.session_state.get("nifty_option_chain", pd.DataFrame())
        if not chain_df.empty:
            st.caption("Fetched at: " + st.session_state.get("nifty_option_chain_time", "unknown"))
            st.dataframe(chain_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No option-chain data fetched yet.")

st.divider()
st.subheader("CE / PE paper risk planner")
chain_df = st.session_state.get("nifty_option_chain", pd.DataFrame())
if mode.startswith("Demo"):
    st.info("Risk planner is available only with a real fetched option-chain LTP. Demo mode will not invent option premiums.")
elif chain_df.empty:
    st.info("Fetch a real Upstox option chain first. No entry or targets are calculated without an actual option LTP.")
else:
    side_choice = st.radio("Contract side", ["CE", "PE"], horizontal=True)
    key_col = f"{side_choice}_instrument_key"
    ltp_col = f"{side_choice}_ltp"
    available = chain_df.dropna(subset=[ltp_col]).copy() if ltp_col in chain_df else pd.DataFrame()
    if available.empty:
        st.warning(f"No real {side_choice} LTP values are present in the fetched chain.")
    else:
        available["contract_label"] = available.apply(
            lambda r: f"{r.get('strike_price', 'Strike?')} | {r.get('expiry', 'Expiry?')} | LTP ₹{float(r[ltp_col]):.2f}", axis=1
        )
        selected_label = st.selectbox("Select option contract", available["contract_label"].tolist())
        selected = available.loc[available["contract_label"] == selected_label].iloc[0]
        ltp = float(selected[ltp_col])
        try:
            plan = option_risk_plan(ltp, float(option_stop_pct), [1, 2, 3, 4], int(option_lot_size), int(option_lots), float(account_value))
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Reference LTP / entry", f"₹{plan['entry']:.2f}")
            p2.metric("Illustrative stop", f"₹{plan['stop_loss']:.2f}")
            p3.metric("Quantity", str(plan["quantity"]))
            p4.metric("Planned premium risk", f"₹{plan['risk_amount']:.2f}")
            target_rows = [{"Level": f"TP{i+1}", "Target premium": f"₹{target:.2f}", "R multiple": f"{i+1}:1"} for i, target in enumerate(plan["targets"])]
            st.dataframe(pd.DataFrame(target_rows), use_container_width=True, hide_index=True)
            st.caption(f"Risk estimate = ₹{plan['risk_amount']:.2f} ({plan['risk_pct_of_account']}% of the entered paper account), before brokerage, taxes, spread and slippage. Contract: {selected.get(key_col, 'instrument key unavailable')}.")
            st.warning("These are mechanical planning levels, not a BUY/SELL recommendation. A selected LTP can change immediately; stop execution is not guaranteed. Lot size is user-entered and must be verified for the selected expiry.")
        except (ValueError, TypeError) as exc:
            st.error(f"Could not calculate risk plan: {exc}")

st.divider()
st.subheader("Smart Flow module status")
status_rows = [
    ("Market data adapter / REST candles", "Scaffolded; validate using a real Upstox account"),
    ("CE/PE option-chain retrieval", "Scaffolded; live response not tested here"),
    ("Live WebSocket / protobuf", "Pending implementation and runtime verification"),
    ("Gold Smart Flow feature parity", "Pending staged port and per-feature regression"),
    ("BOS/CHoCH, liquidity sweep, order blocks, A+ gate", "Only basic provisional structure filters exist in this first scaffold"),
    ("Entry / SL / TP1–TP4 for option premium", "Paper-only premium risk planner added; broker execution not implemented"),
    ("Telegram, durable paper-trade journal, backtest", "Pending integration and tests"),
    ("Broker order placement", "Not implemented; no orders are sent"),
]
st.dataframe(pd.DataFrame(status_rows, columns=["Module", "Status"]), use_container_width=True, hide_index=True)

st.warning("This is an initial development scaffold, not a finished trading system. Do not use provisional scores for real-money decisions. Confirm data freshness, option contract details, fees, spreads, and backtest results before paper/live use.")
