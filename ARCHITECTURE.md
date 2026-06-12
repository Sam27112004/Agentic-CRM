# Agentic CRM Architecture & Data Model

## Architecture Diagram

```mermaid
flowchart TD
    subgraph Frontend [Dashboard UI (React / Vite)]
        Inbox[Mission Control Inbox]
        Thread[Thread Workspace]
        Analytics[Analytics Dashboard]
    end

    subgraph API [FastAPI Backend]
        Ingest[Ingestion Pipeline]
        JobProc[Job Processor]
        Endpoints[REST Endpoints]
    end

    subgraph Intelligence [Multi-Layer Intelligence Engine]
        Heuristics[Layer 1: Heuristic Filter]
        LLMClass[Layer 2: LLM Classifier]
        RAG[Layer 3: RAG Knowledge]
        Agent[Layer 4: Autonomous Triage Agent]
        WebIntel[Layer 5: Web Intelligence Scraper]
    end

    subgraph Data [Data & Storage]
        Postgres[(PostgreSQL)]
        ChromaDB[(ChromaDB Vector Store)]
    end

    %% Flow
    Frontend <--> |HTTP/REST| API
    Ingest --> |Queue| JobProc
    JobProc --> Heuristics
    JobProc --> LLMClass
    LLMClass <--> RAG
    JobProc --> Agent
    Agent <--> RAG
    Agent <--> WebIntel
    
    API <--> Postgres
    RAG <--> ChromaDB
```

## Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    CONTACT {
        int id PK
        string email UK
        string name
        string company
        string status
        numeric account_value
        numeric churn_risk_score
        datetime created_at
        datetime last_contact_at
    }

    THREAD {
        int id PK
        string thread_id UK
        string subject
        string sender_email FK
        datetime first_seen_at
        datetime last_updated_at
        string status
        string assigned_to
    }

    EMAIL {
        int id PK
        int thread_id FK
        string message_id UK
        string sender
        string subject
        text body
        datetime timestamp
        numeric sentiment_score
        string category
        string urgency
        boolean requires_human
        numeric confidence
        jsonb raw_entities
        string status
    }

    ACTION {
        int id PK
        int email_id FK
        jsonb agent_reasoning_log
        string action_type
        text proposed_content
        boolean is_approved
        string approved_by
        datetime executed_at
    }

    DRAFT {
        int id PK
        int email_id FK
        text content
        string status
        datetime created_at
        datetime updated_at
    }

    AUDIT_LOG {
        int id PK
        string entity_type
        int entity_id
        string action
        string performed_by
        datetime timestamp
        jsonb diff
    }

    PROCESSING_JOB {
        int id PK
        int email_id FK
        string status
        string error_message
        datetime created_at
        datetime completed_at
    }

    WEB_INTELLIGENCE_CACHE {
        int id PK
        string source_url
        string target_entity
        jsonb scraped_data
        datetime scraped_at
        datetime expires_at
    }

    %% Relationships
    CONTACT ||--o{ THREAD : "has"
    THREAD ||--o{ EMAIL : "contains"
    EMAIL ||--o{ ACTION : "generates"
    EMAIL ||--o{ DRAFT : "has"
    EMAIL ||--o{ PROCESSING_JOB : "processed_by"
```
