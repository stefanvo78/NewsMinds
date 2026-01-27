# NewsMinds - AI-Powered Intelligence Platform

## Project Overview

NewsMinds is a production-ready, multi-agent AI system that helps organizations extract insights from diverse information sources using advanced RAG (Retrieval-Augmented Generation), MCP (Model Context Protocol) integration, and intelligent agent collaboration.

### Core Value Proposition

An autonomous "AI research team" that:
- Monitors thousands of sources (news, research papers, social media, financial data)
- Identifies trends and emerging signals in real-time
- Fact-checks claims across multiple sources
- Detects bias and misinformation
- Generates personalized intelligence briefings
- Tracks specific topics, companies, or technologies
- Creates knowledge graphs of interconnected events

### Real-World Use Case

**Executive Intelligence Platform**: Think Bloomberg Terminal meets AI research team - a system that continuously monitors, analyzes, and synthesizes information to provide personalized intelligence briefings for executives, analysts, and researchers.

---

## Technology Stack

### Core Technologies

**Language & Framework:**
- Python 3.11+
- FastAPI (API server with WebSocket support)
- Pydantic v2 (data validation)
- AsyncIO (concurrent operations)

**LLM Integration:**
- Azure OpenAI Service (GPT-4 Turbo, GPT-4o, text-embedding-3-large)
- Anthropic Claude Sonnet 4 (via API for reasoning)
- Azure AI Services (Text Analytics, NER, Sentiment Analysis)

**Agent Framework:**
- LangGraph (agent state machines and orchestration)
- LangChain (tool integration)
- Custom agent protocol layer
- Dapr (service-to-service communication)

**MCP Framework:**
- `mcp` Python SDK
- FastMCP for server development
- Custom MCP client implementation

**Vector Database:**
- Qdrant (deployed on Azure Container Apps)
- Hybrid search (dense + sparse retrieval)
- Multiple collections per source type

**Graph Database:**
- Neo4j (deployed on Azure Container Apps)
- APOC and Graph Data Science plugins
- Knowledge graph for entity relationships

**Relational Database:**
- Azure SQL Database (Hyperscale or Business Critical tier)
- User data, subscriptions, query logs
- Agent performance metrics
- Zone-redundant for high availability

**Cache & Message Queue:**
- Azure Cache for Redis (Enterprise Tier)
- Azure Service Bus (Premium tier)
- Priority queues with dead-letter handling

**Search & Analytics:**
- Azure Cognitive Search (full-text search)
- Azure Data Explorer (Kusto - time-series analytics)

**Storage:**
- Azure Blob Storage (Hot/Cool/Archive tiers)
- Azure Files (persistent storage for containers)

**Additional Libraries:**
- `pyodbc` or `asyncpg` - Azure SQL Database drivers
- `sqlalchemy` - ORM for Azure SQL
- `sentence-transformers` - Embeddings
- `rank-bm25` - Sparse retrieval
- `networkx` - Knowledge graph operations
- `beautifulsoup4` - Web scraping
- `playwright` - Browser automation
- `spaCy` - NLP and NER
- `feedparser` - RSS feeds
- `httpx` - Async HTTP client

---

## High-Level Architecture

