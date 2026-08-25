# Agentic CRM — Task & Feature Roadmap (TODO.md)

This document tracks planned features, ongoing enhancements, and architectural upgrades for the **Agentic CRM** system, benchmarked against enterprise CRM standards (Zendesk, Salesforce Service Cloud, Intercom, and HubSpot).

---

## 📌 Status Legend
- `[ ]` **Planned / Backlog**: Feature identified, awaiting implementation.
- `[/]` **In Progress**: Currently under active development.
- `[x]` **Completed**: Built, tested, and verified.

---

## 🚀 Layer 1: Ingestion Engine Improvements (Enterprise Standards)

- [ ] **1. Standard RFC Email Header Parsing & Threading**
  - [ ] Parse `In-Reply-To` and `References` RFC 5322 headers from raw email payloads.
  - [ ] Match incoming replies to existing threads using standard header message chains instead of requiring custom client-calculated `thread_id`.
  - [ ] Fallback fuzzy thread matching by normalized Subject line (stripping `Re:`, `Fwd:`, `[EXTERNAL]`).

- [ ] **2. Signature & Quoted Reply Stripper**
  - [ ] Integrate an email parsing engine (e.g. `talon` or `mailparser`) to strip email signatures, phone numbers, and legal disclaimers.
  - [ ] Strip historical quoted conversation blocks (`On <Date>, <User> wrote: ...`) before LLM ingestion to reduce token overhead by ~60% and prevent hallucination loops.

- [ ] **3. Multi-Modal Attachment & Document Processing Pipeline**
  - [ ] Extract email attachments (PDFs, error screenshots, log files, invoices).
  - [ ] Store attachments in cloud object storage (AWS S3 / GCP Cloud Storage) and generate time-limited signed URLs.
  - [ ] Run OCR / text extraction (e.g. `pdfplumber`, Tesseract, or Gemini Vision) to pass invoice numbers, error stack traces, and document text into LLM context.

- [ ] **4. Resilient Distributed Task Queue (Celery + Redis)**
  - [ ] Replace FastAPI in-memory `BackgroundTasks` with Celery / Redis (or RabbitMQ / AWS SQS).
  - [ ] Implement exponential backoff retries, rate limiting, and Dead-Letter Queues (DLQ) to ensure zero message loss during server crashes or restarts.

---

## 🛡️ Layer 2: Heuristic Pre-Filter Improvements (Enterprise Standards)

- [ ] **1. Auto-Responder & Out-of-Office (OOO) Loop Detection**
  - [ ] Detect `Auto-Submitted: auto-replied` / `X-Autoreply: yes` email headers and "Out of Office / Vacation Responder" subject patterns.
  - [ ] Automatically bypass LLM processing and mark as "Ignored" to prevent infinite automated email response loops.

- [ ] **2. Dynamic Database-Driven Rule Engine**
  - [ ] Replace hardcoded Python tuples (`SPAM_PATTERNS`, `LEGAL_PATTERNS`) with a `heuristic_rules` database table.
  - [ ] Build admin API/UI endpoints to add, edit, test, or toggle regex and keyword matching rules with zero downtime.

- [ ] **3. CRM Account-Tier & VIP Priority Routing**
  - [ ] Replace static domain checks (`enterprise.net`) with dynamic DB queries against `Contact.account_value`, SLA tier, and active deal status.
  - [ ] Automatically assign maximum priority (Score 5) and Fast-Track queueing to High-Value Enterprise accounts ($50k+ ARR).

- [ ] **4. PII & PCI Sensitive Data Redaction / Masking**
  - [ ] Implement Microsoft Presidio / regex scanners to detect Credit Card numbers (PCI-DSS), SSNs, bank details, and API secret keys.
  - [ ] Mask sensitive data (`[REDACTED_CC]`, `[REDACTED_PII]`) before logging or transmitting text to third-party LLM APIs.

