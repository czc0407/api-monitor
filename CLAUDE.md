# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
python3 api_monitor.py          # Run the widget
pip install -r requirements.txt # Install dependency (requests)
```

No test suite or linter configuration exists.

## Architecture

**Event loop:** `api_monitor.py` owns the `root.after()` timer loop. The `tick()` closure fetches both APIs, updates the rate tracker, refreshes the UI, then schedules the next tick. Manual refresh (↻ button, `Cmd+R`, context menu) calls `tick()` directly, cancelling any pending timer to avoid overlapping refreshes.

**Data flow:** `api_clients.fetch_all()` → `list[BalanceSnapshot]` → `rate_tracker.update()` (attaches `.rate` dict in-place) → `widget.refresh()`. Each `BalanceSnapshot` uses `__slots__` and carries either balance data or an `.error` string.

**Rate calculation** (`rate_tracker.py`): Compares consecutive snapshots per service. `money_delta = prev_balance - curr_balance`. If negative → top-up detected → clears history (rate = None for that cycle). Uses configurable `price_per_1M_tokens` to derive `tokens_per_second`. For OpenKey, rate tracks `token_remained_cash` (consumable credits), not the account-level `remained_cash`.

**Error handling:** `_get()` in `api_clients.py` normalizes ALL failures (timeout, DNS, 401, 429, 5xx, JSON parse) into `{"error": "..."}`. Clients propagate errors via `BalanceSnapshot.error`. Widget shows error labels in red and the status dot turns red. The app never crashes on API failures.

**UI:** `overrideredirect(True)` frameless tkinter window. All labels created upfront in `_build_*` methods, updated in-place via `refresh()`. Drag via `<B1-Motion>` on titlebar. Native rounded corners via PyObjC: `_apply_native_corners()` finds the NSWindow by title, sets `contentView.layer.cornerRadius`, makes window non-opaque with `clearColor` background, retries up to 5× at 150ms intervals. Falls back silently if PyObjC unavailable.

**Config:** `config.json` (gitignored) holds API keys, pricing, refresh interval, and UI colors. `config.example.json` is the committed template.

**OpenKey API:** Uses two v2 endpoints — `/v2/account/balance` (financial account) and `/v2/token/balance` (consumable credits). Base URL is `https://openkey.cloud` — the `api.` subdomain does not resolve.
