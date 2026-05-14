"""Parse paper entries from the Awesome-Multimodal-Object-Tracking README.

The README has several distinct formats:
1. Regular papers: `- **MethodName:** Authors.<br />` + next line `"Title." Venue (Year).` + `[[paper](url)]`
2. Survey papers: `- Authors.<br />` + next line `"Title." Venue (Year).` + `[[paper](url)]`
3. News/highlights: `- 2026.01.23: We Released... [[Project](url)]`
4. TOC entries: `- [Section](#anchor)`
5. Dataset tables: `| Dataset | Pub. | ...`
"""

import hashlib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Link patterns
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_YEAR_RE = re.compile(r"\b(20[12]\d)\b")
_QUOTED_TITLE_RE = re.compile(r'"([^"]+)"')

# Known paper / code link keywords
_PAPER_KEYWORDS = {"paper", "arxiv", "pdf", "abs", "openreview", "cvf", "html", "book"}
_CODE_KEYWORDS = {"code", "github", "project", "homepage", "page", "demo", "code "}

# Non-paper section names to skip
_NON_PAPER_SECTIONS = {"contents", "citation", "table of contents"}


@dataclass
class Paper:
    title: str
    year: int | None = None
    category: str = ""
    paper_url: str = ""
    code_url: str = ""
    source_section: str = ""
    raw_line: str = ""
    paper_id: str = ""

    def __post_init__(self):
        if not self.paper_id:
            self.paper_id = compute_paper_id(self.title, self.paper_url)


def normalize_for_id(text: str) -> str:
    """Normalize text for stable ID generation."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[*_`#\[\]()]", "", text)
    return text


def compute_paper_id(title: str, paper_url: str) -> str:
    """Compute a stable SHA-256 ID for a paper."""
    norm_title = normalize_for_id(title)
    norm_url = paper_url.rstrip("/").lower()
    raw = f"{norm_title}||{norm_url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _classify_link(label: str, url: str) -> str:
    """Classify a link as 'paper' or 'code' based on label and URL."""
    label_lower = label.lower().strip()
    url_lower = url.lower()

    if label_lower in _PAPER_KEYWORDS:
        return "paper"
    if label_lower in _CODE_KEYWORDS:
        return "code"

    if any(kw in url_lower for kw in ("arxiv.org", ".pdf", "openreview.net", "cvf", "aaai.org", "neurips.cc", "icml.cc", "springer.com", "sciencedirect.com", "ieeexplore.ieee.org", "ecva.net", "acm.org")):
        return "paper"
    if any(kw in url_lower for kw in ("github.com", "gitlab.com", "huggingface.co", "sites.google.com")):
        return "code"

    return "paper"  # default


def _extract_year(text: str) -> int | None:
    """Extract the most likely publication year from text."""
    matches = _YEAR_RE.findall(text)
    if matches:
        return max(int(y) for y in matches)
    return None


def _clean_title(text: str) -> str:
    """Remove markdown artifacts and extra whitespace from a title."""
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove emoji codes like :boom:, :fire:, :collision:
    text = re.sub(r":[a-z_]+:", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[\-|]+$", "", text).strip()
    return text


def _parse_links_from_text(text: str) -> list[tuple[str, str]]:
    """Extract all markdown links from text."""
    return _LINK_RE.findall(text)


def _parse_line_links(text: str) -> tuple[str, str]:
    """Extract paper_url and code_url from text.

    Returns (paper_url, code_url).
    """
    links = _parse_links_from_text(text)
    paper_url = ""
    code_url = ""

    for label, url in links:
        kind = _classify_link(label, url)
        if kind == "paper" and not paper_url:
            paper_url = url
        elif kind == "code" and not code_url:
            code_url = url

    if not paper_url and links:
        paper_url = links[0][1]
    if not code_url and len(links) > 1:
        for label, url in links:
            if url != paper_url:
                code_url = url
                break

    return paper_url, code_url


def _is_paper_entry_start(line: str) -> bool:
    """Check if a line starts a paper entry (the line with authors).

    Paper entries start with `- ` or `:boom:` and contain author-like text
    followed by `<br />` or a quoted title on this or the next line.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Must be a list item (possibly with emoji prefix)
    if not re.match(r"^[-*+]\s+", stripped) and not re.match(r"^:[a-z_]+:", stripped):
        return False

    # Skip TOC entries: `- [Section](#anchor)`
    if re.match(r"^[-*+]\s+\[[^\]]+\]\(#[^)]+\)\s*$", stripped):
        return False

    # Skip date-prefixed news: `- 2026.01.23: text`
    if re.match(r"^[-*+]\s+\d{4}\.\d{2}\.\d{2}:", stripped):
        return False

    # Skip table rows
    if stripped.startswith("|"):
        return False

    # Skip HTML-heavy lines
    if re.search(r"<(div|p|img|table|tr|td|th)\b", stripped, re.IGNORECASE):
        return False

    # Should contain either <br /> (author line) or a quoted title
    has_br = "<br" in stripped.lower()
    has_quoted = bool(_QUOTED_TITLE_RE.search(stripped))
    has_link = bool(_LINK_RE.search(stripped))

    # Author line: has <br /> and possibly links
    if has_br:
        return True

    # Quoted title with links
    if has_quoted and has_link:
        return True

    # Single-line paper entry with links (must have paper-like link)
    if has_link:
        links = _parse_links_from_text(stripped)
        for label, url in links:
            kind = _classify_link(label, url)
            if kind == "paper":
                return True

    return False