- [ ] **5. Real-Time Spam, SPF/DKIM & Domain Reputation Verification**
  - [ ] Verify SPF, DKIM, and DMARC authentication headers to detect spoofed sender addresses.
  - [ ] Integrate DNS Blacklist (DNSBL / Spamhaus API) and verify domain age and MX records dynamically.

---

## 🧠 Layer 3: LLM Classification & Intelligence Engine (Enterprise Standards)

- [ ] **1. Multi-Lingual Detection & Auto-Translation Pipeline**
  - [ ] Detect incoming email language (e.g. `langdetect` / FastText).
  - [ ] Auto-translate non-English inquiries to English for internal processing, while prompting the agent to draft the final response in the customer's native language.

- [ ] **2. Hierarchical Taxonomy & Root Cause Classification**
  - [ ] Upgrade single-level categories to a 3-tier hierarchy: `L1 Category -> L2 Subcategory -> L3 Root Cause` (e.g. `Billing -> Refund Request -> Duplicate Transaction`).
  - [ ] Extract structured diagnostic fields (e.g. `Browser/OS`, `Affected Feature`, `Order ID`, `Monetary Impact`).

- [ ] **3. Dynamic Few-Shot Exemplar Injection**
  - [ ] Embed high-quality, human-resolved tickets in a dedicated vector index.
  - [ ] Dynamically retrieve top-2 matching historical resolutions and inject them as few-shot exemplars into Gemini's prompt for higher drafting accuracy.

- [ ] **4. Model Cascading & Cost-Aware Routing**
  - [ ] Route simple inquiries (e.g., FAQ lookups, password reset guides) to lightweight fast models (e.g., Gemini 2.0 Flash / Flash-Lite).
  - [ ] Escalate complex complaints, multi-issue emails, and legal negotiations to frontier reasoning models (e.g., Gemini 1.5 Pro / Claude 3.5 Sonnet).

- [ ] **5. Hallucination Detection & Citation Grounding Verification**
  - [ ] Implement a post-generation verification step checking that all factual claims and policy statements in the draft reply exist in the retrieved RAG context.
  - [ ] Flag ungrounded claims for human agent review.

- [ ] **6. Sentiment Velocity & Churn Risk Prediction**
  - [ ] Calculate the rate of sentiment decline across the last 3–5 interactions rather than evaluating emails in isolation.
  - [ ] Automatically calculate an updated churn risk score and trigger proactive customer success notifications when velocity is negative.

---

## 🤖 Layer 4: Autonomous ReAct Agent & Orchestration Engine (Enterprise Standards)

- [ ] **1. External Enterprise Action Tools**
  - [ ] **Stripe Tool**: Look up customer subscription status, verify charges, check invoice payment status, and initiate refunds.
  - [ ] **Jira / Linear Tool**: Auto-create engineering bug tickets with reproduction steps, system logs, and customer metadata extracted from emails.
  - [ ] **E-commerce / ERP Tool**: Query order fulfillment, shipping tracking numbers, and delivery ETAs via external APIs.
  - [ ] **Calendar Tool**: Check calendar availability and insert meeting booking links for high-value sales inquiries.

- [ ] **2. Human-in-the-Loop (HITL) Safety Gates & Policy Permissions**
  - [ ] Implement granular tool permission levels: `Read-Only` (safe to execute autonomously) vs. `Destructive / Financial` (requires human approval).
  - [ ] Require manager approval before executing high-impact actions (e.g., issuing refunds over $100, account cancellations, or data deletion).

- [ ] **3. Multi-Turn Session Persistence & State Machine (LangGraph)**
  - [ ] Migrate the ReAct loop to a durable state machine (LangGraph / Temporal) supporting checkpointing across multi-day email exchanges.
  - [ ] Resume agent reasoning seamlessly when a customer responds to a follow-up clarification email 48 hours later.

