"""Enrich paper metadata by fetching from arXiv API or web pages."""

import logging
import re
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from src.config import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

_ARXIV_ABS_RE = re.compile(r"arxiv\.org/abs/(\d+\.\d+)")
_ARXIV_PDF_RE = re.compile(r"arxiv\.org/pdf/(\d+\.\d+)")


def _extract_arxiv_id(url: str) -> str | None:
    """Extract arXiv paper ID from URL."""
    m = _ARXIV_ABS_RE.search(url)
    if m:
        return m.group(1)
    m = _ARXIV_PDF_RE.search(url)
    if m:
        return m.group(1)
    return None


def _fetch_arxiv_metadata(arxiv_id: str, timeout: int) -> dict:
    """Fetch metadata from arXiv API."""
    api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        resp = requests.get(api_url, timeout=timeout)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        entry = root.find("atom:entry", ns)
        if entry is None:
            return {}

        title_el = entry.find("atom:title", ns)
        abstract_el = entry.find("atom:summary", ns)
        published_el = entry.find("atom:published", ns)
        updated_el = entry.find("atom:updated", ns)

        authors = []
        for author_el in entry.findall("atom:author", ns):
            name_el = author_el.find("atom:name", ns)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        result = {}
        if title_el is not None and title_el.text:
            result["abstract_title"] = re.sub(r"\s+", " ", title_el.text).strip()
        if abstract_el is not None and abstract_el.text:
            result["abstract"] = re.sub(r"\s+", " ", abstract_el.text).strip()
        if published_el is not None and published_el.text:
            result["published"] = published_el.text.strip()[:10]
        if updated_el is not None and updated_el.text:
            result["updated"] = updated_el.text.strip()[:10]
        if authors:
            result["authors"] = authors
        result["arxiv_id"] = arxiv_id

        return result

    except Exception as e:
        logger.warning("Failed to fetch arXiv metadata for %s: %s", arxiv_id, e)
        return {}


def _fetch_web_metadata(url: str, timeout: int) -> dict:
    """Fetch basic metadata from a web page using BeautifulSoup."""
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "mmot-paper-pusher/1.0"},
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        result = {}
        title_tag = soup.find("title")
        if title_tag and title_tag.text:
            result["web_title"] = title_tag.text.strip()[:200]

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result["web_description"] = meta_desc["content"].strip()[:500]

        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            result["web_description"] = og_desc["content"].strip()[:500]

        return result

    except Exception as e:
        logger.warning("Failed to fetch web metadata for %s: %s", url[:80], e)
        return {}


def enrich_paper(paper: dict, timeout: int | None = None) -> dict:
    """Enrich a paper dict with metadata from external sources.

    Args:
        paper: Paper dict with at least 'paper_url' key.
        timeout: Request timeout in seconds.

    Returns:
        The same dict with additional metadata fields.
    """
    t = timeout or REQUEST_TIMEOUT
    url = paper.get("paper_url", "")

    if not url:
        return paper

    arxiv_id = _extract_arxiv_id(url)
    if arxiv_id:
        meta = _fetch_arxiv_metadata(arxiv_id, t)
        paper.update(meta)
    else:
        meta = _fetch_web_metadata(url, t)
        paper.update(meta)

    return paper


def enrich_papers(papers: list[dict], timeout: int | None = None) -> list[dict]:
    """Enrich a list of paper dicts with metadata."""
    for i, p in enumerate(papers):
        try:
            enrich_paper(p, timeout)
        except Exception as e:
            logger.warning("Failed to enrich paper %d: %s", i, e)
    return papers
