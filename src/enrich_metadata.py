"""Enrich paper metadata by fetching from arXiv API, Elsevier API, Semantic Scholar, or web pages."""

import logging
import re
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from src.config import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

_ARXIV_ABS_RE = re.compile(r"arxiv\.org/abs/(\d+\.\d+)")
_ARXIV_PDF_RE = re.compile(r"arxiv\.org/pdf/(\d+\.\d+)")
_SCIENCEDIRECT_RE = re.compile(r"sciencedirect\.com/science/article/(?:abs|pii)/\w+/(\S+)")
_PII_RE = re.compile(r"pii/(S\d{16,})")

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


def _extract_arxiv_id(url: str) -> str | None:
    """Extract arXiv paper ID from URL."""
    m = _ARXIV_ABS_RE.search(url)
    if m:
        return m.group(1)
    m = _ARXIV_PDF_RE.search(url)
    if m:
        return m.group(1)
    return None


def _extract_pii(url: str) -> str | None:
    """Extract PII from a ScienceDirect URL."""
    m = _PII_RE.search(url)
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


def _fetch_elsevier_metadata(pii: str, timeout: int) -> dict:
    """Fetch metadata from Elsevier API using PII.

    Returns DOI, title, journal info. No API key needed for basic metadata.
    """
    api_url = f"https://api.elsevier.com/content/article/pii/{pii}"
    try:
        resp = requests.get(
            api_url,
            headers={"Accept": "application/xml"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return {}

        # Parse XML response
        root = ET.fromstring(resp.text)
        ns = {
            "dc": "http://purl.org/dc/elements/1.1/",
            "prism": "http://prismstandard.org/namespaces/basic/2.0/",
        }

        result = {}
        doi_el = root.find(".//prism:doi", ns)
        if doi_el is not None and doi_el.text:
            result["doi"] = doi_el.text.strip()

        title_el = root.find(".//dc:title", ns)
        if title_el is not None and title_el.text:
            result["elsevier_title"] = re.sub(r"\s+", " ", title_el.text).strip()

        journal_el = root.find(".//prism:publicationName", ns)
        if journal_el is not None and journal_el.text:
            result["journal"] = journal_el.text.strip()

        date_el = root.find(".//prism:coverDate", ns)
        if date_el is not None and date_el.text:
            result["cover_date"] = date_el.text.strip()

        if result.get("doi"):
            logger.info("Elsevier API: DOI=%s, title=%s", result.get("doi"), result.get("elsevier_title", "")[:60])

        return result

    except Exception as e:
        logger.debug("Elsevier API failed for PII %s: %s", pii, e)
        return {}


def _fetch_doi_abstract(doi: str, timeout: int) -> dict:
    """Try to fetch abstract using DOI from multiple sources.

    Tries: CrossRef -> OpenAlex -> Semantic Scholar
    """
    result = {}

    # CrossRef
    try:
        resp = requests.get(f"https://api.crossref.org/works/{doi}", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json().get("message", {})
            abstract = data.get("abstract", "")
            if abstract:
                # Clean CrossRef abstract (often has JATS XML tags)
                abstract = re.sub(r"<[^>]+>", "", abstract).strip()
                if len(abstract) > 20:
                    result["abstract"] = abstract[:2000]
                    logger.info("Found abstract from CrossRef for DOI %s", doi)
                    return result
    except Exception as e:
        logger.debug("CrossRef lookup failed: %s", e)

    # OpenAlex
    try:
        resp = requests.get(f"https://api.openalex.org/works/doi:{doi}", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            inv = data.get("abstract_inverted_index")
            if inv:
                words = {}
                for word, positions in inv.items():
                    for pos in positions:
                        words[pos] = word
                abstract = " ".join(words[k] for k in sorted(words.keys()))
                if len(abstract) > 20:
                    result["abstract"] = abstract[:2000]
                    logger.info("Found abstract from OpenAlex for DOI %s", doi)
                    return result
    except Exception as e:
        logger.debug("OpenAlex lookup failed: %s", e)

    # Semantic Scholar
    try:
        resp = requests.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            params={"fields": "title,abstract"},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            abstract = data.get("abstract", "")
            if abstract and len(abstract) > 20:
                result["abstract"] = abstract[:2000]
                logger.info("Found abstract from Semantic Scholar for DOI %s", doi)
                return result
    except Exception as e:
        logger.debug("Semantic Scholar DOI lookup failed: %s", e)

    return result


def _fetch_semantic_scholar(title: str, url: str, timeout: int) -> dict:
    """Try to fetch abstract from Semantic Scholar API by paper title or URL."""
    result = {}

    # Try by URL first (more precise)
    try:
        resp = requests.get(
            f"https://api.semanticscholar.org/graph/v1/paper/URL:{url}",
            params={"fields": "title,abstract,year,authors,externalIds"},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("abstract"):
                result["abstract"] = data["abstract"][:2000]
            if data.get("title"):
                result["s2_title"] = data["title"]
            if data.get("year"):
                result["s2_year"] = data["year"]
            if result.get("abstract"):
                logger.info("Found paper on Semantic Scholar by URL: %s", data.get("title", "")[:60])
                return result
    except Exception as e:
        logger.debug("Semantic Scholar URL lookup failed: %s", e)

    # Try by title search
    try:
        resp = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": title, "limit": 1, "fields": "title,abstract,year,authors"},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            papers = data.get("data", [])
            if papers:
                paper = papers[0]
                if paper.get("abstract"):
                    result["abstract"] = paper["abstract"][:2000]
                if paper.get("title"):
                    result["s2_title"] = paper["title"]
                if paper.get("year"):
                    result["s2_year"] = paper["year"]
                if result.get("abstract"):
                    logger.info("Found paper on Semantic Scholar by title: %s", paper.get("title", "")[:60])
                    return result
    except Exception as e:
        logger.debug("Semantic Scholar title search failed: %s", e)

    return result


def _fetch_web_metadata(url: str, timeout: int) -> dict:
    """Fetch basic metadata from a web page using BeautifulSoup.

    Tries multiple strategies to find an abstract/summary:
    1. og:description meta tag
    2. description meta tag
    3. citation_abstract meta tag (IEEE, Springer)
    4. Abstract section in page body
    """
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers=_BROWSER_HEADERS,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        result = {}
        title_tag = soup.find("title")
        if title_tag and title_tag.text:
            result["web_title"] = title_tag.text.strip()[:200]

        # Strategy 1: og:description
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            result["web_description"] = og_desc["content"].strip()[:500]

        # Strategy 2: description meta
        if "web_description" not in result:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                result["web_description"] = meta_desc["content"].strip()[:500]

        # Strategy 3: citation_abstract (common in academic publishers)
        citation_abs = soup.find("meta", attrs={"name": "citation_abstract"})
        if citation_abs and citation_abs.get("content"):
            result["abstract"] = citation_abs["content"].strip()[:2000]

        # Strategy 4: Look for abstract section in page body
        if "abstract" not in result:
            for selector in [
                "div.abstract",
                "section.abstract",
                "div#abstract",
                "div.Abstracts",
                "div[role='doc-abstract']",
                "p.article-body__section-text",
            ]:
                el = soup.select_one(selector)
                if el:
                    text = el.get_text(separator=" ", strip=True)
                    if len(text) > 50:
                        result["abstract"] = text[:2000]
                        break

        return result

    except Exception as e:
        logger.warning("Failed to fetch web metadata for %s: %s", url[:80], e)
        return {}


def enrich_paper(paper: dict, timeout: int | None = None) -> dict:
    """Enrich a paper dict with metadata from external sources.

    Strategy:
    1. arXiv papers: fetch from arXiv API
    2. ScienceDirect papers: fetch DOI from Elsevier API, then search for abstract
    3. Other papers: scrape web page, then fallback to Semantic Scholar
    4. Final fallback: use DOI to search CrossRef/OpenAlex/Semantic Scholar

    Args:
        paper: Paper dict with at least 'paper_url' key.
        timeout: Request timeout in seconds.

    Returns:
        The same dict with additional metadata fields.
    """
    t = timeout or REQUEST_TIMEOUT
    url = paper.get("paper_url", "")
    title = paper.get("title", "")

    if not url:
        return paper

    # Strategy 1: arXiv
    arxiv_id = _extract_arxiv_id(url)
    if arxiv_id:
        meta = _fetch_arxiv_metadata(arxiv_id, t)
        paper.update(meta)
        return paper

    # Strategy 2: ScienceDirect -> Elsevier API
    pii = _extract_pii(url)
    if pii:
        logger.info("Detected ScienceDirect PII %s, using Elsevier API", pii)
        elsevier_meta = _fetch_elsevier_metadata(pii, t)
        paper.update(elsevier_meta)

        # If we got a DOI, try to find the abstract from other sources
        doi = paper.get("doi", "")
        if doi:
            doi_meta = _fetch_doi_abstract(doi, t)
            if doi_meta.get("abstract"):
                paper["abstract"] = doi_meta["abstract"]

    # Strategy 3: Generic web scraping
    if not paper.get("abstract"):
        web_meta = _fetch_web_metadata(url, t)
        paper.update(web_meta)

    # Strategy 4: Semantic Scholar fallback
    abstract = paper.get("abstract", "")
    if not abstract or len(abstract.strip()) < 20:
        logger.info("No abstract found yet, trying Semantic Scholar for '%s'", title[:60])
        s2_meta = _fetch_semantic_scholar(title, url, t)
        if s2_meta:
            if s2_meta.get("abstract") and (not abstract or len(abstract.strip()) < 20):
                paper["abstract"] = s2_meta["abstract"]
            if s2_meta.get("s2_title") and not paper.get("abstract_title"):
                paper["abstract_title"] = s2_meta["s2_title"]

    # Strategy 5: DOI-based lookup (if we have DOI but still no abstract)
    doi = paper.get("doi", "")
    abstract = paper.get("abstract", "")
    if doi and (not abstract or len(abstract.strip()) < 20):
        logger.info("Still no abstract, trying DOI-based lookup for %s", doi)
        doi_meta = _fetch_doi_abstract(doi, t)
        if doi_meta.get("abstract"):
            paper["abstract"] = doi_meta["abstract"]

    return paper


def enrich_papers(papers: list[dict], timeout: int | None = None) -> list[dict]:
    """Enrich a list of paper dicts with metadata."""
    for i, p in enumerate(papers):
        try:
            enrich_paper(p, timeout)
        except Exception as e:
            logger.warning("Failed to enrich paper %d: %s", i, e)
    return papers
