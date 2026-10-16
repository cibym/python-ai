import os
import csv
import json
from pathlib import Path

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
RESEND_KEY = os.environ.get("RESEND_API_KEY")
RECIPIENT_EMAIL = os.environ.get("MY_EMAIL")

if not all([GEMINI_KEY, RESEND_KEY, RECIPIENT_EMAIL]):
    raise ValueError("Missing required environment variables: GEMINI_API_KEY, RESEND_API_KEY, MY_EMAIL")

CONFIG_DIR = Path("config")

def load_channels(file_path: Path = CONFIG_DIR / "channels.json") -> list:
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_portfolio(file_path: Path = CONFIG_DIR / "portfolio.csv") -> str:
    if not file_path.exists():
        return "No holdings specified."

    portfolio_items = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get("ticker", "").strip()
            name = row.get("name", "").strip()
            if ticker:
                portfolio_items.append(f"{ticker} ({name})" if name else ticker)

    return ", ".join(portfolio_items) if portfolio_items else "No holdings specified."