def _is_continuation_line(line: str) -> bool:
    """Check if a line is a continuation of a multi-line paper entry.

    Continuation lines are indented and contain links or quoted text.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Must be indented (continuation of a list item)
    if not line.startswith("  "):
        return False

    # Should contain a link or quoted title
    has_link = bool(_LINK_RE.search(stripped))
    has_quoted = bool(_QUOTED_TITLE_RE.search(stripped))

    return has_link or has_quoted


def _extract_title_from_entry(entry_text: str) -> str:
    """Extract paper title from a combined multi-line entry.

    Strategy:
    1. Look for bold method name: **MethodName:** (most recognizable identifier)
    2. Look for quoted title: "Title in Quotes"
    3. Fall back to first non-keyword link text
    """
    # Try bold method name first: **MethodName:** or **MethodName**:**
    # This is the most recognizable identifier for papers in this README
    bold_match = re.search(r"\*\*([^*:]+?):?\*\*\s*:?", entry_text)
    if bold_match:
        name = _clean_title(bold_match.group(1))
        if len(name) > 2:
            return name

    # Try quoted title
    quoted = _QUOTED_TITLE_RE.findall(entry_text)
    if quoted:
        for q in quoted:
            cleaned = _clean_title(q)
            cleaned = cleaned.rstrip(".")
            if len(cleaned) > 5:
                return cleaned

    # Fall back to first non-keyword link label
    links = _parse_links_from_text(entry_text)
    for label, url in links:
        label_clean = label.strip()
        if label_clean.lower() not in _PAPER_KEYWORDS | _CODE_KEYWORDS and len(label_clean) > 3:
            return _clean_title(label_clean)

    # Last resort: strip links and take text
    stripped = _LINK_RE.sub("", entry_text)
    stripped = re.sub(r"<br\s*/?>", " ", stripped)
    stripped = re.sub(r"[\-*|>:]", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if len(stripped) > 5:
        return _clean_title(stripped[:120])

    return ""


def parse_papers(markdown: str) -> list[Paper]:
    """Parse all paper entries from README markdown.

    Handles multi-line entries where authors are on one line and
    title/links on subsequent indented lines.

    Args:
        markdown: The raw README content.

    Returns:
        List of Paper objects.
    """
    papers: list[Paper] = []
    current_section = ""
    current_subsection = ""  # e.g., "2026", "2025"
    in_datasets = False
    in_non_paper_section = False
    lines = markdown.splitlines()

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # Track section headers
        header_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if header_match:
            level = len(header_match.group(1))
            header_text = _clean_title(header_match.group(2))

            if level <= 2:
                current_section = header_text
                in_non_paper_section = header_text.lower() in _NON_PAPER_SECTIONS
                in_datasets = False
                current_subsection = ""
            elif level == 3:
                if "dataset" in header_text.lower():
                    in_datasets = True
                else:
                    in_datasets = False
            elif level == 4:
                # Year subsection like "#### 2026"
                year_match = re.match(r"^(20[12]\d)$", header_text)
                if year_match:
                    current_subsection = header_text

            i += 1
            continue

        # Skip non-paper sections and datasets
        if in_non_paper_section or in_datasets:
            i += 1
            continue

        # Skip table rows
        if stripped.startswith("|"):
            i += 1
            continue

        # Check for paper entry start
        if _is_paper_entry_start(stripped):
            # Collect multi-line entry
            entry_lines = [lines[i]]
            j = i + 1
            while j < len(lines) and _is_continuation_line(lines[j]):
                entry_lines.append(lines[j])
                j += 1

            entry_text = "\n".join(entry_lines)

            try:
                title = _extract_title_from_entry(entry_text)
                if not title or len(title) < 3:
                    i = j
                    continue

                paper_url, code_url = _parse_line_links(entry_text)

                # Must have at least a paper URL
                if not paper_url:
                    i = j
                    continue

                # Extract year from entry text, subsection, or section
                year = _extract_year(entry_text)
                if year is None and current_subsection:
                    year = _extract_year(current_subsection)

                # Determine category
                category = current_section
                if current_subsection:
                    category = f"{current_section} ({current_subsection})"

                paper = Paper(
                    title=title,
                    year=year,
                    category=category,
                    paper_url=paper_url,
                    code_url=code_url,
                    source_section=current_section,
                    raw_line=entry_text[:300],
                )
                papers.append(paper)

            except Exception as e:
                logger.warning("Failed to parse entry at line %d: %s", i, e)

            i = j
            continue

        i += 1

    logger.info("Parsed %d papers from README", len(papers))
    return papers
