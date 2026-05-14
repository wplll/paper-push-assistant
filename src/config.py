"""Centralized configuration from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# DeepSeek API
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# SMTP
SMTP_HOST: str = os.getenv("SMTP_HOST", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
EMAIL_TO: str = os.getenv("EMAIL_TO", "")

# Push settings
PAPERS_PER_DAY: int = int(os.getenv("PAPERS_PER_DAY", "5"))
MIN_PAPERS_PER_DAY: int = int(os.getenv("MIN_PAPERS_PER_DAY", "3"))
SKIP_EMPTY_EMAIL: bool = os.getenv("SKIP_EMPTY_EMAIL", "true").lower() == "true"
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

# Paper source
README_RAW_URL: str = os.getenv(
    "README_RAW_URL",
    "https://raw.githubusercontent.com/983632847/Awesome-Multimodal-Object-Tracking/main/README.md",
)

# Storage
SENT_HISTORY_PATH: str = os.getenv(
    "SENT_HISTORY_PATH",
    str(PROJECT_ROOT / "data" / "sent_history.json"),
)
