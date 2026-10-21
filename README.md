# Smart Flow NIFTY Pro Max — Upstox starter

## Important status
This is **phase 2 development scaffold**, not a production trading system. It contains:
- Upstox REST adapter for V3 intraday/historical candles, V3 quotes, option contracts and option chain
- a clearly labelled synthetic-data demo mode
- basic EMA/RSI/ATR/VWAP and a provisional index structure panel
- safe token loading from Streamlit Secrets or environment variables
- an explicit feature-status table so unfinished Gold features are not falsely claimed complete

The original Gold source is bundled untouched as a reference. The NIFTY scaffold does not yet port all Gold modules; feature parity requires staged implementation and regression tests.

## Files
- `app.py` — Streamlit starter UI
- `upstox_adapter.py` — REST client
- `Smart_Flow_Gold_V3_PRO_StaleData_Fix_Candidate.py` — preserved source reference; do not overwrite
- `FEATURE_PARITY_CHECKLIST.md` — port and regression checklist
- `requirements.txt`

## Run locally / staging
```bash
python -m venv .venv
# activate the environment
python -m pip install -r requirements.txt
python -m py_compile app.py upstox_adapter.py
streamlit run app.py
```

## Configure Upstox safely
In `.streamlit/secrets.toml` for local development (do not commit this file):
```toml
UPSTOX_ACCESS_TOKEN = "put-token-here-locally"
UPSTOX_NIFTY_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
```
On hosted Streamlit, use the host's Secrets manager. Never paste credentials into chat, commit them to Git, or print them in logs. Access token lifetime and API permission depend on the Upstox token type and account configuration.

## Known limitations
- The default index instrument key should be checked against the current Upstox instrument master/API.
- Option-chain response can vary with API response schema; validate against current official documentation.
- This first scaffold uses REST candles and does not yet connect the live V3 WebSocket/protobuf stream.
- Signal scores are provisional research heuristics, not validated trading signals.
- The CE/PE premium planner is only a mechanical paper-planning calculator; its lot size is manually entered and must be verified. Provider-driven lot/tick-size validation, spread/fees/slippage-aware sizing, option-candle analysis and tested trade logic remain pending.
- No broker order placement is implemented.
- Gold modules such as Smart Flow, liquidity sweep, BOS/CHoCH, order-block sequencing, A+ gate, Next Trigger/Retest, Telegram, paper-trade persistence, backtest lab, Turtle, news guide, CRT/Power of 3, Inside Bar, Magic Ratio, FRVP and COT have not all been ported yet. Use checklist to track each one.

## Rollout rule
Keep the existing Gold app untouched. Test this NIFTY app in a separate staging copy. Do not use real money until live feed, data freshness, signal chain, backtest realism and paper-trading regression tests pass.
