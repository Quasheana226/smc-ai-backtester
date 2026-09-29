# CLAUDE.md

Context and guardrails for AI coding assistants working in this repo.
Setup, structure, and usage are in README.md.

## Project
Streamlit app that backtests two rule-based Smart Money Concepts setups
(liquidity sweep, break of structure) on historical crypto candles, then has a
local LLM summarize the results, including sample-size caveats.

## Constraints
- Free and open-source only. No paid APIs, no API keys, no hosted LLMs.
- LLM runs locally via Ollama (`llama3.2`).
- Scope is sweep + BOS only. Premium/discount zones are out of scope unless requested.

## Domain rules (the spec: code must match these exactly)
- **Swing high**: high > highs of `SWING_LOOKBACK` candles on each side.
  Usable only after those later candles close. Swing low is the mirror.
- **Bullish sweep**: low < prior swing low AND close > prior swing low.
- **Bullish BOS**: close crosses above prior swing high (first close only).
- **Entry**: next candle's open. **Stop**: beyond sweep wick / opposite swing,
  plus `STOP_BUFFER_PCT`. **Target**: `RR_TARGET` x risk.
- Same-candle stop and target: stop wins. One open trade at a time.
- No stop level available: no trade. Fees (`FEE_PCT`) are subtracted in R.
- Bearish versions mirror the bullish ones.

## Non-negotiables
- No look-ahead: never use a candle's data before it has closed. Any change to
  detection or simulation needs a test proving this still holds.
- Tunable numbers live in `src/config.py`, never inline.
- `src/` is pure logic with no Streamlit imports. UI code stays in `app.py`.
- Type hints on every function signature. Docstrings on every public function.
  Comments explain *why*, not *what*.

## Workflow
- Propose a plan before multi-file changes.
- Tests accompany every change to `src/detection/` or `src/backtest/`.
- Ask before adding a dependency.
- Before finishing: `pytest -q` and `ruff check .` both pass.
- Branches: `feature/*`, `fix/*`, `docs/*` off `develop`. Conventional commits.
