"""Test script for LLM interpretation of a single paper.

Usage:
    # By paper ID from sent_history.json
    python -m tests.test_llm_single --paper-id b71850f34b5aa49c

    # By title and URL
    python -m tests.test_llm_single --title "HATrack" --url "https://www.sciencedirect.com/science/article/abs/pii/S0957417426013394"

    # Skip metadata enrichment (faster, tests LLM only)
    python -m tests.test_llm_single --title "HATrack" --url "https://example.com/paper" --skip-enrich
"""

import argparse
import json
import logging
import sys
import time

from src.config import SENT_HISTORY_PATH
from src.enrich_metadata import enrich_paper
from src.llm.deepseek_provider import DeepSeekProvider
from src.summarize import summarize_paper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("test-llm-single")


def load_paper_from_history(paper_id: str) -> dict:
    """Load a paper entry from sent_history.json by its ID."""
    with open(SENT_HISTORY_PATH, "r", encoding="utf-8") as f:
        history = json.load(f)

    if paper_id not in history:
        print(f"Error: paper ID '{paper_id}' not found in sent_history.json")
        print(f"Available IDs: {', '.join(history.keys())}")
        sys.exit(1)

    entry = history[paper_id]
    return {
        "paper_id": paper_id,
        "title": entry["title"],
        "paper_url": entry["paper_url"],
    }


def build_paper_dict(title: str, url: str) -> dict:
    """Build a paper dict from title and URL."""
    return {
        "title": title,
        "paper_url": url,
    }


def main():
    parser = argparse.ArgumentParser(description="Test LLM interpretation of a single paper")
    parser.add_argument("--paper-id", help="Paper ID from sent_history.json")
    parser.add_argument("--title", help="Paper title")
    parser.add_argument("--url", help="Paper URL")
    parser.add_argument("--skip-enrich", action="store_true", help="Skip metadata enrichment")
    parser.add_argument("--raw", action="store_true", help="Print raw JSON without formatting")
    args = parser.parse_args()

    # Determine paper source
    if args.paper_id:
        paper = load_paper_from_history(args.paper_id)
    elif args.title and args.url:
        paper = build_paper_dict(args.title, args.url)
    else:
        parser.error("Provide --paper-id or both --title and --url")

    print("=" * 60)
    print(f"Title: {paper['title']}")
    print(f"URL:   {paper['paper_url']}")
    print("=" * 60)

    # Enrich metadata
    if not args.skip_enrich:
        print("\n[1/2] Fetching paper metadata...")
        t0 = time.time()
        enrich_paper(paper)
        elapsed = time.time() - t0
        print(f"  Done in {elapsed:.1f}s")
        if paper.get("abstract"):
            print(f"  Abstract: {paper['abstract'][:200]}...")
        else:
            print("  Abstract: (not found)")
    else:
        print("\n[1/2] Skipping metadata enrichment")

    # LLM summary
    print("\n[2/2] Calling LLM for interpretation...")
    t0 = time.time()
    provider = DeepSeekProvider()
    summary = summarize_paper(paper, provider)
    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s")

    # Output
    print("\n" + "=" * 60)
    print("LLM OUTPUT:")
    print("=" * 60)
    if args.raw:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        if summary.get("parse_error"):
            print("(LLM returned non-JSON, showing raw text)")
            print(summary.get("raw_text", ""))
        else:
            print(f"\n  中文标题: {summary.get('title_cn', 'N/A')}")
            print(f"  一句话总结: {summary.get('one_sentence_summary', 'N/A')}")
            print(f"  研究问题: {summary.get('research_problem', 'N/A')}")
            print(f"  方法概述: {summary.get('method_overview', 'N/A')}")
            innovations = summary.get("key_innovations", [])
            print(f"  创新点:")
            for inn in innovations:
                print(f"    - {inn}")
            print(f"  实验: {summary.get('experiments', 'N/A')}")
            limitations = summary.get("limitations", [])
            print(f"  局限性:")
            for lim in limitations:
                print(f"    - {lim}")
            print(f"  相关性: {summary.get('relevance_to_user', 'N/A')}")
            print(f"  阅读优先级: {summary.get('reading_priority', 'N/A')}")
            print(f"  推荐理由: {summary.get('why_read', 'N/A')}")

    print()


if __name__ == "__main__":
    main()
