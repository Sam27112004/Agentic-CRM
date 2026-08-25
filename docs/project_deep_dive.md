# Agentic CRM — Deep Dive Explanation & Interview Simulation

## PART 1: WHAT IS THIS PROJECT?

**Agentic CRM** is an AI-powered Customer Relationship Management (CRM) email triage system. Instead of human agents manually reading and responding to every customer email, this system uses an **autonomous AI agent** that reads each incoming email, reasons about it, and decides what to do — all on its own.

Think of it like this: a company receives hundreds of customer emails daily. Instead of hiring a team of support agents to sort and reply to all of them, this system automates that entire process using AI.

---

## PART 2: TECHNOLOGY STACK

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python + FastAPI | REST API server |
| **Database** | PostgreSQL + SQLAlchemy | Stores all data |
| **ORM Migrations** | Alembic | Database schema versioning |
| **AI/LLM** | Google Gemini (gemini-3.1-flash-lite) | Brain of the agent |
| **Vector DB** | ChromaDB | Stores embeddings for knowledge base |
| **Embeddings** | SentenceTransformers (all-MiniLM-L6-v2) | Converts text to vectors |
| **Data validation** | Pydantic v2 | Input validation and schemas |
| **HTTP Client** | httpx | Web scraping / external calls |
| **Frontend** | React + Vite + TailwindCSS | Dashboard UI |

---

## PART 3: SYSTEM ARCHITECTURE (End-to-End Flow)

When an email arrives, it goes through 4 distinct layers:

```
Email Received
      |
      v
[Layer 1: Ingestion API]  → validates, deduplicates, creates DB records, queues job
      |
      v
[Layer 2: Heuristic Pre-filter]  → fast rule-based checks (spam? security? legal?)
      |
      v
[Layer 3: LLM Classification]  → Gemini AI classifies category, sentiment, urgency
      |
      v
[Layer 4: Autonomous ReAct Agent]  → reasons + calls tools → draft reply / escalate
```

---

## PART 4: EACH COMPONENT EXPLAINED IN DEPTH

### A. Ingestion Pipeline (`backend/services/ingestion.py`)

**What it does**: Receives raw email data via HTTP POST to `/api/ingest`.

**Step-by-step**:
1. Validates the email payload using Pydantic (`IngestEmailPayload` schema)
2. Checks for duplicate `message_id` to prevent processing same email twice
3. Cleans the subject and body (strips HTML entities, truncates if > 10,000 chars)
4. Gets or creates a **Contact** record for the sender
5. Gets or creates a **Thread** record (groups related emails together)
6. Creates the **Email** record in the DB with status = "Received"
7. Creates a **ProcessingJob** record with status = "Queued"
8. Returns a `job_id` to the caller — processing happens asynchronously in the background

**Why async?** Because LLM calls can take 2-5 seconds. You don't want the HTTP request to hang. FastAPI's `BackgroundTasks` handles this.

---

### B. Heuristic Pre-Filter (`backend/services/heuristic_filter.py`)

**What it does**: A fast, cheap, rule-based filter that runs BEFORE calling the expensive LLM.

**Why?** Calling Gemini for every spam email would waste API quota and money.

**How it works**:
- Checks for **SPAM patterns**: keywords like "buy now", "nigerian prince", "100% free"
- Checks for **SECURITY patterns**: "ransomware", "bitcoin", "data breach", "suspicious login"
- Checks for **LEGAL patterns**: "cease and desist", "GDPR", "right to be forgotten"
- Checks if sender is from a **blocklisted domain** (mailinator.com, tempmail.com)
- Computes a **priority score** (1-5) based on urgency keywords and sender domain

If the email is spam → mark as "Ignored", skip LLM.
If it's a security threat → mark as "Escalated" immediately, skip LLM.
Otherwise → pass it to the LLM classifier.

---

### C. LLM Classification Engine (`backend/services/llm_classifier.py`)

**What it does**: Uses Google Gemini to deeply understand the email and produce a structured classification.

**Context it injects into the prompt**:
1. The email itself (From, Subject, Body)
2. Thread history (previous emails in the same conversation)
3. RAG chunks (top-3 relevant policy documents from the knowledge base)
4. Contact profile (name, company, account value, churn risk score)

