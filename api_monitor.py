"""API Usage Monitor – main entry point."""
import json
import os
import sys
from api_clients import DeepSeekClient, OpenKeyClient, fetch_all
from rate_tracker import RateTracker
from widget_ui import DesktopWidget


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: config.json not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    cfg = load_config()
    interval = cfg.get("refresh_interval_seconds", 30) * 1000  # ms
    pricing = cfg.get("pricing", {})

    deepseek = DeepSeekClient(cfg["deepseek"])
    openkey = OpenKeyClient(cfg["openkey"])
    tracker = RateTracker(
        max_history=10,
        price_deepseek_cny_per_1m=pricing.get("price_per_1M_tokens_cny", 2.5),
        price_openkey_usd_per_1m=pricing.get("price_per_1M_tokens_usd", 0.5),
    )
    widget = DesktopWidget(cfg)

    timer_token = None

    def tick():
        nonlocal timer_token
        # cancel any pending timer to avoid overlapping refreshes
        if timer_token:
            widget.cancel_timer(timer_token)
        snapshots = fetch_all(deepseek, openkey)
        tracker.update(snapshots)
        widget.refresh(snapshots, interval // 1000)
        timer_token = widget.after(interval, tick)

    # wire manual-refresh button
    widget.set_on_refresh(tick)

    # first fetch immediately
    tick()

    try:
        widget.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        if timer_token:
            widget.cancel_timer(timer_token)


if __name__ == "__main__":
    main()
