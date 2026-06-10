"""HTTP clients for DeepSeek and OpenKey APIs."""
import requests
from datetime import datetime
from typing import Optional


class BalanceSnapshot:
    """Normalized balance snapshot for a single service."""

    __slots__ = (
        "service", "timestamp", "currency",
        "total_balance", "granted_balance", "topped_up_balance",
        "remained_cash", "used_cash",
        "token_remained_cash", "token_used_cash",
        "error",
        # attached by rate_tracker
        "rate",
    )

    def __init__(self):
        self.service: str = ""
        self.timestamp: str = ""
        self.currency: str = ""
        self.total_balance: Optional[float] = None
        self.granted_balance: Optional[float] = None
        self.topped_up_balance: Optional[float] = None
        self.remained_cash: Optional[float] = None
        self.used_cash: Optional[float] = None
        self.token_remained_cash: Optional[float] = None
        self.token_used_cash: Optional[float] = None
        self.error: Optional[str] = None
        self.rate: Optional[dict] = None  # {"money_per_second": float, "tokens_per_second": float}


def _get(url: str, headers: dict, timeout: int = 10) -> dict:
    """GET request with normalised error handling."""
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection failed – check network"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}

    if resp.status_code == 401:
        return {"error": "Unauthorized – check API key / token"}
    if resp.status_code == 429:
        return {"error": "Rate limited – wait before retrying"}
    if resp.status_code >= 500:
        return {"error": f"Server error (HTTP {resp.status_code})"}
    if not resp.ok:
        return {"error": f"HTTP {resp.status_code}"}

    try:
        return resp.json()
    except ValueError:
        return {"error": "Invalid JSON in response"}


class DeepSeekClient:
    """Fetch balance from DeepSeek API."""

    def __init__(self, config: dict):
        self.api_key = config.get("api_key", "")
        self.url = config["base_url"].rstrip("/") + config["balance_path"]

    def fetch(self) -> BalanceSnapshot:
        snap = BalanceSnapshot()
        snap.service = "deepseek"
        snap.timestamp = datetime.now().isoformat()

        if not self.api_key:
            snap.error = "API key not configured"
            return snap

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        data = _get(self.url, headers)

        if "error" in data:
            snap.error = data["error"]
            return snap

        try:
            infos = data.get("balance_infos", [])
            if not infos:
                snap.error = "Empty balance_infos in response"
                return snap

            info = infos[0]
            snap.currency = info.get("currency", "CNY")
            snap.total_balance = float(info.get("total_balance", 0))
            snap.granted_balance = float(info.get("granted_balance", 0))
            snap.topped_up_balance = float(info.get("topped_up_balance", 0))
        except (KeyError, ValueError, TypeError) as e:
            snap.error = f"Parse error: {e}"
        return snap


class OpenKeyClient:
    """Fetch balance from OpenKey API (v2)."""

    def __init__(self, config: dict):
        self.token = config.get("bearer_token", "")
        self.base = config["base_url"].rstrip("/")
        self.account_path = config["account_balance_path"]
        self.token_balance_path = config["token_balance_path"]

    def fetch(self) -> BalanceSnapshot:
        snap = BalanceSnapshot()
        snap.service = "openkey"
        snap.timestamp = datetime.now().isoformat()

        if not self.token:
            snap.error = "Bearer token not configured"
            return snap

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

        # fetch account balance
        url = self.base + self.account_path
        data = _get(url, headers)

        if "error" in data:
            snap.error = data["error"]
            return snap

        try:
            balance = data.get("balance", {})
            snap.currency = balance.get("currency", "USD")
            snap.remained_cash = float(balance.get("remained_cash", 0))
            snap.used_cash = float(balance.get("used_cash", 0))
        except (KeyError, ValueError, TypeError) as e:
            snap.error = f"Parse error (account): {e}"
            return snap

        # fetch token balance (consumable credits)
        url_tb = self.base + self.token_balance_path
        data_tb = _get(url_tb, headers)

        if "error" in data_tb:
            # token balance failed but account balance ok — still useful
            return snap

        try:
            tb = data_tb.get("balance", {})
            snap.token_remained_cash = float(tb.get("remained_cash", 0))
            snap.token_used_cash = float(tb.get("used_cash", 0))
        except (KeyError, ValueError, TypeError):
            pass  # token balance parse failure is non-fatal

        return snap


def fetch_all(deepseek: DeepSeekClient, openkey: OpenKeyClient) -> list[BalanceSnapshot]:
    """Fetch both services and return list of snapshots."""
    snapshots = []
    snapshots.append(deepseek.fetch())
    snapshots.append(openkey.fetch())
    return snapshots
