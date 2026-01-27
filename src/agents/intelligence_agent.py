"""
Intelligence Agent - The complete news research agent.

This agent combines:
- RAG for searching your indexed articles
- MCP for accessing external news sources
- LLM reasoning for deciding what to do
"""

from openai import OpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

from src.api.core.config import settings
from src.rag.retriever import rag_retriever


# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def chat(messages: list[dict], max_tokens: int = 1000) -> str:
    """Helper to call ChatGPT."""
    response = openai_client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content

class IntelligenceState(TypedDict):
    """State for the Intelligence Agent."""
    messages: Annotated[list, add_messages]
    query: str

    # From RAG
    internal_docs: list[dict]

    # From MCP (external sources)
    external_articles: list[dict]

    # Analysis
    key_facts: list[str]
    contradictions: list[str]

    # Output
    briefing: str | None

    # Control
    search_strategy: str  # "internal", "external", "both"
    iteration: int


def plan_search(state: IntelligenceState) -> dict:
    """
    Node: Use LLM to plan the search strategy.

    The LLM decides whether to search internal docs, external sources, or both.
    """
    query = state["query"]

    response = chat(
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"""For the query: "{query}"

Should I search:
1. INTERNAL - Our indexed articles only
2. EXTERNAL - External news APIs only
3. BOTH - Both internal and external sources

Consider: Is this about recent events (external), our historical data (internal), or needs comprehensive coverage (both)?

Reply with only: INTERNAL, EXTERNAL, or BOTH"""
            }
        ],
    )

    strategy = response.strip().upper()
    if strategy not in ["INTERNAL", "EXTERNAL", "BOTH"]:
        strategy = "BOTH"

    return {
        "search_strategy": strategy,
        "messages": [{"role": "assistant", "content": f"Search strategy: {strategy}"}],
    }


def search_internal(state: IntelligenceState) -> dict:
    """Node: Search internal RAG database."""
    if state["search_strategy"] == "EXTERNAL":
        return {"internal_docs": []}

    query = state["query"]
    docs = rag_retriever.retrieve(query, limit=10)

    return {
        "internal_docs": docs,
        "messages": [{"role": "assistant", "content": f"Found {len(docs)} internal documents"}],
    }


async def search_external(state: IntelligenceState) -> dict:
    """Node: Search external sources via MCP."""
    if state["search_strategy"] == "INTERNAL":
        return {"external_articles": []}

    # In production, call MCP server here
    # For now, return empty (would integrate with news API)
    return {
        "external_articles": [],
        "messages": [{"role": "assistant", "content": "Searched external sources"}],
    }


def analyze_sources(state: IntelligenceState) -> dict:
    """
    Node: Analyze all sources, extract facts, find contradictions.

    This is deep LLM reasoning over the retrieved content.
    """
    internal = state.get("internal_docs", [])
    external = state.get("external_articles", [])
    query = state["query"]

    # Combine all sources
    all_content = []
    for doc in internal:
        all_content.append(f"[Internal] {doc.get('text', '')}")
    for article in external:
        all_content.append(f"[External] {article.get('summary', '')}")

    if not all_content:
        return {
            "key_facts": [],
            "contradictions": [],
        }

    combined = "\n\n".join(all_content)

    response = chat(
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": f"""Analyze these sources regarding: "{query}"

Sources:
{combined}

Provide:
1. KEY_FACTS: List the most important facts (bullet points)
2. CONTRADICTIONS: Any conflicting information between sources

Format:
KEY_FACTS:
- fact 1
- fact 2

CONTRADICTIONS:
- contradiction 1 (or "None found" if none)"""
            }
        ],
    )

    text = response

    # Parse response
    facts = []
    contradictions = []
    current_section = None

    for line in text.split("\n"):
        line = line.strip()
        if "KEY_FACTS:" in line:
            current_section = "facts"
        elif "CONTRADICTIONS:" in line:
            current_section = "contradictions"
        elif line.startswith("- ") and current_section:
            content = line[2:].strip()
            if current_section == "facts":
                facts.append(content)
            else:
                if "none" not in content.lower():
                    contradictions.append(content)

    return {
        "key_facts": facts,
        "contradictions": contradictions,
        "messages": [{"role": "assistant", "content": f"Analyzed: {len(facts)} facts, {len(contradictions)} contradictions"}],
    }


def generate_briefing(state: IntelligenceState) -> dict:
    """
    Node: Generate the final intelligence briefing.
    """
    facts = state.get("key_facts", [])
    contradictions = state.get("contradictions", [])
    query = state["query"]

    facts_text = "\n".join(f"- {f}" for f in facts) if facts else "No facts extracted"
    contradictions_text = "\n".join(f"- {c}" for c in contradictions) if contradictions else "None"

    response = chat(
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": f"""Create an executive intelligence briefing for: "{query}"

Key Facts:
{facts_text}

Contradictions/Uncertainties:
{contradictions_text}

Format the briefing with:
1. SUMMARY (2-3 sentences)
2. KEY FINDINGS (bullet points)
3. UNCERTAINTIES (if any)
4. RECOMMENDED ACTIONS (if applicable)

Keep it concise and actionable."""
            }
        ],
    )

    briefing = response

    return {
        "briefing": briefing,
        "messages": [{"role": "assistant", "content": briefing}],
    }


def build_intelligence_agent() -> StateGraph:
    """Build the complete Intelligence Agent graph."""
    graph = StateGraph(IntelligenceState)

    # Add nodes
    graph.add_node("plan_search", plan_search)
    graph.add_node("search_internal", search_internal)
    graph.add_node("search_external", search_external)
    graph.add_node("analyze_sources", analyze_sources)
    graph.add_node("generate_briefing", generate_briefing)

    # Define flow
    graph.set_entry_point("plan_search")

    # After planning, do both searches in parallel conceptually
    # (LangGraph will handle this)
    graph.add_edge("plan_search", "search_internal")
    graph.add_edge("search_internal", "search_external")
    graph.add_edge("search_external", "analyze_sources")
    graph.add_edge("analyze_sources", "generate_briefing")
    graph.add_edge("generate_briefing", END)

    return graph.compile()


# Create the agent
intelligence_agent = build_intelligence_agent()


async def get_intelligence_briefing(query: str) -> str:
    """
    Get an intelligence briefing on any topic.

    Args:
        query: What to research

    Returns:
        Executive briefing
    """
    initial_state = {
        "messages": [],
        "query": query,
        "internal_docs": [],
        "external_articles": [],
        "key_facts": [],
        "contradictions": [],
        "briefing": None,
        "search_strategy": "both",
        "iteration": 0,
    }

    final_state = await intelligence_agent.ainvoke(initial_state)
    return final_state["briefing"]