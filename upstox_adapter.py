from __future__ import annotations

from typing import Any
from urllib.parse import quote

import pandas as pd
import requests


class UpstoxError(RuntimeError):
    """Raised when Upstox API returns an error or unexpected response."""


class UpstoxClient:
    BASE = "https://api.upstox.com"

    def __init__(self, access_token: str, timeout: float = 12.0):
        token = (access_token or "").strip()
        if not token:
            raise UpstoxError("Missing access token.")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.timeout = timeout

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.get(
                self.BASE + path,
                headers=self._headers,
                params=params,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise UpstoxError(f"Network request failed: {exc.__class__.__name__}") from exc
        if response.status_code in (401, 403):
            raise UpstoxError("Upstox rejected the token or API permission (HTTP %s)." % response.status_code)
        if not response.ok:
            # Avoid printing request headers/token or raw response body into logs/UI.
            raise UpstoxError(f"Upstox HTTP {response.status_code}. Check API docs, instrument key, expiry and permissions.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstoxError("Upstox returned a non-JSON response.") from exc
        if payload.get("status") == "error":
            raise UpstoxError("Upstox returned status=error. Check instrument key, expiry and permissions.")
        return payload

    def intraday_candles(self, instrument_key: str, unit: str = "minutes", interval: int = 5) -> pd.DataFrame:
        # V3 intraday historical candle endpoint; supports flexible unit/interval.
        encoded = quote(instrument_key, safe="")
        path = f"/v3/historical-candle/intraday/{encoded}/{unit}/{interval}"
        payload = self._get(path, {})
        candles = (payload.get("data") or {}).get("candles") or []
        return self._candles_frame(candles)

    def historical_candles(
        self, instrument_key: str, to_date: str, from_date: str,
        unit: str = "minutes", interval: int = 5
    ) -> pd.DataFrame:
        encoded = quote(instrument_key, safe="")
        path = f"/v3/historical-candle/{encoded}/{unit}/{interval}/{to_date}/{from_date}"
        payload = self._get(path, {})
        candles = (payload.get("data") or {}).get("candles") or []
        return self._candles_frame(candles)

    def option_chain(self, instrument_key: str, expiry_date: str) -> dict[str, Any]:
        return self._get(
            "/v2/option/chain",
            {"instrument_key": instrument_key, "expiry_date": expiry_date},
        )

    def option_contracts(self, instrument_key: str, expiry_date: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"instrument_key": instrument_key}
        if expiry_date:
            params["expiry_date"] = expiry_date
        return self._get("/v2/option/contract", params)

    def quotes_v3(self, instrument_keys: list[str]) -> dict[str, Any]:
        if not instrument_keys:
            raise UpstoxError("At least one instrument key is required.")
        return self._get("/v3/market-quote/quotes", {"instrument_key": ",".join(instrument_keys)})

    @staticmethod
    def _candles_frame(candles: list[list[Any]]) -> pd.DataFrame:
        # Upstox candle shape: [timestamp, open, high, low, close, volume, open_interest?]
        cols = ["time", "open", "high", "low", "close", "volume", "open_interest"]
        if not candles:
            return pd.DataFrame(columns=cols)
        rows = []
        for candle in candles:
            row = list(candle[:7])
            row += [None] * (7 - len(row))
            rows.append(row)
        df = pd.DataFrame(rows, columns=cols)
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True).dt.tz_convert("Asia/Kolkata")
        for col in cols[1:]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time")
        return df.reset_index(drop=True)


def option_chain_to_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """Flatten the documented option-chain response conservatively.

    Response layouts can evolve; preserve a compact inspectable fallback rather than
    guessing fields or manufacturing missing prices/OI.
    """
    data = payload.get("data") or []
    rows: list[dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            row: dict[str, Any] = {
                "strike_price": item.get("strike_price"),
                "expiry": item.get("expiry"),
                "underlying_spot_price": item.get("underlying_spot_price"),
            }
            for side in ("call_options", "put_options"):
                opt = item.get(side) or {}
                md = opt.get("market_data") or {}
                greeks = opt.get("option_greeks") or {}
                prefix = "CE" if side == "call_options" else "PE"
                row[f"{prefix}_instrument_key"] = opt.get("instrument_key")
                row[f"{prefix}_ltp"] = md.get("ltp")
                row[f"{prefix}_bid_price"] = md.get("bid_price")
                row[f"{prefix}_ask_price"] = md.get("ask_price")
                row[f"{prefix}_volume"] = md.get("volume")
                row[f"{prefix}_oi"] = md.get("oi")
                row[f"{prefix}_iv"] = greeks.get("iv")
                row[f"{prefix}_delta"] = greeks.get("delta")
                row[f"{prefix}_gamma"] = greeks.get("gamma")
                row[f"{prefix}_theta"] = greeks.get("theta")
                row[f"{prefix}_vega"] = greeks.get("vega")
            rows.append(row)
    return pd.DataFrame(rows)
