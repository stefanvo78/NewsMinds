"""
Research Agent - A true AI agent that researches and answers questions.

This agent uses LangGraph to orchestrate:
1. Retrieving relevant documents (RAG)
2. Extracting facts from documents
3. Deciding if more research is needed
4. Generating a final answer
"""

from openai import OpenAI
from langgraph.graph import StateGraph, END

from src.api.core.config import settings
from src.agents.state import ResearchAgentState
from src.rag.retriever import rag_retriever

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Lazy-load OpenAI client to allow app startup without API key
_openai_client = None

def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def chat(messages: list[dict], max_tokens: int = 1000) -> str:
    """Helper to call ChatGPT."""
    response = _get_openai_client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content


async def call_mcp_tool(server_name: str, tool_name: str, arguments: dict) -> str:
    """
    Call a tool on an MCP server.

    This is how your agent uses MCP tools!
    """
    # Define server configuration
    server_params = StdioServerParameters(
        command="python",
        args=[f"src/mcp_servers/{server_name}/server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Call the tool
            result = await session.call_tool(tool_name, arguments)

            # Return the text content
            return result.content[0].text if result.content else ""


# Example: Using MCP in a node
async def search_external_news(state: ResearchAgentState) -> dict:
    """Node that uses the MCP news search tool."""
    query = state["query"]

    # Call the MCP tool
    result = await call_mcp_tool(
        server_name="news_search",
        tool_name="search_news",
        arguments={"query": query, "max_results": 5},
    )

    # Parse and add to state
    import json
    news_data = json.loads(result)

    return {
        "external_sources": news_data.get("articles", []),
        "messages": [
            {
                "role": "assistant",
                "content": f"Found {len(news_data.get('articles', []))} external news articles.",
            }
        ],
    }

def retrieve_documents(state: ResearchAgentState) -> dict:
    """
    Node: Retrieve relevant documents from the vector store.

    This is the RAG retrieval step.
    """
    query = state["query"]

    # Get relevant chunks from RAG
    docs = rag_retriever.retrieve(query, limit=5)

    return {
        "retrieved_docs": docs,
        "messages": [
            {
                "role": "assistant",
                "content": f"Retrieved {len(docs)} relevant documents.",
            }
        ],
    }


def extract_facts(state: ResearchAgentState) -> dict:
    """
    Node: Use Claude to extract facts from retrieved documents.

    This is where the LLM does reasoning work.
    """
    docs = state["retrieved_docs"]
    query = state["query"]

    # Build context from documents
    context = "\n\n".join([
        f"Document {i+1}:\n{doc['text']}"
        for i, doc in enumerate(docs)
    ])

    # Ask Claude to extract relevant facts
    response = chat(
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"""Given the following documents, extract the key facts relevant to answering this question: "{query}"

Documents:
{context}

List the relevant facts as bullet points. Only include facts that are directly stated in the documents."""
            }
        ],
    )

    facts_text = response
    facts = [line.strip("- ").strip() for line in facts_text.split("\n") if line.strip().startswith("-")]

    return {
        "facts": facts,
        "messages": [
            {
                "role": "assistant",
                "content": f"Extracted {len(facts)} relevant facts.",
            }
        ],
    }


def decide_next_step(state: ResearchAgentState) -> str:
    """
    Conditional Edge: Decide whether we need more research or can answer.

    This is the "reasoning" part - the LLM decides the control flow!
    """
    facts = state["facts"]
    query = state["query"]
    iteration = state.get("iteration_count", 0)

    # Limit iterations to prevent infinite loops
    if iteration >= 3:
        return "generate_answer"

    # Ask Claude if we have enough information
    response = chat(
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"""Question: "{query}"

Facts gathered so far:
{chr(10).join(f'- {fact}' for fact in facts)}

Do we have enough information to fully answer this question?
Reply with ONLY "YES" or "NO"."""
            }
        ],
    )

    decision = response.strip().upper()

    if "NO" in decision and iteration < 2:
        return "retrieve_documents"  # Need more research
    else:
        return "generate_answer"  # Ready to answer


def generate_answer(state: ResearchAgentState) -> dict:
    """
    Node: Generate the final answer using gathered facts.
    """
    facts = state["facts"]
    query = state["query"]

    response = chat(
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"""Based on the following facts, provide a comprehensive answer to the question.

Question: "{query}"

Facts:
{chr(10).join(f'- {fact}' for fact in facts)}

Provide a clear, well-structured answer. If the facts don't fully answer the question, acknowledge what's missing."""
            }
        ],
    )

    answer = response

    return {
        "answer": answer,
        "messages": [
            {
                "role": "assistant",
                "content": answer,
            }
        ],
    }


def increment_iteration(state: ResearchAgentState) -> dict:
    """Node: Increment the iteration counter."""
    return {
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


def build_research_agent() -> StateGraph:
    """
    Build the Research Agent graph.

    Graph structure:

    START → retrieve_documents → extract_facts → decide_next_step
                    ↑                                    │
                    │                                    ↓
                    └──── (needs more) ←── increment ←──┤
                                                        │
                                                        ↓ (ready)
                                               generate_answer → END
    """
    # Create the graph with our state type
    graph = StateGraph(ResearchAgentState)

    # Add nodes
    graph.add_node("retrieve_documents", retrieve_documents)
    graph.add_node("extract_facts", extract_facts)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("increment_iteration", increment_iteration)

    # Set entry point
    graph.set_entry_point("retrieve_documents")

    # Add edges
    graph.add_edge("retrieve_documents", "extract_facts")

    # Conditional edge - LLM decides what's next!
    graph.add_conditional_edges(
        "extract_facts",
        decide_next_step,
        {
            "retrieve_documents": "increment_iteration",
            "generate_answer": "generate_answer",
        },
    )

    graph.add_edge("increment_iteration", "retrieve_documents")
    graph.add_edge("generate_answer", END)

    return graph.compile()


# Create the agent
research_agent = build_research_agent()


async def research(query: str) -> str:
    """
    Run a research query through the agent.

    Args:
        query: The user's question

    Returns:
        The agent's answer
    """
    # Initialize state
    initial_state = {
        "messages": [],
        "query": query,
        "retrieved_docs": [],
        "facts": [],
        "answer": None,
        "needs_more_research": True,
        "iteration_count": 0,
    }

    # Run the agent
    final_state = research_agent.invoke(initial_state)

    return final_state["answer"]