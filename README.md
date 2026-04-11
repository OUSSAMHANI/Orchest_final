# Multi-Agent Orchestrator

A sophisticated multi-agent orchestration system that automates the software development lifecycle through intelligent agent coordination. Built with LangGraph, FastAPI, and modern AI technologies.

## Overview

The Multi-Agent Orchestrator coordinates four specialized AI agents to transform GitLab issues into automated code changes:

1. **Spec Agent** - Analyzes tickets and generates technical specifications
2. **Coder Agent** - Implements code changes based on specifications
3. **Tester Agent** - Writes and executes tests to validate changes
4. **Reviewer Agent** - Reviews code and ensures quality standards

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator (LangGraph)                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ Planner │→ │ Execute │→ │  Route  │→ │ Handler │           │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Spec Agent    │  │   Coder Agent   │  │  Tester Agent   │
│  (Port 8001)    │  │   (Port 8002)   │  │   (Port 8003)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Key Features

- **Graph-Based Workflow**: Uses LangGraph for stateful, retryable execution pipelines
- **Multi-Phase Spec Agent**: Implements a sophisticated 4-phase spec generation:
  - Phase 0: Workspace analysis
  - Phase 1: BM25 semantic search
  - Phase 2: Tree-sitter AST parsing
  - Phase 3: RAG-based retrieval
  - Phase 4: LLM-powered generation
- **Kafka Integration**: Consumes tickets from Kafka topics for event-driven processing
- **GitLab Integration**: Creates merge requests with automated reviewer assignment
- **Flexible LLM Support**: Works with OpenAI, Anthropic, Groq, or local LLMs
- **Retry & Recovery**: Automatic retry mechanisms with configurable backoff
- **Workspace Isolation**: Per-ticket isolated workspaces with automatic cleanup

## Technology Stack

- **Orchestration**: LangGraph, LangChain
- **API Framework**: FastAPI
- **Message Queue**: Kafka
- **LLM Integration**: OpenAI, Anthropic, Groq
- **Code Analysis**: Tree-sitter
- **Search**: BM25, RAG embeddings
- **Configuration**: Pydantic Settings

## Quick Start

### Prerequisites

- Python 3.10+
- Kafka (for message processing)
- LLM API keys (OpenAI/Anthropic/Groq)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Running the Orchestrator

```bash
# Start the orchestrator API
python -m orchestrator.main

# Or use the start script
./start.bat
```

The API will be available at `http://localhost:8000`

### Running Individual Agents

```bash
# Start Spec Agent
python -m agents.spec_agent.main

# Start Coder Agent
python -m agents.coder_agent.main
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ticket` | POST | Submit a ticket for async processing |
| `/ticket/sync` | POST | Submit a ticket, wait for result |
| `/status/{ticket_id}` | GET | Get ticket processing status |
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |

## Configuration

Configuration is managed via environment variables or `.env` file:

```env
# LLM Settings
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...

# Kafka Settings
KAFKA_BROKERS=localhost:9092
KAFKA_TOPIC_TICKETS=gitlab-tickets

# GitLab Settings
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=glpat-...

# Agent URLs
SPEC_AGENT_URL=http://localhost:8001
CODER_AGENT_URL=http://localhost:8002
TESTER_AGENT_URL=http://localhost:8003
REVIEWER_AGENT_URL=http://localhost:8004
```

## Project Structure

```
Root/
├── orchestrator/           # Main orchestration engine
│   ├── graph/             # LangGraph nodes and edges
│   ├── execution/        # Step execution and retry logic
│   ├── planning/          # Plan generation and validation
│   ├── routing/          # Conditional routing
│   ├── state/            # State management
│   └── consumers/         # Kafka consumers
├── agents/                # Specialized agents
│   ├── spec_agent/       # Specification generator
│   ├── coder_agent/      # Code implementation
│   ├── tester_agent/     # Test generation
│   └── reviewer_agent/   # Code review
├── shared/                # Shared utilities
│   ├── config/           # Configuration management
│   ├── llm/              # LLM client wrappers
│   └── schemas/          # Data schemas
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
└── scripts/               # Utility scripts
```

## Development

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=orchestrator tests/

# Lint
ruff check .
```

## License

MIT