### System Layers
┌─────────────────────────────────────────────────────────────┐
│                     USER LAYER                               │
│  Web Dashboard | Mobile App | API Clients | Slack Bot       │
└────────────────────────────┬────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────┐
│              API GATEWAY (Azure API Management)             │
│  Rate Limiting | Auth (Entra ID) | Caching | Analytics     │
└────────────────────────────┬────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────┐
│         APPLICATION LAYER (Azure App Service)               │
│  • FastAPI Application (WebSocket support)                  │
│  • Orchestrator Service (agent coordination)                │
└────────────────────────────┬────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────┐
│         AGENT LAYER (Azure Container Apps)                  │
│                                                              │
│  Collection Agents (scale 0-N):                             │
│    • News Monitor Agent                                     │
│    • Research Paper Agent (ArXiv, PubMed, Scholar)         │
│    • Social Media Agent (Twitter/X, Reddit, LinkedIn)      │
│    • Financial Agent (SEC, earnings calls)                 │
│    • Patent Agent                                           │
│                                                              │
│  Analysis Agents (scale 0-N):                               │
│    • Entity Recognition Agent (NER + disambiguation)        │
│    • Trend Detection Agent (anomaly detection)             │
│    • Fact-Checking Agent (cross-source verification)       │
│    • Sentiment Analysis Agent (multi-dimensional)          │
│    • Bias Detection Agent (political, framing)             │
│                                                              │
│  Synthesis Agents (scale 0-N):                              │
│    • Summarization Agent (multi-document)                  │
│    • Knowledge Graph Agent (entity relationships)          │
│    • Report Generation Agent                                │
│                                                              │
│  • KEDA Autoscaling (event-driven, queue-based)            │
│  • Dapr for inter-agent communication                       │
└────────────────────────────┬────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────┐
│         MCP SERVER LAYER (Azure Container Apps)             │
│                                                              │
│  Data Source MCP Servers:                                   │
│    • mcp-news-api (News API integration)                   │
│    • mcp-arxiv (research papers)                           │
│    • mcp-twitter (social media monitoring)                 │
│    • mcp-sec-edgar (SEC filings)                           │
│    • mcp-youtube (video transcripts)                       │
│    • mcp-podcast (audio transcription)                     │
│                                                              │
│  Tool MCP Servers:                                          │
│    • mcp-nlp-toolkit (advanced NLP)                        │
│    • mcp-fact-check-db (fact-checking database)            │
│    • mcp-sentiment-analyzer                                 │
│    • mcp-graph-db (Neo4j access)                           │
│                                                              │
│  Coordination MCP Servers:                                  │
│    • mcp-agent-coordinator (agent messaging)                │
│    • mcp-vector-db (Qdrant access)                         │
│    • mcp-cognitive-search (Azure Search access)            │
└────────────────────────────┬────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│                                                              │
│  • Qdrant (vector database - Container Apps)                │
│  • Neo4j (graph database - Container Apps)                  │
│  • Azure SQL Database (Hyperscale/Business Critical)        │
│  • Redis (cache & queue - Enterprise tier)                  │
│  • Service Bus (message queue - Premium)                    │
│  • Cognitive Search (full-text search)                      │
│  • Data Explorer (time-series analytics)                    │
│  • Blob Storage (object storage - tiered)                   │
└─────────────────────────────────────────────────────────────┘

---

## Agent Architecture

### Orchestrator Agent (Intelligence Director)

**Responsibilities:**
- Query planning and decomposition
- Agent selection and delegation
- Priority management
- Bias detection coordination
- Result synthesis and aggregation
- Load balancing across agents

**Communication Pattern:**
User Request → API → Service Bus Queue → Orchestrator
↓
[Task Decomposition]
↓
┌─────────────────────────┼─────────────────────┐
↓                         ↓                     ↓
Collection             Analysis              Synthesis
Agents                Agents                Agents
↓                         ↓                     ↓
Service Bus Topics     Service Bus Topics    Service Bus Topics
↓                         ↓                     ↓
[Process & Store]      [Process & Store]     [Process & Store]
└─────────────────────────┼─────────────────────┘
↓
Orchestrator
↓
[Result Synthesis]
↓
Service Bus → API → User
### Collection Agents

#### 1. News Monitor Agent
- Real-time news scraping from multiple sources
- RSS feed monitoring
- Breaking news detection
- Source credibility scoring
- Deduplication across sources

**Scaling:** Min 1, Max 5 (based on queue depth)

#### 2. Research Paper Agent
- ArXiv, PubMed, Google Scholar monitoring
- Academic paper extraction and parsing
- Citation analysis
- Preprint tracking

**Scaling:** Min 0, Max 3 (scale to zero when idle)

#### 3. Social Media Agent
- Twitter/X stream monitoring
- Reddit topic tracking
- LinkedIn professional updates
- Influencer and expert identification
- Viral content detection

**Scaling:** Min 1, Max 10 (high burst capacity)

#### 4. Financial Agent
- SEC filing monitoring (EDGAR)
- Earnings call transcription
- Financial news aggregation
- Market data tracking

**Scaling:** Min 0, Max 3

