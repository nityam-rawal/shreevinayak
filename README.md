# Apni Dukaan

Local Indian shop manager web app.

## Start

Option 1:

```powershell
python trial.py
```

Then open:

- `http://127.0.0.1:8000/login`
- On phone on same Wi-Fi: `http://YOUR_PC_IP:8000/login`

Option 2:

- Double-click `start_shop.bat`

## Deploy

The project is deployment-ready for a Python host.

Files added:

- `requirements.txt`
- `Procfile`
- `.gitignore`

Example host:

- Render
- Railway

`Procfile` uses:

```text
web: gunicorn trial:app
```

## Login

- Default PIN: `1234`

## Features

- Inventory
- Purchase / restock
- Sales invoice
- Expense entry
- Customer due / vendor due
- Daily dashboard
- CSV export
- DB backup
- Hindi / English toggle
- Quick Hinglish entry
- Browser voice input support
- Printable invoice page

## Telegram

Optional:

1. Set `TELEGRAM_BOT_TOKEN` in your environment.
2. Open app settings and set `telegram_chat_id`.
3. Enable Telegram in settings.

## Notes

- Data is stored in `shop_manager.db`
- App must keep running while you use it from phone/browser
- Best browser for voice input: Chrome on Android
- Native APK is not built yet on this machine because Java/Gradle/Android SDK are not installed
