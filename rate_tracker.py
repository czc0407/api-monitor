"""Consumption rate calculation engine."""
from collections import deque
from api_clients import BalanceSnapshot


class RateTracker:
    def __init__(self, max_history: int = 10, price_deepseek_cny_per_1m: float = 2.5, price_openkey_usd_per_1m: float = 0.5):
        self._history: dict[str, deque[BalanceSnapshot]] = {}
        self._max = max_history
        self._prices: dict[str, float] = {
            "deepseek": price_deepseek_cny_per_1m,
            "openkey": price_openkey_usd_per_1m,
        }

    def _key(self, snap: BalanceSnapshot) -> str:
        return snap.service

    def update(self, snapshots: list[BalanceSnapshot]):
        """Attach `rate` dict to each snapshot (mutates in place)."""
        now_ts = None
        for s in snapshots:
            k = self._key(s)
            if k not in self._history:
                self._history[k] = deque(maxlen=self._max)

            # compute rate against most recent previous snapshot
            prev = self._history[k][-1] if self._history[k] else None

            if s.error or prev is None or prev.error:
                s.rate = None
            else:
                # time delta
                import datetime as _dt
                try:
                    t_now = _dt.datetime.fromisoformat(s.timestamp)
                    t_prev = _dt.datetime.fromisoformat(prev.timestamp)
                    dt = (t_now - t_prev).total_seconds()
                except (ValueError, TypeError):
                    s.rate = None
                else:
                    if dt <= 0:
                        s.rate = None
                    else:
                        prev_total = self._get_total_balance(prev)
                        curr_total = self._get_total_balance(s)
                        if prev_total is None or curr_total is None:
                            s.rate = None
                        else:
                            money_delta = prev_total - curr_total
                            if money_delta < 0:
                                # top-up detected → reset rate
                                s.rate = None
                                # clear history on top-up so next interval gives fresh baseline
                                self._history[k].clear()
                            else:
                                money_per_second = money_delta / dt
                                price = self._prices.get(k, 2.5)
                                tokens_per_second = (money_per_second * 1_000_000) / price
                                s.rate = {
                                    "money_per_second": money_per_second,
                                    "tokens_per_second": tokens_per_second,
                                }

            # store for next interval
            self._history[k].append(s)

    @staticmethod
    def _get_total_balance(snap: BalanceSnapshot) -> float | None:
        """Return the primary balance as a float for rate calculation."""
        if snap.service == "deepseek":
            return snap.total_balance  # CNY
        if snap.service == "openkey":
            # use token balance for rate tracking (actual consumable credits)
            return snap.token_remained_cash
        return None
