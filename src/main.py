"""Main entry point for the MMOT Paper Pusher."""

import logging
import sys

from src.config import (
    MIN_PAPERS_PER_DAY,
    PAPERS_PER_DAY,
    SKIP_EMPTY_EMAIL,
)
from src.email_sender import build_subject, send_email
from src.enrich_metadata import enrich_papers
from src.fetch_readme import fetch_readme
from src.llm.deepseek_provider import DeepSeekProvider
from src.parse_papers import Paper, parse_papers
from src.ranker import rank_papers
from src.render_email import render_email_html, render_empty_email_html
from src.storage import filter_unsent, load_history, mark_sent, save_history
from src.summarize import summarize_papers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mmot-pusher")


def _paper_to_dict(paper: Paper) -> dict:
    """Convert a Paper dataclass to a plain dict for enrichment/summarization."""
    return {
        "title": paper.title,
        "year": paper.year,
        "category": paper.category,
        "paper_url": paper.paper_url,
        "code_url": paper.code_url,
        "source_section": paper.source_section,
        "raw_line": paper.raw_line,
        "paper_id": paper.paper_id,
    }


def run() -> int:
    """Run the full paper push pipeline.

    Returns:
        0 on success, 1 on error.
    """
    logger.info("=" * 60)
    logger.info("MMOT Paper Pusher - Starting run")
    logger.info("=" * 60)

    # Step 1: Fetch README
    try:
        markdown = fetch_readme()
        logger.info("✅ README fetched successfully")
    except Exception as e:
        logger.error("❌ Failed to fetch README: %s", e)
        return 1

    # Step 2: Parse papers
    papers = parse_papers(markdown)
    logger.info("✅ Parsed %d papers from README", len(papers))
    if not papers:
        logger.warning("No papers parsed from README. Check the source URL and parser logic.")
        return 0

    # Step 3: Load history and filter unsent
    history = load_history()
    unsent_papers = filter_unsent(papers, history)
    logger.info("✅ Unsent papers: %d", len(unsent_papers))

    # Step 4: Handle empty case
    if not unsent_papers:
        logger.info("No unsent papers available.")
        if SKIP_EMPTY_EMAIL:
            logger.info("SKIP_EMPTY_EMAIL=true, skipping email.")
            return 0
        else:
            html = render_empty_email_html()
            subject = build_subject(0)
            send_email(subject, html)
            return 0

    # Step 5: Rank and select
    selected_papers = rank_papers(unsent_papers, top_n=PAPERS_PER_DAY)
    if len(selected_papers) < MIN_PAPERS_PER_DAY:
        logger.warning(
            "Only %d papers available (minimum requested: %d). Sending what we have.",
            len(selected_papers),
            MIN_PAPERS_PER_DAY,
        )
    logger.info("✅ Selected %d papers for today", len(selected_papers))

    # Step 6: Enrich metadata
    paper_dicts = [_paper_to_dict(p) for p in selected_papers]
    logger.info("Enriching metadata...")
    enrich_papers(paper_dicts)
    logger.info("✅ Metadata enrichment complete")

    # Step 7: Generate summaries via LLM
    logger.info("Generating LLM summaries...")
    try:
        provider = DeepSeekProvider()
        summarize_papers(paper_dicts, provider)
        logger.info("✅ LLM summaries generated")
    except Exception as e:
        logger.error("❌ LLM summarization failed: %s", e)
        logger.info("Continuing without summaries...")

    # Step 8: Render email
    total_sent = len(history)
    html = render_email_html(paper_dicts, total_sent=total_sent + len(selected_papers))
    subject = build_subject(len(selected_papers))
    logger.info("✅ Email rendered")

    # Step 9: Send email
    sent_ok = send_email(subject, html)
    if sent_ok:
        logger.info("✅ Email sent successfully")
    else:
        logger.error("❌ Email sending failed")
        # Still update history to avoid infinite retry on bad email config
        # The user can manually clear history if needed

    # Step 10: Update sent history
    for paper in selected_papers:
        mark_sent(history, paper.paper_id, paper.title, paper.paper_url)
    save_history(history)
    logger.info("✅ History updated: %d total entries", len(history))

    logger.info("=" * 60)
    logger.info("Run complete. Papers sent: %d", len(selected_papers))
    logger.info("=" * 60)
    return 0


def main():
    """CLI entry point."""
    sys.exit(run())


if __name__ == "__main__":
    main()
