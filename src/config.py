"""Configuration settings for the portfolio risk alert system."""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3.2")
DEFAULT_ISSUER_LIMIT = float(os.getenv("ISSUER_LIMIT", 8.0))
DEFAULT_SECTOR_LIMIT = float(os.getenv("SECTOR_LIMIT", 25.0))
DEFAULT_GEOGRAPHY_LIMIT = float(os.getenv("GEOGRAPHY_LIMIT", 70.0))
CORRELATION_THRESHOLD = float(os.getenv("CORRELATION_THRESHOLD", 0.85))

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
NOTIFICATION_WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
