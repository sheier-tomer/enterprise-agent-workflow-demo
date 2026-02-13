# Enterprise Agentic Workflow Engine

## About The Project

This repository serves as a reference implementation for an **Agentic Workflow Engine** designed for high-compliance environments, such as financial services. It demonstrates how to orchestrate complex, multi-step AI workflows while maintaining strict audit trails, guardrails, and deterministic behavior.

The core use case modeled here is **Financial Transaction Analysis**: automating the review of customer transactions to detect anomalies, cross-reference them with internal policies, and generate an explanation or escalation request.

**Key Technical Concepts:**
*   **Deterministic Orchestration**: Using [LangGraph](https://langchain-ai.github.io/langgraph/) to define workflows as state machines, ensuring predictable paths (Ingest → Detect → Retrieve → Decide).
*   **Retrieval-Augmented Generation (RAG)**: Using PostgreSQL with `pgvector` to semantically search policy documents relevant to the specific anomaly.
*   **Auditability**: Every step, tool call, and decision is logged to an immutable append-only audit trail.
*   **Guardrails**: Input validation, content filtering, and confidence thresholds prevent "hallucinations" and unauthorized actions.

---

## Architecture

The system is built as an async event-driven REST API.

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                      Client (REST API)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI API Layer                        │
│  • GET /customers                                           │
│  • POST /tasks/run                                          │
│  • GET /tasks/{id}                                          │
│  • GET /tasks/{id}/audit                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Guardrails Enforcement Layer                   │
│  • Tool allowlist validation                                │
│  • Pydantic schema validation                               │
│  • Rate limiting & Content filtering                        │
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

1.  **Ingest Transactions**: Fetches and aggregates transaction history for the given customer.
2.  **Detect Anomalies**: Applies statistical heuristics to identify outliers (e.g., sudden spikes, unusual merchants).
3.  **Retrieve Policies**: Vectors are generated for the anomaly context and used to query the `policy_documents` table for relevant compliance rules.
4.  **Draft Explanation**: An LLM (or mock agent) synthesizes the transaction data and policies into a coherent narrative.
5.  **Evaluate Confidence**: A decision node checks the confidence score of the analysis.
    *   **Score < 0.7**: Routes to **Escalate** (flag for human review).
    *   **Score ≥ 0.7**: Routes to **Finalize** (auto-approve/reject).

---

## Getting Started

### Prerequisites

*   Docker & Docker Compose
*   Git

### Option 1: Run with Docker (Recommended)

This is the fastest way to explore the project. It spins up the API and a pre-configured PostgreSQL database.

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd EnterpriseAIWorkflow

# 2. Start the services
docker-compose up --build

# 3. Access the API
# The app will be available at http://localhost:8000
# Note: Initial startup takes ~30s to seed the database and build vector indexes.
```

### Option 2: Local Development

If you wish to modify the code or run it without Docker containers for the app.

```bash
# 1. Install dependencies
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env to set your database URL

# 3. Start PostgreSQL (we still use Docker for the DB)
docker-compose up db -d

# 4. Run database migrations
alembic upgrade head

# 5. Start the application
python -m app.main
```

### Verification

Once running, you can check the health status:

```bash
curl http://localhost:8000/api/v1/health
```

Or open the Swagger UI in your browser: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Usage Guide

### 1. Identify a Customer

The system is seeded with synthetic data. First, retrieve a valid customer ID.

```bash
curl http://localhost:8000/api/v1/customers?limit=1
```

*Response (example):*
```json
[
  {
    "id": "a1b2c3d4-...",
    "name": "John Doe",
    ...
  }
]
```

### 2. Trigger an Analysis Workflow

Use the customer ID to start an async analysis task.

```bash
curl -X POST http://localhost:8000/api/v1/tasks/run \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "YOUR_CUSTOMER_UUID_HERE",
    "analysis_window_days": 30
  }'
```

### 3. Retrieve Results

Poll the status endpoint to get the final report and decision.

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}
```

### 4. Inspect the Audit Trail

View the step-by-step execution log to understand *why* the decision was made.

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}/audit
```

---

## Configuration

The application is configured via environment variables. See `.env.example` for all options.

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `USE_MOCK_LLM` | `true` for deterministic local runs, `false` to use OpenAI | `true` |
| `OPENAI_API_KEY` | Required if `USE_MOCK_LLM=false` | - |
| `EMBEDDING_PROVIDER` | `sentence-transformers` (local), `openai`, or `mock` | `sentence-transformers` |

---

## Project Structure

*   `app/agent/`: Contains the LangGraph state machine and node definitions.
*   `app/guardrails/`: Logic for validating inputs and outputs.
*   `app/rag/`: Vector search implementation using `pgvector`.
*   `app/audit/`: Services for writing immutable logs to the database.
*   `app/tools/`: The specific "skills" the agent can call (Analyzer, Detector, etc.).

## Disclaimer

**This project is for educational and demonstration purposes only.**

*   All data is synthetic (generated via `Faker`).
*   Policy documents are mock representations.
*   This system is not intended for production use with real customer data.
