# Notion + Google Calendar Bot

This Python bot monitors a Notion database for tasks and syncs "In Progress" tasks to Google Calendar.

## 🛠 Setup

1. Create a Notion integration and share your database with it
2. Create a Google Cloud Project and download `credentials.json` (OAuth Client ID for Desktop App)
3. Fill out `.env` with your Notion token and database ID

## ▶️ Run

```bash
pip install -r requirements.txt
python main.py
```

This script checks Notion every minute and starts/ends events accordingly.
