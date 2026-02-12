# Enterprise Agentic Workflow Engine (Finance Demo)

## Disclaimer

This project is a demonstration for educational and portfolio purposes.

- All data is synthetic (generated via Faker).
- All examples are fictional.
- Policy documents are mock representations.
- This system is not intended for production use with real customer data.

## Project Overview

This project implements an agentic workflow orchestration backend using Python. It demonstrates architectural patterns for building scalable, auditable, and reliable systems.

### Core Technologies

- **FastAPI**: Async REST API with Pydantic validation
- **LangGraph**: State machine orchestration with conditional routing
- **PostgreSQL + pgvector**: Vector similarity search for RAG
- **SQLAlchemy 2.0**: Async ORM
- **Alembic**: Database migrations
- **Docker**: Containerized deployment

### Key Features

- **Agentic Workflows**: Multi-step state machine with conditional branching
- **Retrieval-Augmented Generation (RAG)**: Policy document retrieval using vector similarity
- **Guardrails**: Tool allowlisting, schema validation, content filtering, and rate limiting
- **Audit Logging**: Immutable audit trail for workflow steps
- **Strict Validation**: Pydantic models for all inputs and outputs
- **Dual Mode**: Supports both mock execution (no API key required) and real LLM integration (OpenAI)
- **Testing**: Async Pytest suite with fixtures

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Client (REST API)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI API Layer                        │
│  • POST /tasks/run                                          │
│  • GET /tasks/{id}                                          │
│  • GET /tasks/{id}/audit                                    │
│  • GET /health                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Guardrails Enforcement Layer                   │
│  • Tool allowlist validation                                │
│  • Pydantic schema validation                               │
│  • Content filtering                                        │
│  • Rate limiting                                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                LangGraph State Machine                      │
│                                                             │
│  START → Ingest → Detect → Retrieve → Draft → Evaluate     │
│                                           │                 │
│                                 ┌─────────┴─────────┐       │
│                                 ▼                   ▼       │
│                            Escalate             Finalize    │
│                                 │                   │       │
│                                 └─────────┬─────────┘       │
│                                           ▼                 │
│                                         END                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Tools      │  │   RAG        │  │   Audit      │
│   Registry   │  │   System     │  │   Logger     │
│              │  │              │  │              │
│ • Analyzer   │  │ • Embeddings │  │ • Events     │
│ • Detector   │  │ • Retriever  │  │ • Duration   │
│ • Drafter    │  │ • Indexer    │  │ • Tool calls │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
              ┌──────────────────────┐
              │   PostgreSQL         │
              │   + pgvector         │
              │                      │
              │ • Customers          │
              │ • Transactions       │
              │ • Policy Docs        │
              │ • Workflow Runs      │
              │ • Audit Events       │
              └──────────────────────┘
```

### Workflow Steps

1.  **Ingest Transactions**: Analyze customer transaction history.
2.  **Detect Anomalies**: Identify suspicious patterns.
3.  **Retrieve Policies**: Search for relevant policy documents.
4.  **Draft Explanation**: Generate analysis.
5.  **Evaluate Confidence**: Route based on confidence score.
6.  **Escalate**: Flag for review if confidence is low.
7.  **Finalize**: Assemble result.

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Option 1: Run with Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd EnterpriseAIWorkflow

# Start the services
docker-compose up --build

# The application will be available at http://localhost:8000
# Database seeding and indexing takes approximately 30 seconds.
```

### Option 2: Local Development

```bash
# Install dependencies
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env to configure database URL

# Start PostgreSQL with pgvector
docker-compose up db

# Run migrations
alembic upgrade head

# Start the application
python -m app.main
```

### Verification

```bash
# Health check
curl http://localhost:8000/api/v1/health

# API documentation
# Open http://localhost:8000/docs in your browser
```

---

## Usage

### 1. Run a Workflow

```bash
curl -X POST http://localhost:8000/api/v1/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "YOUR_CUSTOMER_UUID_HERE",
    "analysis_window_days": 30,
    "anomaly_threshold": 0.8
  }'
```

### 2. Check Status

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}
```

### 3. Retrieve Audit Log

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}/audit
```

---

## Project Structure

```
EnterpriseAIWorkflow/
├── app/
│   ├── main.py                    # FastAPI entrypoint
│   ├── config.py                  # Configuration settings
│   ├── api/                       # API routes and schemas
│   ├── agent/                     # LangGraph workflow definitions
│   ├── tools/                     # Tool implementations
│   ├── rag/                       # Vector search and embeddings
│   ├── db/                        # Database models and session
│   ├── audit/                     # Audit logging
│   ├── guardrails/                # Safety and validation
│   └── demo_data/                 # Synthetic data generators
├── alembic/                       # Migrations
├── tests/                         # Test suite
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Database Schema

- **customers**: Synthetic customer records.
- **transactions**: Transaction history with anomaly labels.
- **policy_documents**: Mock policies with vector embeddings.
- **workflow_runs**: Execution records and results.
- **audit_events**: Immutable audit trail.

## Configuration

Configuration is managed via environment variables (see `.env.example`).

- `DATABASE_URL`: Connection string for PostgreSQL.
- `USE_MOCK_LLM`: Toggle between mock mode and real LLM usage.
- `OPENAI_API_KEY`: Required if `USE_MOCK_LLM` is false.
- `EMBEDDING_PROVIDER`: Options include `sentence-transformers`, `openai`, or `mock`.

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

## License

This project is for demonstration purposes only.
