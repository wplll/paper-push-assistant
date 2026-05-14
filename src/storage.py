"""Manage sent paper history for deduplication."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.config import SENT_HISTORY_PATH

logger = logging.getLogger(__name__)


def load_history(path: str | None = None) -> dict:
    """Load sent history from JSON file.

    Returns:
        Dict mapping paper_id -> metadata dict.
    """
    p = Path(path or SENT_HISTORY_PATH)
    if not p.exists():
        logger.info("No history file found at %s, starting fresh", p)
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded %d entries from history", len(data))
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load history from %s: %s", p, e)
        return {}


def save_history(history: dict, path: str | None = None) -> None:
    """Save sent history to JSON file.

    Args:
        history: Dict mapping paper_id -> metadata.
        path: Override file path.
    """
    p = Path(path or SENT_HISTORY_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d entries to history at %s", len(history), p)


def mark_sent(history: dict, paper_id: str, title: str, paper_url: str) -> dict:
    """Mark a paper as sent in the history.

    Args:
        history: The history dict to update.
        paper_id: Stable paper identifier.
        title: Paper title for logging.
        paper_url: Paper URL for logging.

    Returns:
        Updated history dict.
    """
    history[paper_id] = {
        "title": title,
        "paper_url": paper_url,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    return history


def filter_unsent(papers: list, history: dict) -> list:
    """Filter out papers that have already been sent.

    Args:
        papers: List of Paper objects.
        history: The sent history dict.

    Returns:
        List of Paper objects not yet in history.
    """
    unsent = [p for p in papers if p.paper_id not in history]
    logger.info(
        "Filtered: %d total, %d already sent, %d unsent",
        len(papers),
        len(papers) - len(unsent),
        len(unsent),
    )
    return unsent
