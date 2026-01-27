"""Tests for the Intelligence Agent."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_claude():
    """Mock Claude API responses."""
    with patch("src.agents.intelligence_agent.claude") as mock:
        yield mock


@pytest.fixture
def mock_rag():
    """Mock RAG retriever."""
    with patch("src.agents.intelligence_agent.rag_retriever") as mock:
        yield mock


def test_plan_search_returns_valid_strategy(mock_claude):
    """Test that plan_search returns a valid strategy."""
    from src.agents.intelligence_agent import plan_search

    # Mock Claude to return "BOTH"
    mock_claude.messages.create.return_value = MagicMock(
        content=[MagicMock(text="BOTH")]
    )

    state = {
        "query": "What's happening with AI?",
        "messages": [],
    }

    result = plan_search(state)

    assert result["search_strategy"] in ["INTERNAL", "EXTERNAL", "BOTH"]


def test_search_internal_respects_strategy(mock_rag):
    """Test that internal search respects the strategy."""
    from src.agents.intelligence_agent import search_internal

    mock_rag.retrieve.return_value = [
        {"text": "Test document", "score": 0.9}
    ]

    # When strategy is INTERNAL, should search
    state = {"query": "test", "search_strategy": "INTERNAL"}
    result = search_internal(state)
    assert len(result["internal_docs"]) > 0

    # When strategy is EXTERNAL, should skip
    state = {"query": "test", "search_strategy": "EXTERNAL"}
    result = search_internal(state)
    assert len(result["internal_docs"]) == 0


@pytest.mark.asyncio
async def test_full_agent_flow(mock_claude, mock_rag):
    """Test the complete agent flow."""
    from src.agents.intelligence_agent import get_intelligence_briefing

    # Mock all Claude calls
    mock_claude.messages.create.side_effect = [
        MagicMock(content=[MagicMock(text="BOTH")]),  # plan_search
        MagicMock(content=[MagicMock(text="KEY_FACTS:\n- Fact 1\n- Fact 2\n\nCONTRADICTIONS:\nNone")]),  # analyze
        MagicMock(content=[MagicMock(text="## Briefing\n\nThis is the briefing.")]),  # generate
    ]

    mock_rag.retrieve.return_value = [
        {"text": "Test content", "score": 0.9}
    ]

    briefing = await get_intelligence_briefing("Test query")

    assert briefing is not None
    assert "Briefing" in briefing