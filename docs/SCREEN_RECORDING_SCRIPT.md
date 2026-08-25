# Agentic CRM — Screen Recording Walkthrough Script

**Target Length:** 5–10 minutes
**Tools Needed:** Screen recorder (OBS, Loom, QuickTime), microphone, Agentic CRM running locally (`backend` and `frontend` servers on).

## Preparation (Before Recording)
1. Ensure the PostgreSQL database is completely fresh and seeded only with contacts:
   ```bash
   python -m backend.services.reset_inbox
   python -m backend.services.seed_contacts
   ```
2. Verify the RAG database is seeded:
   ```bash
   python -m backend.services.rag --seed
   ```
3. Have 3 terminal windows ready:
   - Terminal 1: Backend `uvicorn backend.main:app --reload --port 8000`
   - Terminal 2: Frontend `npm run dev`
   - Terminal 3: Simulator ready to run `python -m backend.services.simulator --speed 0.25`
4. Open your browser to `http://localhost:5174` (or `5173`) to the **Mission Control Inbox**.

---

## 1. Introduction (0:00 - 1:00)
- **Visual:** Show the empty Mission Control Inbox.
- **Action:** Briefly explain the project: "This is Agentic CRM, an AI-powered CRM that autonomously monitors an inbox, triages emails, executes agentic reasoning using ReAct loops, and drafts replies grounded in our internal policies."
- **Action:** Run the simulator in Terminal 3.
  ```bash
  python -m backend.services.simulator --speed 0.25
  ```
- **Visual:** Switch back to the Inbox. Show the emails streaming in live. Point out the real-time "Stats Bar" at the top updating, and the badges (Urgency, Category, Sentiment) appearing.

## 2. Agent Reasoning & Legal Escalation — Bob Outage (1:00 - 3:00)
- **Visual:** Find the email from `bob.jones@enterprise.net` with the subject "Escalation: SLA Breach + Legal Review". Click on it to open the Thread Workspace.
- **Narrative:** "Let's look at a complex escalation. Bob is threatening legal action over an SLA breach."
- **Action:** Point to the **Contact Profile** card on the right. Mention he is an Enterprise client with an $84,000 account value.
- **Action:** Expand the **Agent Reasoning Trace**. Walk through the steps the agent took:
  1. *Thought:* Check thread history.
  2. *Thought:* Check account status.
  3. *Action:* `flag_for_legal` because of the legal threat.
  4. *Action:* `search_knowledge_base` to retrieve the SLA policy.
  5. *Action:* `escalate_to_human` since the system is forbidden from auto-replying to legal threats.
- **Highlight:** Show that the agent successfully identified the legal threat, retrieved the correct policy, and held back an auto-reply.

## 3. RAG Retrieval Debug View (3:00 - 4:00)
- **Visual:** Stay in Bob's Thread Workspace, scroll down to the **RAG Context Panel** (or use the Swagger UI /docs to test the RAG endpoint directly).
- **Narrative:** "The agent's decisions are grounded in our internal markdown policies, not hallucinated LLM knowledge."
- **Action:** Open the RAG Context Panel and show the exact chunk retrieved from `sla_policy.md` regarding the "10% monthly credit" for P0 incidents. 
- **Alternative Action:** If you prefer, switch to the Swagger UI (`http://localhost:8000/docs`), execute `GET /rag/search` with "SLA breach credit obligation", and show the vector search results returning the exact markdown chunks and cosine similarity scores.

## 4. Web Intelligence Module — Karen Churn Scenario (4:00 - 6:00)
- **Visual:** Go back to the Inbox and find the thread from `karen.w@retail-co.com` (subject related to multiple unresolved issues or public reviews). Open her Thread Workspace.
- **Narrative:** "The agent isn't limited to internal data. It can scrape the web to assess public reputation damage."
- **Action:** Point out Karen's deteriorating sentiment score in the timeline.
- **Action:** Expand the **Web Intelligence / Reasoning panel**. Show where the agent noticed her threat to post publicly, and triggered the `scrape_public_sentiment` tool (or web scraper).
- **Action:** Highlight the result where the agent injected external Trustpilot/G2 review sentiment into its context to realize the high risk of churn, deciding to apply a retention offer based on `refund_policy.md`.

## 5. Analytics Dashboard (6:00 - 8:00)
- **Visual:** Click "Analytics" in the top navigation.
- **Narrative:** "All of this raw text and sentiment data is aggregated into structured business intelligence."
- **Action:** Show the **Sentiment Trend Line Chart**. Point out how it tracks the moving average of sentiment across all senders.
- **Action:** Show the **Category Distribution**. Highlight how the system autonomously tagged Complaints, Bugs, and Inquiries.
- **Action:** Highlight the **At-Risk Accounts** panel, showing users whose sentiment has dropped consecutively, giving human agents a prioritized hitlist to prevent churn.

## 6. Architecture & Conclusion (8:00 - 9:00)
- **Visual:** Open the `architecture.png` (or `er_diagram.mmd` rendered) to show the flow.
- **Narrative:** Briefly wrap up by pointing out the multi-layer pipeline: "Raw emails hit a heuristic pre-filter (FastAPI), then an LLM classifier, and finally the ReAct agent which interacts with ChromaDB for RAG and PostgreSQL for state, all orchestrating asynchronously without Celery."
- **Call to Action:** "Check out the repo for the full schema and code!"
