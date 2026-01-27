"""
Agent State - The shared data structure for LangGraph agents.

State flows through the graph, accumulating information as the agent works.
"""

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentMessage(TypedDict):
    """A message in the conversation."""
    role: str  # "user", "assistant", or "tool"
    content: str


class ResearchAgentState(TypedDict):
    """
    State for the Research Agent.

    This state is passed between nodes and accumulates information.
    """
    # The conversation history (uses add_messages reducer to append)
    messages: Annotated[list, add_messages]

    # The user's original query
    query: str

    # Retrieved documents from RAG
    retrieved_docs: list[dict]

    # Facts extracted from documents
    facts: list[str]

    # The final answer
    answer: str | None

    # Whether we need more research
    needs_more_research: bool

    # Number of research iterations
    iteration_count: int