"""Tests for paper ranking logic."""

import pytest

from src.parse_papers import Paper
from src.ranker import compute_score, rank_papers


def _make_paper(title="", year=None, code_url="", paper_url="", category="", raw_line=""):
    return Paper(
        title=title,
        year=year,
        code_url=code_url,
        paper_url=paper_url,
        category=category,
        raw_line=raw_line,
    )


class TestComputeScore:
    def test_newer_year_scores_higher(self):
        p2025 = _make_paper(year=2025)
        p2022 = _make_paper(year=2022)
        assert compute_score(p2025) > compute_score(p2022)

    def test_code_bonus(self):
        with_code = _make_paper(code_url="https://github.com/example")
        without_code = _make_paper()
        assert compute_score(with_code) > compute_score(without_code)

    def test_arxiv_url_bonus(self):
        arxiv = _make_paper(paper_url="https://arxiv.org/abs/2501.12345")
        other = _make_paper(paper_url="https://example.com/paper.pdf")
        assert compute_score(arxiv) > compute_score(other)

    def test_keyword_bonus(self):
        kw = _make_paper(title="Multimodal RGBT Tracking with Transformer", category="RGBT")
        plain = _make_paper(title="Generic Method", category="Other")
        assert compute_score(kw) > compute_score(plain)

    def test_vision_language_keyword(self):
        vl = _make_paper(title="Vision-Language Tracking", raw_line="vision-language tracker 2025")
        basic = _make_paper(title="Basic Tracker")
        assert compute_score(vl) > compute_score(basic)


class TestRankPapers:
    def test_returns_top_n(self):
        papers = [_make_paper(title=f"Paper {i}", year=2020 + i) for i in range(10)]
        result = rank_papers(papers, top_n=5)
        assert len(result) == 5

    def test_newer_papers_ranked_first(self):
        papers = [
            _make_paper(title="Old Paper", year=2021),
            _make_paper(title="New Paper", year=2025, code_url="https://github.com/x"),
        ]
        result = rank_papers(papers, top_n=2)
        assert result[0].title == "New Paper"

    def test_empty_input(self):
        result = rank_papers([], top_n=5)
        assert result == []

    def test_fewer_than_requested(self):
        papers = [_make_paper(title="Only Paper")]
        result = rank_papers(papers, top_n=5)
        assert len(result) == 1

    def test_code_paper_outranks_no_code(self):
        """A 2024 paper with code should rank higher than a 2024 paper without code."""
        with_code = _make_paper(
            title="Paper with Code", year=2024,
            code_url="https://github.com/example",
            paper_url="https://arxiv.org/abs/2401.00001",
        )
        no_code = _make_paper(
            title="Paper without Code", year=2024,
            paper_url="https://arxiv.org/abs/2401.00002",
        )
        result = rank_papers([no_code, with_code], top_n=2)
        assert result[0].title == "Paper with Code"