#### 5. Patent Agent
- USPTO and EPO patent monitoring
- Patent filing analysis
- Technology trend identification

**Scaling:** Min 0, Max 2

### Analysis Agents

#### 1. Entity Recognition Agent
- Named Entity Extraction (persons, companies, locations, products)
- Entity disambiguation and linking
- Entity relationship mapping
- Deduplication across sources

**Technologies:** spaCy, Azure Text Analytics

#### 2. Trend Detection Agent
- Statistical anomaly detection
- Topic clustering and modeling
- Emerging theme identification
- Temporal pattern analysis
- Signal vs. noise filtering

**Technologies:** scikit-learn, Azure Data Explorer

#### 3. Fact-Checking Agent
- Cross-source claim verification
- Claim extraction from text
- Confidence scoring
- Source credibility assessment
- Contradiction detection

**Process:**
1. Extract claims from articles
2. Search for supporting/contradicting evidence
3. Cross-reference across trusted sources
4. Compute confidence scores
5. Flag contradictions

#### 4. Sentiment Analysis Agent
- Multi-dimensional sentiment (positive, negative, neutral)
- Emotional tone analysis (anger, fear, joy, etc.)
- Narrative arc tracking
- Opinion vs. fact distinction
- Sentiment time-series for trends

**Technologies:** Azure Text Analytics, custom transformers

