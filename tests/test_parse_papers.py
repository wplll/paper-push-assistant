"""Tests for paper parsing logic."""

import pytest

from src.parse_papers import Paper, _extract_year, compute_paper_id, parse_papers


class TestExtractYear:
    def test_extracts_2025(self):
        assert _extract_year("Some paper 2025 title") == 2025

    def test_extracts_max_year(self):
        assert _extract_year("2023 vs 2024 comparison") == 2024

    def test_returns_none_when_no_year(self):
        assert _extract_year("No year here") is None

    def test_ignores_old_years(self):
        assert _extract_year("Since 1999 we have") is None


class TestComputePaperId:
    def test_stable_id(self):
        id1 = compute_paper_id("Test Paper", "https://arxiv.org/abs/1234.5678")
        id2 = compute_paper_id("Test Paper", "https://arxiv.org/abs/1234.5678")
        assert id1 == id2

    def test_different_for_different_titles(self):
        id1 = compute_paper_id("Paper A", "https://arxiv.org/abs/1234.5678")
        id2 = compute_paper_id("Paper B", "https://arxiv.org/abs/1234.5678")
        assert id1 != id2

    def test_normalizes_case(self):
        id1 = compute_paper_id("Test Paper", "https://arxiv.org/abs/1234.5678")
        id2 = compute_paper_id("test paper", "https://arxiv.org/abs/1234.5678")
        assert id1 == id2

    def test_normalizes_trailing_slash(self):
        id1 = compute_paper_id("Test", "https://arxiv.org/abs/1234.5678")
        id2 = compute_paper_id("Test", "https://arxiv.org/abs/1234.5678/")
        assert id1 == id2


class TestParsePapers:
    """Test with realistic README-like markdown."""

    SAMPLE_MD = """
## Survey

- Pengyu Zhang, Dong Wang, Huchuan Lu.<br />
  "Multi-modal Visual Tracking: Review and Experimental Comparison." ArXiv (2022).
  [[paper](https://arxiv.org/abs/2012.04176)]

## Embodied Visual Tracking
### Papers
#### 2026
- **AdaTracker:** Kui Wu, Hao Chen, Jinzhu Han.<br />
  "AdaTracker: Learning Adaptive In-Context Policy for Cross-Embodiment Active Visual Tracking." IEEE RA-L (2026).
  [[paper](https://arxiv.org/abs/2604.20305)]

#### 2025
- **TrackVLA:** Shaoan Wang, Jiazhao Zhang.<br />
  "TrackVLA: Embodied Visual Tracking in the Wild." CoRL (2025).
  [[paper](https://arxiv.org/abs/2505.23189)]
  [[project](https://pku-epic.github.io/TrackVLA-web/)]
  [[code](https://github.com/wsakobe/TrackVLA)]

## Vision-Language Tracking
### Papers
#### 2026
- **SVLTrack:** Yaozong Zheng, Bineng Zhong.<br />
  "Learning to Track Instance from Single Nature Language Description." CVPR (2026).
  [[paper](https://arxiv.org/abs/2605.07064)]

- **VL-UniTrack:** Boyue Xu, Ruichao Hou.<br />
  "VL-UniTrack: A Unified Framework with Visual-Language Prompts for UAV-Ground Visual Tracking." ArXiv (2026).
  [[paper](https://arxiv.org/abs/2605.04574)]
  [[code](https://github.com/xuboyue1999/VL-UniTrack.git)]

## Contents
- [Survey](#survey)
- [Embodied Visual Tracking](#embodied-visual-tracking)
- [Vision-Language Tracking](#vision-language-tracking)

## :collision: Highlights
- 2026.01.23: We Released UAV-Anti-UAV dataset V1.5 ([Project](https://github.com/example))
- 2025.04.02: We Released UW-COT220 & VL-SAM2 ([Project](https://github.com/example2))
"""

    def test_parses_real_papers(self):
        papers = parse_papers(self.SAMPLE_MD)
        titles = [p.title for p in papers]
        # All 5 papers should be found
        assert len(papers) == 5
        assert any("Multi-modal Visual Tracking" in t for t in titles)
        assert any("AdaTracker" in t for t in titles)
        assert any("TrackVLA" in t for t in titles)
        assert any("SVLTrack" in t for t in titles)
        assert any("VL-UniTrack" in t for t in titles)

    def test_does_not_parse_toc(self):
        papers = parse_papers(self.SAMPLE_MD)
        titles = [p.title for p in papers]
        assert not any("Embodied Visual Tracking" == t for t in titles)

    def test_does_not_parse_news(self):
        papers = parse_papers(self.SAMPLE_MD)
        titles = [p.title for p in papers]
        assert not any("Released" in t for t in titles)

    def test_extracts_years(self):
        papers = parse_papers(self.SAMPLE_MD)
        ada = [p for p in papers if "AdaTracker" in p.title][0]
        assert ada.year == 2026
        trackvla = [p for p in papers if "TrackVLA" in p.title][0]
        assert trackvla.year == 2025

    def test_extracts_paper_urls(self):
        papers = parse_papers(self.SAMPLE_MD)
        ada = [p for p in papers if "AdaTracker" in p.title][0]
        assert "arxiv.org/abs/2604.20305" in ada.paper_url

    def test_extracts_code_urls(self):
        papers = parse_papers(self.SAMPLE_MD)
        trackvla = [p for p in papers if "TrackVLA" in p.title][0]
        assert "github.com/wsakobe/TrackVLA" in trackvla.code_url

    def test_extracts_category(self):
        papers = parse_papers(self.SAMPLE_MD)
        ada = [p for p in papers if "AdaTracker" in p.title][0]
        assert "Embodied Visual Tracking" in ada.category
        svl = [p for p in papers if "SVLTrack" in p.title][0]
        assert "Vision-Language Tracking" in svl.category

    def test_handles_empty_input(self):
        papers = parse_papers("")
        assert papers == []

    def test_paper_id_generated(self):
        papers = parse_papers(self.SAMPLE_MD)
        for p in papers:
            assert p.paper_id
            assert len(p.paper_id) == 16

    def test_paper_without_code(self):
        papers = parse_papers(self.SAMPLE_MD)
        no_code = [p for p in papers if not p.code_url]
        assert len(no_code) >= 1

    def test_no_dataset_table_rows(self):
        """Dataset tables should not be parsed as papers."""
        md = """
## RGBT Tracking
### Datasets
| Dataset | Pub. & Date | WebSite |
|:-----:|:-----:|:-----:|
| [GTOT](https://arxiv.org/abs/1607.02905) | TIP-2016 | [GTOT](https://github.com/lchljlu/GTOT) |

### Papers
#### 2025
- **Method:** Author.<br />
  "Paper Title." Venue (2025).
  [[paper](https://arxiv.org/abs/2501.00001)]
"""
        papers = parse_papers(md)
        assert len(papers) == 1
        # Bold method name takes priority over quoted title
        assert papers[0].title == "Method"

    def test_year_subsection_applied(self):
        """Year from #### 2025 header should apply to papers without explicit year."""
        md = """
## RGBT Tracking
### Papers
#### 2025
- **Method:** Author.<br />
  "A New Tracking Method." Venue (2025).
  [[paper](https://arxiv.org/abs/2501.00001)]
"""
        papers = parse_papers(md)
        assert len(papers) == 1
        assert papers[0].year == 2025
