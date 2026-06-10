# API Monitor

macOS desktop widget that tracks your **DeepSeek** and **OpenKey** API balances in real-time, showing token consumption speed and remaining money.

## Features

- Real-time balance display for DeepSeek (CNY) and OpenKey (USD)
- Token consumption rate calculation (money/sec, tokens/sec)
- macOS-native rounded corners via PyObjC
- Frameless draggable window, always on top
- Manual refresh button + auto-refresh every 30s
- Status indicator: green = all OK, red = error
- Right-click context menu, `Cmd+R` refresh, `Esc` close

## Requirements

- macOS (PyObjC for native rounded corners)
- Python 3.10+
- `requests`

## Quick Start

```bash
git clone https://github.com/czc0407/api-monitor.git
cd api-monitor
pip install -r requirements.txt
cp config.example.json config.json
```

Edit `config.json` with your API keys:

```json
{
  "deepseek": {
    "api_key": "sk-..."
  },
  "openkey": {
    "bearer_token": "sk-..."
  }
}
```

Then run:

```bash
python3 api_monitor.py
```

## Configuration

| Key | Description | Default |
|---|---|---|
| `deepseek.api_key` | DeepSeek API key | — |
| `openkey.bearer_token` | OpenKey bearer token | — |
| `pricing.price_per_1M_tokens_cny` | DeepSeek blended price (¥/1M tokens) | 2.5 |
| `pricing.price_per_1M_tokens_usd` | OpenKey blended price ($/1M tokens) | 0.5 |
| `refresh_interval_seconds` | Auto-refresh interval | 30 |

## Project Structure

```
api_monitor.py       # Entry point + timer loop
api_clients.py       # DeepSeek & OpenKey HTTP clients
rate_tracker.py      # Consumption rate calculation
widget_ui.py         # tkinter desktop widget UI
config.json          # API keys (gitignored)
config.example.json  # Template config
requirements.txt     # requests
```

## Controls

| Action | Method |
|---|---|
| Refresh | Click ↻ / `Cmd+R` |
| Move | Drag title bar |
| Quit | Click ✕ / `Esc` / right-click → Quit |
