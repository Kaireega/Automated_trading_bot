# Infrastructure Fix Tracker
> Clearing pre-live blockers. Strategy overhaul handled separately.
> Started: 2026-03-19

| # | Fix | Status | Verified? |
|---|-----|--------|-----------|
| 1 | main.py TimeFrame string/enum crash | ✅ | ⬜ run 3 loops to confirm |
| 2 | Pre-trade cooldown enforcement | ✅ | ⬜ run live and check logs |
| 3 | Trade journal fallback (file-based if MongoDB fails) | ✅ | ✅ MongoDB connected, write/read/delete verified |
| 4 | config.env deletion | ✅ | ✅ file does not exist |
| 5 | News gatekeeper static schedule | ✅ | ⬜ check logs for S-1 block messages |
| 6 | Safety feature checklist after overhaul | ⬜ (post-overhaul) | ⬜ |

## Fix 1 — What changed
- `main.py`: Added `_normalize_timeframe_keys()` method that converts string keys ('H4', 'H1') → TimeFrame enums.
- Called immediately after `all_data[pair]` is read at the top of each pair's analysis block.
- Changed `TimeFrame.M5` → `TimeFrame.H4` on lines 322, 365, 367 (bot uses H4 as primary TF).
- Also added `self._last_trade_time = None` init (used by Fix 2).

## Fix 2 — What changed
- `main.py`: Cooldown check inserted before `execute_trade`. Reads `config.trading.pre_trade_cooldown_seconds` (default 30s).
- If a trade was executed within the cooldown window, skips the pair for this loop cycle.
- Records `self._last_trade_time = datetime.utcnow()` after every successful trade execution.

## Fix 3 — What changed
- `position_manager.py`: Added `FileTradeJournal` class at top of file (writes JSONL to `results/trade_journal.jsonl`).
- `PositionManager.__init__`: `self._file_journal = FileTradeJournal(...)` always initialized.
- `_record_trade()`: MongoDB failure now falls back to `_file_journal.record_open()` instead of just logging a warning.
- `_close_position()`: MongoDB failure now falls back to `_file_journal.record_close()`.
- Trades are now always recorded somewhere — MongoDB if it works, file if it doesn't.

## Fix 4 — What changed
- `config.env` did not exist. No action needed.

## Fix 5 — What changed
- `fundamental_analyzer.py`: Added `_RECURRING_HIGH_IMPACT` class-level schedule of FOMC, NFP, ECB, BOE windows.
- `should_block_trading()` now checks the static schedule first (works even when external API is down), then falls through to the dynamic calendar check.
- Blocks ±30 minutes around each event window.

## Fix 6 — Pending (run after strategy overhaul)
See checklist in `INFRA_FIXES_PROMPT.md` Fix 6 section.
