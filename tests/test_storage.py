"""Tests for storage / sent history logic."""

import json
import os
import tempfile

import pytest

from src.storage import filter_unsent, load_history, mark_sent, save_history


class TestLoadHistory:
    def test_loads_empty_when_no_file(self):
        result = load_history("/tmp/nonexistent_history_file.json")
        assert result == {}

    def test_loads_from_file(self, tmp_path):
        path = str(tmp_path / "history.json")
        data = {"abc123": {"title": "Test", "sent_at": "2025-01-01"}}
        with open(path, "w") as f:
            json.dump(data, f)
        result = load_history(path)
        assert "abc123" in result
        assert result["abc123"]["title"] == "Test"

    def test_handles_corrupt_json(self, tmp_path):
        path = str(tmp_path / "corrupt.json")
        with open(path, "w") as f:
            f.write("not valid json {{{")
        result = load_history(path)
        assert result == {}


class TestSaveHistory:
    def test_saves_and_reloads(self, tmp_path):
        path = str(tmp_path / "history.json")
        data = {"id1": {"title": "Paper 1", "sent_at": "2025-06-01T00:00:00"}}
        save_history(data, path)

        with open(path, "r") as f:
            loaded = json.load(f)
        assert loaded["id1"]["title"] == "Paper 1"

    def test_creates_parent_dir(self, tmp_path):
        path = str(tmp_path / "subdir" / "history.json")
        save_history({"test": {"title": "T"}}, path)
        assert os.path.exists(path)


class TestMarkSent:
    def test_adds_entry(self):
        history = {}
        mark_sent(history, "paper123", "Title", "https://example.com")
        assert "paper123" in history
        assert history["paper123"]["title"] == "Title"
        assert "sent_at" in history["paper123"]


class TestFilterUnsent:
    def _make_paper(self, paper_id, title="Test"):
        class FakePaper:
            def __init__(self, pid, t):
                self.paper_id = pid
                self.title = t

        return FakePaper(paper_id, title)

    def test_filters_correctly(self):
        papers = [
            self._make_paper("a", "Paper A"),
            self._make_paper("b", "Paper B"),
            self._make_paper("c", "Paper C"),
        ]
        history = {"b": {"title": "Paper B"}}
        result = filter_unsent(papers, history)
        assert len(result) == 2
        assert result[0].paper_id == "a"
        assert result[1].paper_id == "c"

    def test_all_sent(self):
        papers = [self._make_paper("a")]
        history = {"a": {"title": "Paper A"}}
        result = filter_unsent(papers, history)
        assert len(result) == 0

    def test_none_sent(self):
        papers = [self._make_paper("a"), self._make_paper("b")]
        history = {}
        result = filter_unsent(papers, history)
        assert len(result) == 2