- [ ] **4. Adversarial Prompt Injection & Jailbreak Defense**
  - [ ] Deploy NeMo Guardrails / Llama Guard to detect and block indirect prompt injection attempts inside customer email bodies.
  - [ ] Enforce strict system prompt protection to prevent leaking internal instructions, API keys, or system credentials.

- [ ] **5. Dynamic Tool Selection & Token Budget Management**
  - [ ] Dynamically bind only relevant tools based on Layer 3 category to save prompt tokens and reduce agent confusion.
  - [ ] Enforce strict per-ticket token and cost budgets with automatic fallback to human triage if budget is reached.

---

## 📚 Layer 5: RAG & Knowledge Management System (Enterprise Standards)

- [ ] **1. Hybrid Search (Dense Embeddings + Sparse BM25 / Full-Text Search)**
  - [ ] Combine dense vector search (SentenceTransformers / Gemini Embeddings) with sparse lexical search (BM25 or PostgreSQL `tsvector`).
  - [ ] Use Reciprocal Rank Fusion (RRF) to accurately retrieve exact part numbers, error codes, and policy names alongside semantic matches.

- [ ] **2. Live Enterprise Knowledge Connectors**
  - [ ] Build automatic sync integrations with Notion, Confluence, Google Docs, and Zendesk Help Center.
  - [ ] Implement webhook listeners to re-index documents instantly whenever company documentation or pricing pages are updated.

- [ ] **3. Knowledge Gap Auto-Detection**
  - [ ] Log customer questions where RAG retrieval returned low similarity scores (< 0.60) or where the agent failed to answer.
  - [ ] Present a "Knowledge Base Gaps" report to support managers highlighting missing documentation.

- [ ] **4. Multi-Tenant Knowledge Partitioning & Metadata Filtering**
  - [ ] Filter KB document retrieval by customer plan tier (Free vs. Enterprise), product line, and geographical region (GDPR vs. US policies).

---

## 🗄️ Layer 6: Database, Scalability & Compliance Architecture (Enterprise Standards)

- [ ] **1. Multi-Tenant Architecture & Data Isolation**
  - [ ] Add `tenant_id` / `organization_id` to all tables with PostgreSQL Row-Level Security (RLS) for enterprise B2B SaaS readiness.
  - [ ] Support custom per-tenant LLM keys, SLA definitions, and knowledge bases.

- [ ] **2. Unified Vector Storage (`pgvector`)**
  - [ ] Migrate vector storage from ChromaDB to PostgreSQL `pgvector` with HNSW indexing.
  - [ ] Eliminate file-sync issues, enable transactional consistency between CRM records and embeddings, and simplify multi-instance deployment.

- [ ] **3. Distributed Caching & Rate Limiting (Redis)**
  - [ ] Cache contact profiles, customer ARR, and active company rules in Redis to minimize database read overhead.
  - [ ] Implement distributed rate limiters per IP / sender to protect against email flood attacks.

- [ ] **4. Enterprise Compliance & Retention Policies**
  - [ ] Immutable SOC-2 and HIPAA compliant audit logging for every AI decision and human edit.
  - [ ] GDPR "Right to be Forgotten" cascade deletion workflow for customer data across database records and vector embeddings.

---

## 💻 Layer 7: Agent Workspace & Human-in-the-Loop Frontend (Enterprise Standards)

- [ ] **1. Real-Time WebSockets & Live Streaming**
  - [ ] Stream LLM thought traces and draft generation in real-time to the agent dashboard via FastAPI WebSockets.
  - [ ] Live inbox updates without manual page refreshes when new emails arrive.

- [ ] **2. Agent Collision Detection & Live Presence**
  - [ ] Display visual indicators when another human agent is currently viewing or drafting a reply on the same thread to prevent duplicate replies.

- [ ] **3. AI Co-Pilot Draft Editor**
  - [ ] Inline AI completions, one-click tone adjustments (e.g., "Make more empathetic", "Make concise", "Formal"), and macro/snippet insertion.
  - [ ] Diff view highlighting human edits versus the AI's original proposed draft.

