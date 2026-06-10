# Agentic CRM Intelligence Platform

> AI-powered Customer Relationship Management system that autonomously monitors a high-volume inbox, triages emails with multi-dimensional intelligence, executes agentic workflows, and surfaces real-time business insights.

<!-- FILL LATER: Replace with your actual repo URL -->
<!-- ![GitHub Repo](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME) -->

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Seeding the Knowledge Base](#seeding-the-knowledge-base)
- [Running the Email Simulation](#running-the-email-simulation)
- [API Reference](#api-reference)
- [Component Breakdown](#component-breakdown)
  - [Ingestion Pipeline](#1-ingestion-pipeline)
  - [Heuristic Pre-filter](#2-heuristic-pre-filter)
  - [LLM Classification Engine](#3-llm-classification-engine)
  - [RAG Pipeline](#4-rag-pipeline)
  - [Autonomous Triage Agent](#5-autonomous-triage-agent)
  - [Web Intelligence Module](#6-web-intelligence-module)
  - [Sentiment Tracker](#7-sentiment-tracker)
  - [Frontend Dashboard](#8-frontend-dashboard)
- [Special Scenario Handling](#special-scenario-handling)
- [Database Schema](#database-schema)
- [Architectural Decisions & Trade-offs](#architectural-decisions--trade-offs)
- [Known Limitations](#known-limitations)
- [Benchmarks](#benchmarks)
- [Demo](#demo)

---

## Overview

This system handles the full email lifecycle — from ingestion to resolution — including edge cases like ransomware threats, GDPR data requests, SLA escalations, and conflicting sentiment signals. The AI acts as an autonomous agent, not just a classifier: it reasons step-by-step, calls tools, retrieves internal policy documents, and decides whether to auto-reply, escalate, or flag for legal review.

---

## Architecture

```mermaid
flowchart TB
 subgraph FE["Frontend — React + Tailwind"]
        F1["Mission Control Inbox"]
        F2["Thread Workspace"]
        F3["Analytics Dashboard"]
  end
 subgraph API["FastAPI Backend"]
        A1["POST /api/ingest"]
        A2["GET /api/status/:job_id"]
        A3["GET /threads/:email"]
        A4["POST /agent/dry-run/:id"]
        A5["GET /rag/search"]
        A6["GET /analytics/sentiment-trend"]
  end
 subgraph QUEUE["Background Job Queue — FastAPI Built-in (Background Tasks)"]
        Q1["Job: classify_email"]
        Q2["Job: run_agent"]
        Q3["Job: scrape_web_intel"]
        Q4["Streaming replay simulator"]
  end
 subgraph HEURISTIC["Layer 1 — Heuristic Pre-filter"]
        H1["Spam detector"]
        H2["Urgency + security flags"]
        H3["Thread linker"]
        H4["Priority scorer"]
  end
 subgraph LLM["Layer 2 — LLM Classification Engine"]
        L1["Gemini / OpenAI API"]
        L2["Structured JSON output"]
        L3["Confidence threshold check"]
  end
 subgraph AGENT["Autonomous Triage Agent — ReAct / CoT"]
        AG1["Reasoning loop — max 6 steps"]
        AG2["search_knowledge_base"]
        AG3["get_thread_history"]
        AG4["draft_reply"]
        AG5["escalate_to_human"]
        AG6["flag_for_legal"]
        AG7["create_internal_ticket"]
        AG8["scrape_public_sentiment"]
  end
 subgraph RAG["RAG Pipeline"]
        R1["6 KB markdown docs"]
        R2["Chunker 300-500 tokens"]
        R3["Embedding model"]
        R4["ChromaDB — vector store"]
        R5["Top-3 retrieval + cite policy"]
  end
 subgraph WEBINTEL["Web Intelligence Module"]
        W1["Async scraper"]
        W2["robots.txt check"]
        W3["In-memory dict cache — 6h TTL"]
        W4["Trustpilot / G2 / Capterra"]
  end
 subgraph DB["PostgreSQL"]
        D1["contacts · threads · emails"]
        D2["actions · audit_log"]
        D3["web_intelligence_cache"]
        D4["Sentiment trend index"]
  end
 subgraph SENTIMENT["Sentiment Tracker"]
        S1["Moving average per sender"]
        S2["3x negative — escalation alert"]
        S3["GET /analytics/sentiment-trend"]
  end
    FE -- REST / WebSocket --> API
    API -- validate + save + enqueue --> QUEUE
    API -- poll --> DB
    QUEUE --> HEURISTIC
    HEURISTIC --> LLM
    HEURISTIC -- spam / security route --> DB
    LLM -- inject thread + RAG chunks --> RAG
    LLM --> AGENT & SENTIMENT & DB
    AGENT --> AG1 & DB
    AG1 --> AG2 & AG3 & AG4 & AG5 & AG6 & AG7 & AG8
    AG2 --> RAG
    AG8 --> WEBINTEL
    AGENT -- store reasoning log --> DB
    RAG --> R1
    R1 --> R2
    R2 --> R3
    R3 --> R4
    R4 --> R5
    WEBINTEL --> W1 & DB
    W1 --> W2
    W2 --> W3
    W3 --> W4
    SENTIMENT --> DB
```

---

## Tech Stack

| Layer | Technology | Justification |
|---|---|---|
| Backend | FastAPI (Python) | Async-native, fast to scaffold, built-in BackgroundTasks eliminates need for Celery/Redis |
| Database | PostgreSQL | Relational integrity for threads/contacts, JSON columns for raw entities and agent logs |
| Vector DB | ChromaDB | Zero-config persistent client, no extra infrastructure needed for a single-node deployment |
| LLM | Gemini 1.5 Flash / GPT-4o-mini | Structured JSON output mode, cost-efficient for high-volume classification |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) | Runs locally, no API cost, sufficient quality for policy document retrieval |
| Frontend | React + Tailwind CSS | Component-based, rapid UI development, good ecosystem for real-time dashboards |
| Background Jobs | FastAPI BackgroundTasks | Built-in, zero extra infra — sufficient for single-instance demo |
| Web Scraping | httpx + BeautifulSoup4 | Async HTTP client, lightweight HTML parsing |
| Caching | In-memory Python dict | 6h TTL cache for web intel scrapes — Redis would be used in production |

---

## Project Structure

```
agentic-crm/
├── backend/
│   ├── main.py                  # FastAPI app, route registration
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── contact.py
│   │   ├── thread.py
│   │   ├── email.py
│   │   ├── action.py
│   │   └── audit_log.py
│   ├── services/
│   │   ├── ingestion.py         # Schema validation, dedup, thread linking
│   │   ├── heuristic_filter.py  # Layer 1: spam, urgency, security flags
│   │   ├── llm_engine.py        # Layer 2: LLM classification, structured output
│   │   ├── agent.py             # ReAct agent loop, tool dispatcher
│   │   ├── rag.py               # Chunking, embedding, ChromaDB retrieval
│   │   ├── web_intel.py         # Async scraper, cache, robots.txt check
│   │   └── sentiment.py         # Moving average, deterioration detection
│   ├── tools/                   # Agent tool implementations
│   │   ├── search_kb.py
│   │   ├── thread_history.py
│   │   ├── contact_profile.py
│   │   ├── draft_reply.py
│   │   ├── escalate.py
│   │   ├── flag_legal.py
│   │   ├── create_ticket.py
│   │   └── scrape_sentiment.py
│   ├── knowledge_base/          # RAG source documents
│   │   ├── pricing_policy.md
│   │   ├── sla_policy.md
│   │   ├── refund_policy.md
│   │   ├── api_docs.md
│   │   ├── compliance_faq.md
│   │   └── escalation_matrix.md
│   ├── migrations/              # Alembic migration files
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Inbox.jsx
│   │   │   ├── ThreadWorkspace.jsx
│   │   │   └── Analytics.jsx
│   │   └── components/
├── data/
│   └── email-data-advanced.json
├── openapi.json                 # Full OpenAPI spec
├── .env.example
├── requirements.txt
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### 1. Clone the repository

```bash
# FILL LATER: Replace with your actual repo URL
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database setup

```bash
# Create the database
createdb agentic_crm

# Run migrations
alembic upgrade head
```

### 4. Frontend setup

```bash
cd frontend
npm install
```

### 5. Start the servers

```bash
# Terminal 1 — Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Backend runs at `http://localhost:8000`
Frontend runs at `http://localhost:5173`
Swagger UI at `http://localhost:8000/docs`

### Seed CRM Contacts

The autonomous agent relies on CRM profile data when calling:

* get_contact_profile(email)
* check_account_status(email)

Before running the simulator, seed demo CRM records:

```bash
python -m services.seed_contacts
```

Example seeded contacts:

| Email                                                                   | Status | Account Value |
| ----------------------------------------------------------------------- | ------ | ------------- |
| [bob.jones@enterprise.net](mailto:bob.jones@enterprise.net)             | VIP    | 84000         |
| [alice.smith@greenlight-npo.org](mailto:alice.smith@greenlight-npo.org) | Active | 12000         |
| [karen.w@retail-co.com](mailto:karen.w@retail-co.com)                   | Active | 6000          |
| [marcus.del@fintech-startup.co](mailto:marcus.del@fintech-startup.co)   | Active | 25000         |

These records provide realistic data for escalation, churn-risk analysis, and agent decision-making.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/agentic_crm

# LLM — use either OpenAI or Gemini
# FILL LATER: Add your actual API key
OPENAI_API_KEY=sk-...
# or
GEMINI_API_KEY=...

# LLM model to use
LLM_MODEL=gpt-4o-mini
# or
LLM_MODEL=gemini-1.5-flash

# Embedding model (runs locally, no key needed)
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ChromaDB path
CHROMA_PERSIST_PATH=./chroma_db

# Email simulation speed (emails per second)
SIMULATION_SPEED=1

# Web intel cache TTL in seconds (default 6 hours)
WEB_INTEL_CACHE_TTL=21600
```

---

## Seeding the Knowledge Base

Before running the system, embed the 6 policy documents into ChromaDB:

```bash
cd backend
python -m services.rag --seed
```

This will:
1. Read all `.md` files from `knowledge_base/`
2. Chunk them into 300–500 token segments with 50-token overlap
3. Embed each chunk using `all-MiniLM-L6-v2`
4. Store vectors in ChromaDB at the path defined in `CHROMA_PERSIST_PATH`

You should see output like:
```
Seeding knowledge base...
  pricing_policy.md    → 8 chunks
  sla_policy.md        → 6 chunks
  refund_policy.md     → 7 chunks
  api_docs.md          → 9 chunks
  compliance_faq.md    → 8 chunks
  escalation_matrix.md → 5 chunks
Done. 43 total chunks embedded and stored.
```

To verify retrieval is working:
```bash
curl "http://localhost:8000/rag/search?q=GDPR+data+portability"
```

---

## Running the Email Simulation

Replay `email-data-advanced.json` as a real-time stream:

```bash
# Default: 1 email per second
python -m services.simulator

# Load test: 10 emails per second
SIMULATION_SPEED=10 python -m services.simulator

# Single email (by message_id)
python -m services.simulator --message-id msg_052
```

Or via the API:
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d @data/email-data-advanced.json
```

---

## API Reference

Full spec available at `/docs` (Swagger UI) or in `openapi.json`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/ingest` | Ingest a new email; returns `job_id` |
| `GET` | `/api/status/{job_id}` | Poll processing status |
| `GET` | `/dashboard/stats` | Counts: Pending, Replied, Escalated, Critical, Spam |
| `GET` | `/threads/{contact_email}` | Full thread with emails, actions, agent logs |
| `POST` | `/respond/{email_id}` | Send a reply; updates status |
| `PATCH` | `/drafts/{id}` | Edit a proposed auto-reply |
| `POST` | `/drafts/{id}/approve` | Approve and send; triggers audit log |
| `GET` | `/analytics/sentiment-trend` | Time-series sentiment per sender or global |
| `GET` | `/analytics/category-breakdown` | Category distribution over date range |
| `GET` | `/rag/search` | Debug: query KB and return chunks + scores |
| `GET` | `/intelligence/reputation` | Latest scraped public sentiment |
| `POST` | `/agent/dry-run/{email_id}` | Agent planning mode — no execution |
| `GET` | `/audit/{entity_type}/{entity_id}` | Full audit history for any entity |
| `GET` | `/contacts/{email}` | Contact profile with churn risk, open threads |
| `PATCH` | `/contacts/{email}/status` | Update contact status (VIP, Blocked, etc.) |

All error responses follow this envelope:
```json
{
  "error_code": "DUPLICATE_MESSAGE_ID",
  "message": "Email with this message_id already exists",
  "details": { "message_id": "msg_001", "existing_id": 42 }
}
```

---

## Component Breakdown

### 1. Ingestion Pipeline

Emails enter via `POST /api/ingest`. The service:

- Validates the JSON schema — rejects missing fields with descriptive errors
- Checks for duplicate `message_id` (idempotent — re-delivery is a no-op)
- Strips empty or whitespace-only bodies before processing
- Truncates bodies over 10,000 characters to the first 8,000 + appends `[TRUNCATED]`
- Links the email to an existing thread by `thread_id`, or creates a new one
- Assigns an initial priority score based on keyword heuristics (before LLM processing)
- Enqueues a background job and immediately returns `{ job_id, status: "queued" }`

Edge cases handled:
- Empty subject → defaults to `"(no subject)"`
- HTML entities in body → stripped before LLM processing
- Out-of-order timestamps → stored as-is, sorted by `timestamp` on read
- Extremely long bodies → chunked for LLM context window

### 2. Heuristic Pre-filter

Runs synchronously on ingest, target under 10ms. Three sub-filters:

**Spam detector** — keyword blocklist (`buy now`, `Nigerian prince`, `100% free`, etc.) + sender domain reputation list. Spam emails are routed to the Ignored queue and never reach the LLM.

**Urgency + security flags** — keyword scan for `URGENT`, `P0`, `legal`, `cease and desist`, `ransomware`, `BTC`, `bitcoin`, `data breach`, `suspicious login`. Security-flagged emails are immediately routed to the security queue regardless of other classification.

**Thread linker** — matches `thread_id` from payload to existing threads. If no match, creates a new thread record.

**Priority scorer** — assigns an integer priority (1–5) based on keyword presence, sender VIP status, and account value from the contacts table.

### 3. LLM Classification Engine

For every non-spam, non-internal email the LLM prompt includes:

1. Full thread history (all prior emails in the thread, ordered by timestamp)
2. Top-3 RAG chunks retrieved for this email's content
3. Contact profile (VIP status, account value, churn risk)
4. Structured output instructions with the exact JSON schema

**Conflicting signal resolution strategy:**

When an email contains contradictory signals (e.g. "I love the product but want a refund and will post publicly"), the engine applies this priority order:

```
Legal / Security > Complaint > Billing > Inquiry
```

The highest-priority category wins. Both signals are preserved in `detected_entities`. If `confidence < 0.70`, the email is automatically flagged `requires_human: true` regardless of category, and the `escalation_reason` field documents the conflict.

**Structured output schema:**
```json
{
  "category": "Complaint|Inquiry|Bug Report|Feature Request|Compliance|Legal|Billing|Spam|Internal|Other",
  "sentiment": "Positive|Neutral|Negative|Mixed",
  "sentiment_score": -1.0,
  "urgency": "Critical|High|Medium|Low",
  "requires_human": true,
  "escalation_reason": "...",
  "suggested_reply": "...",
  "confidence": 0.91,
  "detected_entities": {
    "order_ids": [],
    "ticket_ids": [],
    "monetary_amounts": [],
    "deadlines": [],
    "products_mentioned": []
  }
}
```

### 4. RAG Pipeline

Grounds the agent in internal policy — not LLM parametric memory.

**Knowledge base documents:**

| Document | Contents |
|---|---|
| `pricing_policy.md` | Pricing tiers, non-profit discounts (30% off Standard), pro-rata billing rules, enterprise custom pricing |
| `sla_policy.md` | Uptime SLA (99.9%), incident response times, credit calculation formula, RCA delivery SLA (24h for P0) |
| `refund_policy.md` | No refunds after 14 days, exception process, credits vs refunds, churn retention playbook |
| `api_docs.md` | Rate limits by tier, v1 deprecation timeline, v2 breaking changes, header requirements |
| `compliance_faq.md` | HIPAA BAA availability, GDPR DPA process, SOC 2 Type II status, data residency options |
| `escalation_matrix.md` | Who handles: legal threats, security incidents, PR crises, VIP churns, GDPR requests |

**Chunking strategy:** 300–500 token segments with 50-token overlap. Overlap ensures policy sentences that span chunk boundaries are not lost.

**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` — runs locally, 384-dimension vectors, no API cost. Chosen over OpenAI embeddings to avoid per-token cost at classification time.

**Why ChromaDB over alternatives:**
- FAISS: no persistence without extra code; pure in-memory by default
- pgvector: requires PostgreSQL extension install; adds operational complexity
- Pinecone: cloud-only, API key dependency, overkill for 43 chunks
- ChromaDB: persistent local client, Python-native, zero extra infrastructure

**Retrieval:** On each email, the email body + subject are embedded and top-3 chunks are retrieved by cosine similarity. Chunks are injected into the LLM prompt with their source document name so the LLM can cite the policy in its suggested reply.

Debug endpoint: `GET /rag/search?q=your+query` returns chunks with similarity scores.

### 5. Autonomous Triage Agent

Implements a ReAct (Reason + Act) loop. For each email:

```
Thought: What do I know about this email and sender?
Action: get_thread_history(sender_email)
Observation: [thread history returned]
Thought: Is there a legal risk here?
Action: search_knowledge_base("legal escalation SLA breach")
Observation: [relevant policy chunks returned]
...
```

**Guard rails:**
- Maximum 6 tool calls per email — if unresolved after 6 steps, escalates to human with the full reasoning summary
- Never auto-replies to `urgency: Critical` emails
- Never auto-replies to emails flagged as spam, ransomware, or legal cease-and-desist
- `confidence < 0.70` → always routes to human

**Dry-run mode:** `POST /agent/dry-run/{email_id}` runs the full reasoning loop but does not execute any write actions (no replies sent, no tickets created). Returns the complete reasoning trace.

**Reasoning log** is stored as JSON in the `actions` table:
```json
[
  { "step": 1, "thought": "...", "action": "get_thread_history", "input": "bob@...", "observation": "..." },
  { "step": 2, "thought": "...", "action": "search_knowledge_base", "input": "SLA breach credit", "observation": "..." }
]
```

### 6. Web Intelligence Module

Triggered when:
- Email body contains `review`, `Trustpilot`, `G2`, `Twitter`, `post publicly`
- `sentiment_score < -0.6`
- `category = Complaint` AND `urgency = High or Critical`
- Press or investor inquiry detected

**Flow:**
1. Check in-memory cache — if fresh result exists (under 6h), return immediately
2. Check `robots.txt` for the target domain — skip if disallowed
3. Scrape asynchronously (does not block main pipeline)
4. Store result in cache with 6h TTL
5. Inject as a "Market Intelligence" block into the agent's context

If scraping fails for any reason, the agent proceeds without web data — graceful degradation.

> **Note:** In-memory cache is used for simplicity in this build. In production this would be replaced with Redis to survive server restarts and share cache across multiple worker instances.

### 7. Sentiment Tracker

Tracks `sentiment_score` over time per sender using a rolling moving average.

- Scores are stored on every email record in PostgreSQL
- Moving average is computed over the last N emails per sender
- **Deterioration detection:** 3 or more consecutive negative scores from one sender triggers an escalation alert and sets the contact's `churn_risk_score` to High
- Exposed via `GET /analytics/sentiment-trend?sender=X&days=30`

### 8. Frontend Dashboard

**View 1 — Mission Control Inbox**
- Filterable, sortable email list with visual badges for Sentiment, Category, and Urgency
- Tabs: All | Needs Human | Auto-Replied | Escalated | Spam
- Real-time updates via polling (configurable interval)
- Thread grouping: multiple emails from the same sender collapsed into one row
- Bulk actions: Mark as Spam, Assign, Archive
- Full-text search across subject and body

**View 2 — Thread Workspace**
- Left pane: email content with entity highlights (monetary amounts, ticket IDs)
- Center pane: chronological thread timeline with per-message sentiment indicator
- Right pane: contact profile card (VIP status, account value, churn risk score)
- Agent Reasoning Panel: collapsible Thought → Action → Observation trace
- RAG Context Panel: retrieved chunks with similarity scores
- Action area: Approve & Send / Edit Draft / Escalate / Mark Spam
- Web intelligence block shown inline when scraped data is available

**View 3 — Analytics Dashboard**
- Sentiment trend line chart (per sender or global)
- Category distribution chart
- Response time heatmap by hour of day
- At-risk accounts panel: senders with deteriorating sentiment or unresolved threads over 48h
- Agent performance metrics: auto-reply rate, escalation rate, average confidence score

---

## Special Scenario Handling

### GDPR Data Request (`msg_052`)
- Detected via keywords: `GDPR`, `Article 20`, `data portability`, `right to receive`
- Classified as `category: Compliance`, `urgency: High`, `requires_human: true`
- Agent calls `flag_for_legal()` and `create_internal_ticket()` with a 30-day statutory deadline
- Auto-acknowledgement is generated citing the 30-day statutory window — but is held for human approval before sending
- Does **not** receive a generic auto-reply

### Ransomware Threat (`msg_038`)
- Detected at heuristic layer via keywords: `BTC`, `bitcoin`, `publish data`, `ransomware`
- Immediately flagged `urgency: Critical`, `category: Legal`
- Routed to security queue before LLM processing
- Agent calls `flag_for_legal()` and `escalate_to_human()` with security brief
- **Never auto-replied under any circumstances**

### Chatbot Misinformation (`msg_056`)
- Agent retrieves actual refund policy via RAG
- Compares chatbot-stated policy with retrieved policy and documents the discrepancy in the escalation brief
- Drafts an empathetic reply that acknowledges the confusion without admitting legal liability
- Escalates to human with a summary of what the chatbot said vs. actual policy

### Reputation Crisis — Karen (`msg_033`)
- Detected: 3 emails from `karen.w@retail-co.com` with zero replies and negative sentiment
- Sentiment tracker fires a deterioration alert
- Web intelligence module is triggered: scrapes current G2/Trustpilot score
- Agent generates a high-priority escalation brief with a retention offer from `refund_policy.md`

### Bob — SLA Breach + Legal Escalation (`msg_060`)
Full agent reasoning trace for this scenario:

```
Step 1 — get_thread_history(bob.jones@enterprise.net)
         → 4 prior emails retrieved: P0 outage → SLA breach → RCA request → legal threat

Step 2 — search_knowledge_base("SLA breach credit obligation")
         → sla_policy.md: "P0 incidents exceeding 4h entitle customer to 10% monthly credit"

Step 3 — check_account_status(bob.jones@enterprise.net)
         → Enterprise tier, account value $84,000, renewal on hold

Step 4 — Recognises legal threat in msg_060 body
         → flag_for_legal(email_id, issue_type="SLA breach + legal review")

Step 5 — draft_reply(context, tone="empathetic", policy_refs=["sla_policy.md"])
         → Holding reply citing SLA credit policy, no admission of liability

Step 6 — escalate_to_human(email_id, reason="Legal threat + Enterprise renewal at risk", priority="Critical")
         → Pre-filled brief with full thread summary and credit calculation
```

### Alice — Conflicting Thread Signals (`msg_041`)
- Agent reads the full 5-email thread before classifying
- Thread history: pricing inquiry → non-profit discount → close → upgrade → pro-rata billing question
- RAG retrieves `pricing_policy.md` with the correct tier for Alice's current plan
- Billing question is answered with the correct pro-rata calculation, not generic pricing

---

## Database Schema

```sql
-- contacts
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    company VARCHAR(255),
    status VARCHAR(50) DEFAULT 'Active', -- VIP | Blocked | Active | Churned
    account_value NUMERIC(12, 2),
    churn_risk_score NUMERIC(3, 2),      -- 0.0 to 1.0
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_contact_at TIMESTAMPTZ
);

-- threads
CREATE TABLE threads (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT,
    sender_email VARCHAR(255) REFERENCES contacts(email),
    first_seen_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'Open',   -- Open | Resolved | Escalated | Ignored
    assigned_to VARCHAR(255)
);

-- emails
CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER REFERENCES threads(id),
    message_id VARCHAR(255) UNIQUE NOT NULL,  -- idempotency key
    sender VARCHAR(255),
    subject TEXT,
    body TEXT,
    timestamp TIMESTAMPTZ,
    sentiment_score NUMERIC(4, 2),
    category VARCHAR(100),
    urgency VARCHAR(50),
    requires_human BOOLEAN,
    confidence NUMERIC(4, 2),
    raw_entities JSONB,
    status VARCHAR(50) DEFAULT 'Received'  -- Received | Processing | Replied | Escalated | Ignored
);

-- processing_jobs
CREATE TABLE processing_jobs (
id SERIAL PRIMARY KEY,
email_id INTEGER REFERENCES emails(id),
status VARCHAR(50) NOT NULL,  -- Queued | Processing | Completed | Failed
error_message TEXT,
created_at TIMESTAMPTZ DEFAULT NOW(),
completed_at TIMESTAMPTZ
);

CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);


-- actions
CREATE TABLE actions (
    id SERIAL PRIMARY KEY,
    email_id INTEGER REFERENCES emails(id),
    agent_reasoning_log JSONB,
    action_type VARCHAR(100),  -- Auto-Reply | Escalate | Legal-Flag | Ticket-Created | Ignored
    proposed_content TEXT,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(255),
    executed_at TIMESTAMPTZ
);

-- drafts
CREATE TABLE drafts (
id SERIAL PRIMARY KEY,
email_id INTEGER REFERENCES emails(id),
content TEXT NOT NULL,
status VARCHAR(50) DEFAULT 'Pending', -- Pending | Edited | Approved | Sent
created_at TIMESTAMPTZ DEFAULT NOW(),
approved_at TIMESTAMPTZ
);

CREATE INDEX idx_drafts_email_id ON drafts(email_id);


-- knowledge_chunks
CREATE TABLE knowledge_chunks (
    id SERIAL PRIMARY KEY,
    source_doc VARCHAR(255),
    chunk_text TEXT,
    embedding vector(384),  -- pgvector extension (ChromaDB used instead — this is for reference)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- web_intelligence_cache
CREATE TABLE web_intelligence_cache (
    id SERIAL PRIMARY KEY,
    source_url TEXT,
    target_entity VARCHAR(255),
    scraped_data JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- audit_log
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(100),
    entity_id INTEGER,
    action VARCHAR(255),
    performed_by VARCHAR(255),  -- agent | user_id
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    diff JSONB
);

-- indexes
CREATE INDEX idx_emails_thread_id ON emails(thread_id);
CREATE INDEX idx_emails_sender ON emails(sender);
CREATE INDEX idx_emails_sentiment_score ON emails(sentiment_score);
CREATE INDEX idx_emails_timestamp ON emails(timestamp);
CREATE INDEX idx_threads_sender_email ON threads(sender_email);
CREATE INDEX idx_threads_status ON threads(status);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
```

---

## Architectural Decisions & Trade-offs

### FastAPI BackgroundTasks vs Celery + Redis
**Decision:** FastAPI's built-in `BackgroundTasks` over Celery + Redis.

**Trade-off:** BackgroundTasks run in the same process as the web server. If the server restarts mid-processing, the job is lost. Celery with Redis would persist jobs across restarts and allow horizontal scaling across multiple workers. For a single-instance demo, BackgroundTasks is sufficient and eliminates two infrastructure dependencies.

**Production path:** Replace with Celery + Redis when deploying multi-instance.

### ChromaDB vs pgvector
**Decision:** ChromaDB as a standalone vector store over pgvector.

**Trade-off:** Splitting vector storage from relational storage adds a second data store to operate. pgvector would keep everything in one database. However, pgvector requires a PostgreSQL extension that may not be available in all hosting environments, and ChromaDB's Python API is significantly simpler for a take-home build. The 43-chunk knowledge base is small enough that ChromaDB's performance is not a concern.

**Production path:** Migrate to pgvector to reduce operational complexity.

### In-memory cache vs Redis for Web Intel
**Decision:** Python dict with TTL logic over Redis.

**Trade-off:** Cache is lost on server restart. Acceptable for a demo where scrapes are inexpensive to repeat. Redis would provide persistence, pub/sub for cache invalidation, and shared cache across instances.

### sentence-transformers vs OpenAI Embeddings
**Decision:** Local `all-MiniLM-L6-v2` over `text-embedding-ada-002`.

**Trade-off:** Lower embedding quality (384 vs 1536 dimensions) but zero per-token cost, no network latency on retrieval, and no API key dependency for the RAG pipeline. For a 43-chunk knowledge base the quality difference is negligible.

### Conflicting Signal Resolution
When an email contains contradictory signals, the system applies a strict priority order: `Legal/Security > Complaint > Billing > Inquiry > Other`. The highest-priority signal determines the `category` field. Both signals are preserved in `detected_entities` and documented in `escalation_reason`. Any classification with `confidence < 0.70` is automatically flagged for human review regardless of resolved category.

### Job Queue + Worker Model

Although the implementation uses FastAPI BackgroundTasks, the architecture models processing as a Job Queue → Worker pattern.

Flow:

Email Ingested
→ processing_jobs record created
→ Worker picks up queued job
→ Classification
→ Agent execution
→ Job marked Completed / Failed

This mirrors production systems that would typically use Redis + Celery while keeping the demo implementation lightweight and infrastructure-free.

---

## Known Limitations

<!-- FILL LATER: Document what you ran out of time for or what you know is incomplete -->
<!-- Examples to consider:
- Web scraping targets are mocked / real scraping is rate-limited
- WebSocket real-time updates replaced with polling at X second intervals
- Frontend search is client-side only, not full-text indexed
- Churn prediction score is rule-based, not ML-trained
- Email simulation does not handle attachments
-->

---

## Benchmarks

<!-- FILL LATER: Run these queries against your actual database and paste the EXPLAIN ANALYZE output -->

**Target:** `GET /threads/{contact_email}` must return in under 100ms for threads up to 50 emails.

```
-- FILL LATER: paste EXPLAIN ANALYZE output here
EXPLAIN ANALYZE
SELECT e.* FROM emails e
JOIN threads t ON e.thread_id = t.id
WHERE t.sender_email = 'bob.jones@enterprise.net'
ORDER BY e.timestamp ASC;
```

**Target:** Sentiment trend query over 30 days must use index scan.

```
-- FILL LATER: paste EXPLAIN ANALYZE output here
EXPLAIN ANALYZE
SELECT sender, sentiment_score, timestamp FROM emails
WHERE sender = 'karen.w@retail-co.com'
AND timestamp > NOW() - INTERVAL '30 days'
ORDER BY timestamp ASC;
```

**Target:** Vector similarity search must return top-3 chunks in under 200ms.

<!-- FILL LATER: paste ChromaDB query timing here -->

---

## Demo

<!-- FILL LATER: Replace with your actual screen recording link -->
<!-- Suggested structure for the 5-10 min recording:
  1. (0:00 - 1:30) Email stream ingestion — show the simulator running, emails appearing in the inbox
  2. (1:30 - 3:30) Agent reasoning trace for bob_outage escalation — show the full Thought/Action/Observation log
  3. (3:30 - 5:00) RAG retrieval debug view — GET /rag/search with a policy query, show chunks + scores
  4. (5:00 - 7:00) Karen churn scenario — show 3-email deterioration, web intel trigger, escalation brief
  5. (7:00 - 8:30) Analytics dashboard — sentiment trend, category breakdown, at-risk accounts
-->

Screen recording: **[FILL LATER — link to Loom / YouTube unlisted]**
