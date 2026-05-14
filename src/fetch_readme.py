"""Fetch the raw README content from GitHub."""

import logging

import requests

from src.config import README_RAW_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def fetch_readme(url: str | None = None, timeout: int | None = None) -> str:
    """Download raw README markdown from GitHub.

    Args:
        url: Override URL. Defaults to config README_RAW_URL.
        timeout: Request timeout in seconds. Defaults to config REQUEST_TIMEOUT.

    Returns:
        The raw markdown text of the README.

    Raises:
        requests.RequestException: On network or HTTP errors.
    """
    target = url or README_RAW_URL
    t = timeout or REQUEST_TIMEOUT
    logger.info("Fetching README from %s", target)
    resp = requests.get(target, timeout=t, headers={"User-Agent": "mmot-paper-pusher/1.0"})
    resp.raise_for_status()
    logger.info("README fetched successfully (%d bytes)", len(resp.text))
    return resp.text