- [ ] **4. SLA Countdown Timers & Escalation Banners**
  - [ ] Real-time visual countdown timers for First Response Time (FRT) and Resolution SLA targets.
  - [ ] Visual alert badges for impending SLA breaches based on customer tier.

- [ ] **5. Interactive One-Click Action Cards**
  - [ ] Embedded UI cards in the Thread Workspace to approve refunds, create Jira tickets, or confirm legal escalation with one click.

---

## 🌐 Layer 8: Integrations & Live Communications Hub

- [ ] **1. Full Two-Way Gmail Sync (Google Cloud Pub/Sub + OAuth2)**
  - [ ] Set up GCP project with Gmail API & Pub/Sub push notifications.
  - [ ] Implement `users.watch()` background job/cron to renew push subscription.
  - [ ] Create `/api/webhooks/gmail` FastAPI endpoint to receive real-time push events and fetch message bodies via Gmail API.
  - [ ] Send replies directly through the user's Gmail account via OAuth2 user credentials.

- [ ] **2. Transactional Email Dispatcher (SendGrid / Mailgun / AWS SES)**
  - [ ] Replace simulated replies with live outbound email dispatch using SendGrid/Mailgun with DKIM/SPF signing.
  - [ ] Inbound webhook parser for SendGrid / Mailgun / Postmark incoming events.

- [ ] **3. Internal Collaboration Bots (Slack & Microsoft Teams)**
  - [ ] Send instant webhook notifications to dedicated Slack/Teams channels on `Critical` urgency or `Legal` escalation.
  - [ ] Allow human agents to approve or modify AI drafts directly from Slack interactive buttons.

---

## 📊 Layer 9: LLMOps, Observability & Evaluations (Enterprise Standards)

- [ ] **1. End-to-End LLM Tracing (Langfuse / Arize Phoenix / OpenTelemetry)**
  - [ ] Trace every LLM call, token consumption, latency breakdown, tool invocation, and cost per email.
  - [ ] Tag traces with `email_id`, `contact_id`, and `agent_id` for granular debugging.

- [ ] **2. CI/CD Automated Evaluation Suite (Golden Benchmark Dataset)**
  - [ ] Maintain a curated benchmark dataset of 150+ edge-case emails (adversarial prompts, legal threats, billing disputes, multi-intent).
  - [ ] Run automated regression evals in GitHub Actions on prompt or model changes to ensure accuracy >= 95% before deployment.

- [ ] **3. Continuous Learning & RLHF Feedback Loop**
  - [ ] Track human agent acceptance rate, rejection rate, and diffs on AI drafts.
  - [ ] Use edited drafts as few-shot training examples to continuously refine system prompts.

---

## ✅ Completed System Capabilities

- [x] **Layer 1**: Ingestion API with message deduplication, HTML entity cleaning, and Contact/Thread record association.
- [x] **Layer 2**: Heuristic Pre-Filter with keyword pattern scanning (Spam, Security, Legal) and blocklist domain detection.
- [x] **Layer 3**: Google Gemini LLM Classification Engine with Pydantic schema validation (Category, Sentiment, Urgency, Confidence, Entities).
- [x] **Layer 4**: Autonomous ReAct Agent with 7 tools (`get_thread_history`, `search_knowledge_base`, `draft_reply`, `escalate_to_human`, `flag_for_legal`, `create_internal_ticket`, `scrape_public_sentiment`) and `MAX_STEPS = 6` guardrails.
- [x] **RAG Engine**: Knowledge base with Markdown chunking, SentenceTransformers embeddings (`all-MiniLM-L6-v2`), and ChromaDB vector persistence.
- [x] **Database**: 10 PostgreSQL SQLAlchemy models with Alembic schema migrations and JSONB reasoning logs.
- [x] **Frontend**: React + Vite + TailwindCSS dashboard (Inbox with multi-filter, Thread Workspace with full reasoning trace, and Analytics charts).

