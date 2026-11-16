"""Unit tests for SQLite MemoryStore, user facts, and entity recall."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from remi.core.memory import MemoryStore


@pytest.fixture
def temp_memory():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        mem = MemoryStore(db_path=db_path)
        yield mem


def test_memory_add_and_get_history(temp_memory):
    temp_memory.add_message(role="user", content="open youtube", session_id="test")
    temp_memory.add_message(role="assistant", content="opening youtube", session_id="test")

    history = temp_memory.get_recent_history(limit=5, session_id="test")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "open youtube"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "opening youtube"


def test_memory_facts_crud(temp_memory):
    temp_memory.set_fact("preferred_browser", "edge", category="preferences")
    assert temp_memory.get_fact("preferred_browser") == "edge"

    temp_memory.set_fact("preferred_browser", "chrome", category="preferences")
    assert temp_memory.get_fact("preferred_browser") == "chrome"

    all_facts = temp_memory.get_all_facts()
    assert "preferred_browser" in all_facts
    assert all_facts["preferred_browser"] == "chrome"


def test_memory_entity_recall(temp_memory):
    assert temp_memory.recall_entity("last_url") is None

    temp_memory.remember_entity("last_url", "https://github.com", detail="github")
    recalled = temp_memory.recall_entity("last_url")
    assert recalled is not None
    assert recalled["value"] == "https://github.com"
    assert recalled["detail"] == "github"
