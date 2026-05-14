"""Rank and select papers for daily push."""

import logging
import re
from dataclasses import dataclass

from src.parse_papers import Paper

logger = logging.getLogger(__name__)

# High-value keywords for multimodal object tracking
_KEYWORDS = [
    "vision-language",
    "multimodal",
    "rgbt",
    "rgbd",
    "rgbl",
    "rgbe",
    "uav",
    "tracking",
    "prompt",
    "memory",
    "adapter",
    "mamba",
    "transformer",
    "foundation model",
    "embodied",
    "cross-modal",
    "fusion",
    "language model",
    "visual tracking",
]


def _keyword_score(text: str) -> float:
    """Score based on keyword presence."""
    text_lower = text.lower()
    score = 0.0
    for kw in _KEYWORDS:
        if kw in text_lower:
            score += 1.0
    return score


def _year_score(year: int | None) -> float:
    """Higher score for newer papers."""
    if year is None:
        return 0.0
    return max(0.0, (year - 2020) * 2.0)


def _code_score(code_url: str) -> float:
    """Bonus for having code."""
    return 3.0 if code_url else 0.0


def _url_quality_score(paper_url: str) -> float:
    """Score based on URL source quality."""
    url = paper_url.lower()
    if "arxiv.org" in url:
        return 2.0
    if "openreview.net" in url:
        return 1.8
    if "cvf" in url or "ieee" in url:
        return 1.5
    if "github.com" in url or "huggingface.co" in url:
        return 1.2
    if paper_url:
        return 0.5
    return 0.0


def compute_score(paper: Paper) -> float:
    """Compute a ranking score for a paper."""
    combined_text = f"{paper.title} {paper.category} {paper.source_section} {paper.raw_line}"
    return (
        _year_score(paper.year) * 2.0
        + _code_score(paper.code_url) * 1.5
        + _url_quality_score(paper.paper_url)
        + _keyword_score(combined_text)
    )


def rank_papers(papers: list[Paper], top_n: int = 5) -> list[Paper]:
    """Rank papers by relevance and return top N.

    Args:
        papers: List of Paper objects to rank.
        top_n: Number of top papers to return.

    Returns:
        Top N papers sorted by score descending.
    """
    if not papers:
        return []

    scored = [(compute_score(p), p) for p in papers]
    scored.sort(key=lambda x: x[0], reverse=True)

    selected = [p for _, p in scored[:top_n]]
    logger.info(
        "Ranked %d papers, selected top %d (scores: %s)",
        len(papers),
        len(selected),
        [f"{s:.1f}" for s, _ in scored[:top_n]],
    )
    return selected
