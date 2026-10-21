# Smart Flow NIFTY Pro Max — Gold feature parity checklist

Legend: `NOT STARTED` means not yet ported/verified in the NIFTY app. Gold source is preserved separately.

## Existing Gold features to preserve or adapt
- [ ] Quick Trade mobile dashboard
- [ ] Full Pro workspace and tabs
- [ ] Single Master Snapshot / common signal state
- [ ] Live feed connection and Data Health / freshness / reconnect handling
- [ ] 1H / 15M / 5M multi-timeframe analysis
- [ ] Smart Flow scoring
- [ ] Early Entry Engine
- [ ] Big Candle detection
- [ ] BUY / SELL / WAIT with Entry, SL, TP1–TP4
- [ ] Support / Resistance
- [ ] VWAP
- [ ] Liquidity Sweep
- [ ] BOS / CHoCH
- [ ] Order Block map and confirmation sequence
- [ ] Institutional Confluence (label as price/volume proxy; not proof of institutions)
- [ ] A+ Signal Gate and reasons/missing confirmations
- [ ] Next Trigger + Retest Map
- [ ] Market Regime and ADX
- [ ] Equal High / Equal Low liquidity
- [ ] Telegram alerts, diagnostics, deduplication and secret-safe handling
- [ ] Paper / Forward Trading
- [ ] Paper-trade log and persistence semantics
- [ ] Scanner / Backtest / Strategy Lab
- [ ] Turtle Strategy
- [ ] Economic news planner / guide (label manual inputs; no fake live calendar)
- [ ] Magic Ratio
- [ ] CRT / Power of 3
- [ ] Inside Bar close confirmation
- [ ] COMEX/CFTC/COT adapted only if a relevant authentic NIFTY source exists; never reuse Gold data as NIFTY data
- [ ] FRVP / candle-volume-derived profile (clearly distinguish from order-book volume)
- [ ] Golden Chicken scanner/backtest module (review whether it is suitable for NIFTY before porting)
- [ ] Risk sizing, backtest slippage/spread/fees and stop-gap handling

## NIFTY Options-specific features
- [ ] Verify NIFTY instrument key from current Upstox instrument master
- [ ] REST historical/intraday candle adapter
- [ ] WebSocket V3 + protobuf decode + reconnect + heartbeat + stale tick guard
- [ ] Index spot analysis separated from option contract analysis
- [ ] Option chain and contract expiry/strike resolution
- [ ] CE/PE selector and option premium candle analysis
- [ ] Greeks / IV / volume / OI with timestamps and unavailable states
- [ ] Bid/ask spread and liquidity filter
- [ ] Correct lot size / tick size / expiry validation from provider data
- [x] Basic paper-only premium-based reference Entry / SL / TP1–TP4 calculator (mechanical levels only)
- [ ] Validated strategy-based Entry / SL / TP1–TP4
- [ ] Provider-validated options risk engine and paper-trade P&L with fees/slippage
- [ ] Opening range, previous day high/low, gap filter, India VIX context
- [ ] Option-chain stale-data / partial-response guard
- [ ] Replay tests and look-ahead bias checks
- [ ] Full mobile/desktop smoke tests
- [ ] Telegram test in a private test chat
- [ ] Feature-by-feature regression report before release

## Current phase-1 scaffold status
- [x] Separate NIFTY app shell
- [x] Upstox REST adapter scaffold
- [x] Explicit demo mode
- [x] Secrets via Streamlit Secrets/environment
- [x] Provisional technical calculations
- [ ] Live REST response tested with user account
- [ ] WebSocket live stream tested
- [ ] All Gold feature parity completed
- [ ] Real-money readiness approved


## Phase-2 additions (static checks only)
- [x] CE/PE selection from fetched option chain
- [x] Use provider-returned LTP only; no synthetic option premiums
- [x] Illustrative premium stop and TP1–TP4 calculation
- [x] Quantity and estimated premium risk display
- [ ] Live response validation, contract lot-size verification and full Streamlit runtime test