**Output** (structured JSON validated by Pydantic):
- `category`: Complaint / Inquiry / Bug Report / Feature Request / Legal / Billing / Spam / etc.
- `sentiment`: Positive / Negative / Neutral / Mixed
- `sentiment_score`: float from -1.0 to +1.0
- `urgency`: Critical / High / Medium / Low
- `requires_human`: true/false
- `confidence`: 0.0 to 1.0 — how confident the LLM is
- `detected_entities`: order IDs, ticket IDs, monetary amounts, deadlines, products

**Post-processing rules (business logic on top of LLM)**:
- If `confidence < 0.70` → automatically set `requires_human = True`
- If `urgency = Critical` → automatically set `requires_human = True`
- Clamp `sentiment_score` to [-1, 1] range
- If LLM returns invalid category → fallback to "Other"

**Conflict resolution**: If signals conflict (e.g., email sounds positive but contains a legal threat), the system uses a priority ranking: `Legal > Compliance > Complaint > Billing > Bug Report > Feature Request > Inquiry`

**Sentiment deterioration detection**: If a customer sends 3 consecutive emails all with sentiment_score < -0.2, the system auto-escalates and triggers web scraping to check public reputation.

---

### D. RAG (Retrieval-Augmented Generation) Knowledge Base (`backend/services/rag.py`)

**What is RAG?** Instead of the LLM relying only on its training data, RAG lets you inject *your own specific company documents* into the prompt. This grounds the AI in your actual policies.

**Knowledge base documents** (stored as `.md` files):
- `refund_policy.md` — refund rules
- `pricing_policy.md` — pricing tiers
- `sla_policy.md` — service level agreements
- `escalation_matrix.md` — escalation rules
- `compliance_faq.md` — GDPR/compliance answers
- `api_docs.md` — API documentation

**How RAG works**:
1. At startup, each document is split into 300-word chunks (with 50-word overlap)
2. Each chunk is converted into a **vector embedding** using `SentenceTransformer (all-MiniLM-L6-v2)`
3. Embeddings are stored in **ChromaDB** (a vector database that persists to disk)
4. When classifying an email, query text (subject + body) is embedded and the top-3 most semantically similar chunks are retrieved
5. These chunks are injected into the LLM prompt

**Similarity scoring**: ChromaDB returns L2 (Euclidean) distance. This is converted to a 0-1 similarity score using `1 / (1 + distance)`.

---

### E. Autonomous ReAct Agent (`backend/services/agent.py`)