#### 5. Bias Detection Agent
- Political bias identification
- Source bias profiling
- Framing analysis (how stories are told)
- Omission detection (what's not said)
- Balanced perspective generation

### Synthesis Agents

#### 1. Summarization Agent
- Multi-document summarization
- Key point extraction
- Timeline generation
- Executive summary creation
- Hierarchical summarization (detail levels)

**Techniques:**
- Extractive summarization
- Abstractive summarization (LLM-based)
- Hybrid approaches

#### 2. Knowledge Graph Agent
- Entity relationship building
- Event causality mapping
- Temporal graph updates
- Graph-based querying and reasoning
- Relationship strength scoring

#### 3. Report Generation Agent
- Structured report creation
- Visualization generation (charts, graphs)
- Citation formatting
- Multi-format export (PDF, Markdown, HTML)
- Executive briefing templates

---

## Agent Communication Protocol

### Message Format
```json
{
"from_agent": "research_agent",
"to_agent": "fact_checker_agent",
"message_type": "task_request",
"task_id": "550e8400-e29b-41d4-a716-446655440000",
"parent_task_id": "parent-uuid",
"timestamp": "2025-01-23T10:30:00Z",
"priority": "high",
"payload": {
"action": "verify_claim",
"claim": "Company X released product Y in Q3 2024",
"sources": [
"https://example.com/article1",
"https://example.com/article2"
],
"context": "competitor_analysis",
"required_confidence": 0.85
},
"metadata": {
"user_id": "user-123",
"session_id": "session-456"
}
}```

### Communication Patterns

**1. Request-Response:**
- Direct agent queries with synchronous responses
- Used for quick operations (e.g., NER, sentiment)

**2. Publish-Subscribe:**
- Broadcast updates to interested agents
- Used for event notifications (breaking news, trend alerts)

**3. Task Queue:**
- Asynchronous work distribution
- Priority queues for urgent vs. normal tasks
- Dead-letter queues for failed tasks

**4. Consensus:**
- Multi-agent agreement on uncertain facts
- Voting mechanism with confidence weights
- Used for fact-checking and bias detection

### Azure Service Bus Configuration

**Queues:**
- `orchestrator-queue` - Incoming user requests
- `{agent-name}-queue` - Per-agent task queues
- `results-queue` - Completed task results
- `dlq-*` - Dead-letter queues for failed messages

**Topics & Subscriptions:**
- `news-events` topic
  - `trend-detection-sub`
  - `fact-checking-sub`
  - `knowledge-graph-sub`
- `analysis-complete` topic
  - `report-generation-sub`
  - `user-notification-sub`

**Message Properties:**
- `priority`: high, normal, low
- `task_type`: collect, analyze, verify, synthesize
- `retry_count`: number of retry attempts
- `deadline`: task completion deadline

---



## Project Structure
```
newsminds/
│
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── dependencies.py            # Dependency injection
│   ├── config.py                  # Configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── query.py
│   │   ├── alert.py
│   │   └── report.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── query.py
│   │   ├── sources.py
│   │   ├── alerts.py
│   │   └── reports.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database.py           # Azure SQL operations
│   │   ├── vector_store.py       # Qdrant operations
│   │   ├── graph_db.py           # Neo4j operations
│   │   └── cache.py              # Redis operations
│   └── websocket.py              # WebSocket handlers
│
├── orchestrator/
│   ├── __init__.py
│   ├── main.py                   # Orchestrator service
│   ├── task_decomposer.py
│   ├── agent_selector.py
│   ├── result_aggregator.py
│   └── message_handlers.py
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py             # Base agent class
│   ├── collection/
│   │   ├── __init__.py
│   │   ├── news_monitor.py
│   │   ├── research_paper.py
│   │   ├── social_media.py
│   │   ├── financial.py
│   │   └── patent.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── entity_recognition.py
│   │   ├── trend_detection.py
│   │   ├── fact_checker.py
│   │   ├── sentiment.py
│   │   └── bias_detection.py
│   └── synthesis/
│       ├── __init__.py
│       ├── summarization.py
│       ├── knowledge_graph.py
│       └── report_generator.py
│
├── mcp_servers/
│   ├── news_api/
│   │   ├── server.py
│   │   └── Dockerfile
│   ├── arxiv/
│   │   ├── server.py
│   │   └── Dockerfile
│   ├── twitter/
│   │   ├── server.py
│   │   └── Dockerfile
│   ├── agent_coordinator/
│   │   ├── server.py
│   │   └── Dockerfile
│   └── vector_db/
│       ├── server.py
│       └── Dockerfile
│
├── rag/
│   ├── __init__.py
│   ├── embeddings.py             # Embedding generation
│   ├── vector_store.py           # Qdrant interface
│   ├── retriever.py              # Hybrid retrieval
│   ├── chunking.py               # Document chunking
│   ├── reranker.py               # Result reranking
│   └── query_transform.py        # Query enhancement
│
├── knowledge_graph/
│   ├── __init__.py
│   ├── entity_extractor.py       # NER and extraction
│   ├── graph_builder.py          # Graph construction
│   ├── graph_querier.py          # Graph queries
│   └── schemas.py                # Graph schemas
│
├── communication/
│   ├── __init__.py
│   ├── message_bus.py            # Service Bus wrapper
│   ├── dapr_client.py            # Dapr integration
│   └── protocols.py              # Message formats
│
├── infrastructure/
│   ├── main.bicep                # Main infrastructure
│   ├── sql-schema.sql            # Database schema
│   ├── app-service.bicep
│   ├── container-apps.bicep
│   ├── databases.bicep
│   └── monitoring.bicep
│
├── ui/
│   ├── streamlit_app.py          # Demo interface
│   └── components/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.orchestrator
│   ├── Dockerfile.agent
│   └── docker-compose.yml
│
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   ├── deployment.md
│   └── development.md
│
├── scripts/
│   ├── setup_database.py
│   ├── deploy_infrastructure.sh
│   └── run_migrations.py
│
├── requirements.txt
├── pyproject.toml
├── README.md
└── .env.example
```


## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- Set up Azure infrastructure with Bicep
- Create Azure SQL database with schema
- Implement FastAPI skeleton
- Set up authentication with Entra ID
- Configure Application Insights

### Phase 2: Core RAG (Weeks 3-4)
- Deploy Qdrant on Container Apps
- Implement embedding pipeline with Azure OpenAI
- Build hybrid search functionality
- Create query interface
- Test with sample data

### Phase 3: Agent Framework (Weeks 5-7)
- Build orchestrator service
- Implement first collection agent (news monitor)
- Set up Service Bus communication
- Deploy agents to Container Apps
- Test agent coordination

### Phase 4: MCP Integration (Weeks 8-9)
- Build first MCP server (News API)
- Integrate MCP client in agents
- Add more MCP servers (ArXiv, Twitter)
- Test end-to-end MCP flow

### Phase 5: Advanced Features (Weeks 10-12)
- Implement Neo4j knowledge graph
- Add fact-checking agent
- Build tren