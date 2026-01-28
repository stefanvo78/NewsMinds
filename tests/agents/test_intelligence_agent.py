"""Tests for the Intelligence Agent."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses."""
    with patch("src.agents.intelligence_agent._get_openai_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_rag():
    """Mock RAG retriever."""
    with patch("src.agents.intelligence_agent.rag_retriever") as mock:
        yield mock


def test_plan_search_returns_valid_strategy(mock_openai):
    """Test that plan_search returns a valid strategy."""
    from src.agents.intelligence_agent import plan_search

    # Mock OpenAI to return "BOTH"
    mock_openai.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="BOTH"))]
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

    mock_rag.retrieve.return_value = [{"text": "Test document", "score": 0.9}]

    # When strategy is INTERNAL, should search
    state = {"query": "test", "search_strategy": "INTERNAL"}
    result = search_internal(state)
    assert len(result["internal_docs"]) > 0

    # When strategy is EXTERNAL, should skip
    state = {"query": "test", "search_strategy": "EXTERNAL"}
    result = search_internal(state)
    assert len(result["internal_docs"]) == 0


@pytest.mark.asyncio
async def test_full_agent_flow(mock_openai, mock_rag):
    """Test the complete agent flow."""
    from src.agents.intelligence_agent import get_intelligence_briefing

    # Mock all OpenAI calls
    mock_openai.chat.completions.create.side_effect = [
        MagicMock(
            choices=[MagicMock(message=MagicMock(content="BOTH"))]
        ),  # plan_search
        MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="KEY_FACTS:\n- Fact 1\n- Fact 2\n\nCONTRADICTIONS:\nNone"
                    )
                )
            ]
        ),  # analyze
        MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="## Briefing\n\nThis is the briefing.")
                )
            ]
        ),  # generate
    ]

    mock_rag.retrieve.return_value = [{"text": "Test content", "score": 0.9}]

    briefing = await get_intelligence_briefing("Test query")

    assert briefing is not None
    assert "Briefing" in briefing