**What is ReAct?** ReAct stands for **Reason + Act**. It's an agentic pattern where the AI alternates between:
- **Thinking** (reasoning about what to do next)
- **Acting** (calling a tool)
- **Observing** (reading the tool's output)
- ...then repeating until done

**The loop**:
1. Agent receives email + classification context
2. Calls Gemini with a system prompt describing all available tools
3. Gemini responds with a JSON: `{"thought": "...", "action": "tool_name", "action_input": {...}, "is_final": false}`
4. The system executes the tool, gets the result (observation)
5. Observation is fed back to Gemini as the next message
6. Loop continues for up to **6 steps** (MAX_STEPS)
7. If 6 steps exhausted without resolution → auto-escalate to human

**Guard rails** (cannot be overridden by the agent):
- Emails with `category = Spam/Security/Legal` → NEVER auto-reply
- Emails with `urgency = Critical` → NEVER auto-reply
- Emails with `confidence < 0.70` → NEVER auto-reply

**Dry-run mode**: The agent can run its full reasoning loop without executing any write actions. Used for debugging and previewing what the agent would do.

---

### F. Agent Tools (`backend/services/agent_tools.py`)

The agent has 7 tools it can call:

| Tool | What it does |
|---|---|
| `get_thread_history` | Fetches all previous emails from the same sender |
| `search_knowledge_base` | Queries RAG for relevant policy documents |
| `draft_reply` | Creates a Draft record with AI-written reply text |
| `escalate_to_human` | Marks email as "Escalated", creates Action record |
| `flag_for_legal` | Flags email for legal review with threat summary |
| `create_internal_ticket` | Creates an internal support ticket |
| `scrape_public_sentiment` | Scrapes Trustpilot/G2 for company reputation data |

**Caching in `scrape_public_sentiment`**: Uses a two-layer cache:
1. In-memory Python dict (fastest, lost on restart)
2. PostgreSQL `web_intelligence_cache` table (persistent, 6-hour TTL)

This avoids hammering external sites on every email from the same company.

**robots.txt compliance**: Before scraping, the tool fetches and parses the target site's `robots.txt` to check if scraping is allowed. This is an ethical/legal consideration.

**TOOL_REGISTRY**: A dictionary that maps tool names to their function, description, parameters, and whether they need a DB session. The agent uses this to dynamically discover and call tools.

---

### G. Database Models (PostgreSQL + SQLAlchemy)

The system has **10 database models**:

| Model | Table | Purpose |
|---|---|---|
| `Email` | `emails` | The raw email data + classification results |
| `Thread` | `threads` | Groups related emails from same sender/conversation |
| `Contact` | `contacts` | Customer profile (name, company, account_value, churn_risk_score) |
| `Action` | `actions` | Records every action taken (escalate, reply, ticket) + agent reasoning log (JSONB) |
| `Draft` | `drafts` | AI-generated draft replies awaiting human approval |
| `ProcessingJob` | `processing_jobs` | Tracks async job status (Queued → Processing → Completed/Failed) |
| `AuditLog` | `audit_logs` | Immutable audit trail of every change |
| `KnowledgeChunk` | `knowledge_chunks` | (Optional SQL storage of KB chunks) |
| `WebIntelligenceCache` | `web_intelligence_cache` | Cached web scraping results |

**JSONB columns**: `Action.agent_reasoning_log` and `Email.raw_entities` use PostgreSQL's JSONB type, which allows storing and querying nested JSON directly in the database.

**Indexes**: The `Email` model has 4 indexes on `thread_id`, `sender`, `sentiment_score`, and `timestamp` — optimized for the most common query patterns.

---

### H. FastAPI Backend (`backend/main.py`)

**Main API endpoints**:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/ingest` | Ingest a new email |
| GET | `/api/status/{job_id}` | Check processing job status |
| GET | `/api/emails` | List emails with filtering, sorting, pagination |
| PATCH | `/api/emails/{id}` | Update email status/category |
| GET | `/dashboard/stats` | Dashboard counts (Pending, Replied, Escalated, etc.) |
| GET | `/threads/{contact_email}` | Full thread view for a contact |
| GET | `/rag/search` | Debug: test the RAG knowledge base |
| POST | `/agent/dry-run/{email_id}` | Run agent reasoning without writing |
| POST | `/respond/{email_id}` | Send a manual reply |
| PATCH | `/drafts/{id}` | Edit an AI draft |
| POST | `/drafts/{id}/approve` | Approve and "send" a draft |
| GET | `/analytics/sentiment-trend` | Sentiment over time |
| GET | `/analytics/category-breakdown` | Email categories pie chart data |
| GET | `/analytics/at-risk-accounts` | Contacts with high churn risk |
| GET | `/analytics/agent-metrics` | Agent run stats |
| GET | `/analytics/response-heatmap` | Email volume by day/hour |
| GET | `/contacts/{email}` | Get contact profile |
| GET | `/audit/{entity_type}/{id}` | Audit history |

---

### I. Frontend (React + Vite + TailwindCSS)

**Three main pages**:

1. **Inbox** (`Inbox.jsx`) — Email list with filtering (category, urgency, status), sorting, search, and pagination. Clicking an email opens the Thread Workspace.

2. **Thread Workspace** (`ThreadWorkspace.jsx`) — Shows the full conversation history, contact profile (with churn risk), agent reasoning trace (step-by-step AI thinking), AI-generated drafts, and lets the human approve/edit/send responses.

3. **Analytics** (`Analytics.jsx`) — Charts showing:
   - Sentiment trend over time
   - Category breakdown (pie chart)
   - At-risk accounts (high churn risk)
   - Agent metrics (total runs, avg steps, escalation rate)
   - Response heatmap (email volume by day × hour)

**Routing**: Uses simple hash-based routing (`window.location.hash`). No React Router needed. URLs like `#thread/email@example.com/42` navigate to a specific email in a thread.

---

## PART 5: KEY DESIGN DECISIONS & WHY

1. **Why async job processing?** LLM calls are slow (2-5s). We don't want the API to block. We return a `job_id` immediately and process in background.

2. **Why heuristics before LLM?** Saves money and API quota. 30-40% of emails are obvious spam/security. No need to pay for LLM calls on those.

3. **Why RAG instead of just prompting Gemini?** Gemini doesn't know your company's specific refund policy or SLA commitments. RAG injects the *exact* relevant policy text into the prompt, making replies accurate and grounded.

4. **Why ReAct pattern for the agent?** Simple classification is a one-shot decision. But complex emails may need multiple steps: check thread history → search KB → decide to escalate. ReAct allows multi-step reasoning.

5. **Why store the reasoning log in the DB?** Full transparency and auditability. Humans can see exactly *why* the AI made each decision — crucial for enterprise trust and compliance.

6. **Why MAX_STEPS = 6?** Prevents infinite loops. If the agent can't resolve in 6 steps, it auto-escalates to a human rather than spinning forever.

7. **Why JSONB for reasoning logs?** The structure of a reasoning trace varies (different tools, different step counts). JSONB lets you store this flexible nested structure without schema migrations.

8. **Why confidence threshold at 0.70?** Below 70% confidence, the LLM itself is uncertain. Better to escalate to a human than risk a wrong automated reply that could damage customer relationships.

---

## PART 6: INTERVIEW Q&A SIMULATION

---

**Q1: Can you explain what your Agentic CRM project does at a high level?**

> "Agentic CRM is an AI-powered email triage system for customer support. When a customer sends an email, instead of routing it to a human immediately, the system uses an autonomous AI agent to read the email, understand its intent and urgency, search relevant company policies, and then decide on an action — whether that's drafting an automated reply, escalating to a human, flagging it for legal review, or creating an internal ticket. The agent uses the ReAct pattern — it reasons, acts by calling tools, observes the result, and loops until it reaches a decision. The whole system is built with FastAPI on the backend, PostgreSQL for persistence, and Google Gemini as the LLM brain."

---

**Q2: What is the ReAct pattern and why did you use it?**

> "ReAct stands for Reason + Act. It's an agentic framework where the LLM doesn't just give a one-shot answer — instead it operates in a loop. In each step, the model thinks out loud in a 'thought' field, selects an 'action' (which is a tool call), and I execute that tool. The result (observation) is fed back to the model as the next message. The model then continues reasoning based on what it observed. I used ReAct because customer emails are often complex — resolving them may require first checking the customer's history, then searching the knowledge base for the relevant policy, and only then drafting a reply. A single-shot prompt can't do multi-step reasoning like that."

---

**Q3: What is RAG and how did you implement it?**

> "RAG stands for Retrieval-Augmented Generation. The idea is that instead of relying solely on the LLM's training data, you retrieve relevant documents from your own knowledge base and inject them into the prompt. In my project, the knowledge base contains company documents like the refund policy, SLA commitments, and escalation matrix — all stored as Markdown files. During startup, these files are chunked into 300-word pieces with 50-word overlap and embedded using the sentence-transformers library with the all-MiniLM-L6-v2 model. These embeddings are stored in ChromaDB, a vector database. When classifying or replying to an email, I embed the email's subject and body, query ChromaDB for the top-3 most similar chunks, and inject those chunks directly into the LLM's prompt. This ensures the AI's replies are grounded in actual company policy rather than hallucinated."

---

**Q4: How do you prevent the AI from making bad decisions?**

> "There are multiple layers of safety. First, a heuristic pre-filter catches obvious spam, security threats, and legal emails using keyword pattern matching before the LLM even runs. Second, in the LLM classifier, I post-process the output — if confidence is below 70%, requires_human is automatically set to true regardless of what the LLM said. Third, in the agent itself, there are hard-coded guard rails: emails categorized as Spam, Security, or Legal, or with Critical urgency, can never receive an auto-reply — the agent must escalate or flag for legal. Fourth, MAX_STEPS = 6 prevents the agent from looping forever — if it can't resolve in 6 steps, it auto-escalates. Fifth, there's a dry-run mode where you can run the full agent reasoning without actually committing any write actions, which lets humans inspect the agent's thinking before trusting it."

---

**Q5: How does the job processing work asynchronously?**

> "When the `/api/ingest` endpoint receives an email, it immediately creates an Email record and a ProcessingJob record with status 'Queued', and returns the job_id to the caller. Then, using FastAPI's BackgroundTasks, it kicks off the job processor in the background without blocking the HTTP response. The JobProcessor class then runs the full pipeline: heuristic filter → LLM classification → sentiment deterioration check → ReAct agent. The job status transitions from Queued → Processing → Completed or Failed. The client can poll `/api/status/{job_id}` to check progress. This design means the API always responds in milliseconds even though the full pipeline takes several seconds."

---

**Q6: Explain the database schema and your key design decisions.**

> "The schema has 9 main tables. The core entity is Email, which stores the raw email content plus all the classification fields added by the LLM — category, urgency, sentiment_score, confidence, requires_human, and raw_entities as JSONB. Emails are grouped into Threads by thread_id, and each Thread is linked to a Contact which stores customer profile data like account_value and churn_risk_score. When the agent takes an action, it creates an Action record that stores the action_type, proposed_content, and most importantly the agent_reasoning_log in a JSONB column — this is the complete step-by-step trace of the agent's thinking. AI-generated replies go into Draft records which are held in a 'Pending' state until a human approves them. All state changes are recorded in the AuditLog table. I used PostgreSQL's JSONB type for the reasoning log and entities because their structure is dynamic and doesn't fit neatly into a fixed schema."

---

**Q7: What is ChromaDB and why did you use it over a traditional database for vectors?**

> "ChromaDB is a purpose-built vector database. Traditional relational databases like PostgreSQL can store data, but they're not optimized for similarity search — finding the most semantically similar text to a query. ChromaDB uses ANN (Approximate Nearest Neighbor) algorithms to efficiently find the closest vectors in high-dimensional space, which is exactly what we need for RAG. It also integrates well with Python, supports persistent storage to disk, and has a simple API. The alternative would have been pgvector (a PostgreSQL extension for vectors), but ChromaDB required no database schema changes and was simpler to set up for this project."

---

**Q8: How does sentiment deterioration detection work?**

> "After classifying each email, the system queries the last 3 emails from the same sender, ordered by timestamp descending. If all 3 have a sentiment_score below -0.2 (meaning consistently negative), the system detects 'sentiment deterioration' — a pattern suggesting the customer is increasingly frustrated. When this is detected, the current email is automatically escalated to 'Escalated' status with 'High' urgency, category overridden to 'Complaint', and requires_human set to true. Additionally, the system looks up the customer's company from their Contact record and triggers the scrape_public_sentiment tool to check if they're posting negative reviews on Trustpilot or G2. This is a proactive retention feature."

---

**Q9: Walk me through what happens when an email with a legal threat arrives.**

> "First, the ingestion API receives it, deduplicates by message_id, and creates the records. In Layer 2, the heuristic filter scans the body for patterns like 'cease and desist', 'GDPR', or 'right to be forgotten'. If found, `is_legal = True` is flagged. In Layer 3, even if the LLM classifier returns a category like 'Inquiry', the job processor overrides it to 'Legal' because `triage.is_legal` is True, and sets `requires_human = True`, updating status to 'Escalated'. In Layer 4, the ReAct agent receives the context with a message like 'IMPORTANT: Auto-reply blocked: category is Legal. You MUST escalate to human or flag for legal. Do NOT draft a reply.' The agent then calls the flag_for_legal tool with a threat_summary, which creates an Action record and an AuditLog entry. The email appears in the inbox flagged as Legal and Escalated for a human to handle."

---

**Q10: What are some limitations or areas you'd improve?**

> "Several things. First, the web scraping of Trustpilot and G2 is largely blocked — those sites have strong bot protection and robots.txt restrictions. A real solution would use their official APIs or a third-party review aggregation service. Second, the 'send reply' functionality is simulated — in production you'd integrate with an actual email provider like SendGrid or Gmail API. Third, the background task uses FastAPI's in-process BackgroundTasks, which is fine for demo but not reliable in production — a task queue like Celery with Redis would be more resilient. Fourth, the LLM model is gemini-3.1-flash-lite which is the free tier — in production you'd want better rate limit handling and possibly fine-tuning on company-specific email patterns. Fifth, there's no authentication on the API — in production this would need proper auth like OAuth2 or API keys."

---

> [!TIP]
> Keep these answers conversational. Don't recite them verbatim — use them as a mental framework and speak naturally.

