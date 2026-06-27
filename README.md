# TechAssist AI — Multi-Tenant RAG Knowledge Assistant

> **Empowering non-technical teams to answer complex technical questions with AI-grounded confidence.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-FF6600)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 The Problem

Non-technical Business Development representatives regularly meet clients who ask detailed technical questions — *How does the product work? What's included in the scope? How long will a feature take? Why is something not possible?*

Without a technical person in the room, these questions either go **unanswered** or get answered **incorrectly**. Both hurt the client relationship.

## 💡 The Solution

**TechAssist AI** is a production-grade, multi-tenant SaaS Knowledge Assistant that allows organizations to upload their internal documentation (product specs, APIs, project scope, FAQs) and instantly query them using **Retrieval-Augmented Generation (RAG)**.

The system retrieves relevant information, generates accurate client-friendly responses, and **avoids hallucinations** through a three-tier confidence scoring engine:

| Confidence | Score | Behavior |
|:---|:---:|:---|
| 🟢 **HIGH** | ≥ 80% | Delivers grounded answer rewritten in client-friendly tone |
| 🟡 **MEDIUM** | 50–79% | Provides partial answer + professional bridge script for follow-up |
| 🔴 **LOW** | < 50% | Flags as knowledge gap — generates a polished deferral script instead of guessing |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                      │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │  BD Rep Chat  │  │  Admin Dashboard  │  │  Super Admin    │  │
│  └──────┬───────┘  └────────┬─────────┘  └────────┬──────────┘  │
└─────────┼──────────────────┼──────────────────────┼─────────────┘
          │                  │                      │
          ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Application Gateway)              │
│  ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌───────────────┐    │
│  │ JWT Auth│  │ Rate Limit│  │ Audit Log│  │ Gap Resolution│    │
│  └────┬────┘  └─────┬─────┘  └────┬─────┘  └──────┬────────┘    │
└───────┼─────────────┼─────────────┼───────────────┼────────────-┘
        │             │             │               │
   ┌────▼────┐   ┌────▼────┐   ┌───▼───┐    ┌──────▼──────┐
   │ SQLite/ │   │ChromaDB │   │ Groq  │    │  Embedding  │
   │ Postgres│   │(per-    │   │ LLM   │    │  Engine     │
   │         │   │ tenant) │   │       │    │             │
   └─────────┘   └─────────┘   └───────┘    └─────────────┘
```

### Query Lifecycle: Input → Response

```
  BD Rep types question
         │
         ▼
  ┌──────────────┐
  │ JWT Validate │──→ Rate Limit Check (30 req/min)
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  Embed Query │──→ Search tenant's ChromaDB collection
  └──────┬───────┘
         ▼
  ┌──────────────┐     ┌─────────────────────────────────┐
  │  Confidence  │────→│ HIGH: Grounded Answer + Tone    │
  │   Scoring    │     │ MEDIUM: Answer + Bridge Script  │
  │  (top-3 avg) │     │ LOW: Knowledge Gap → Admin Flag │
  └──────┬───────┘     └─────────────────────────────────┘
         ▼
  ┌──────────────┐
  │ Audit Log +  │──→ Response streamed via SSE
  │ DB Persist   │
  └──────────────┘
```

---

## 🚀 Development Roadmap

### Version 1 — Basic RAG Assistant ✅
> Authentication, document upload, and intelligent Q&A

- [x] JWT-based login with role separation (BD Rep / Admin)
- [x] Document ingestion pipeline (PDF, DOCX, MD, TXT)
- [x] Recursive chunking with `chunk_size=512` and `overlap=50`
- [x] Embedding via Ollama (`nomic-embed-text`) with sentence-transformers fallback
- [x] ChromaDB vector storage and semantic retrieval
- [x] Groq LLM (Llama 3.3 70B) for grounded answer generation
- [x] Three-tier confidence scoring (HIGH / MEDIUM / LOW)
- [x] Tone rewriting for client-friendly responses
- [x] Bridge response generation for low-confidence queries
- [x] Real-time chat UI with SSE streaming

### Version 2 — Multi-Tenant & Role-Based Access ✅
> Tenant isolation and organizational hierarchy

- [x] Multi-tenant architecture with `tenant_id` scoping on all data
- [x] Tenant-isolated ChromaDB collections (`kb_{tenant_id}`)
- [x] Super Admin panel for tenant & user management
- [x] Role-based access control (Super Admin → Admin → BD Rep)
- [x] Admin dashboard with analytics and query monitoring
- [x] User feedback system (thumbs up/down ratings)

### Version 3 — Production-Ready Features ✅
> Enterprise hardening, compliance, and knowledge management

- [x] Dynamic Knowledge Gap Resolution (admin resolves → auto re-embeds)
- [x] Compliance audit logging (logins, uploads, deletions, queries)
- [x] PDF chat export for meeting records
- [x] Document versioning and management
- [x] Rate limiting via `slowapi` (prevents LLM quota exhaustion)
- [x] Batch embedding optimization (concurrent threads, batch encoding)
- [x] Docker-ready deployment configuration
- [x] PostgreSQL support for production environments

---

## 🔑 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Configure Environment
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=your_jwt_secret_key
```

### 2. Start Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

On first start, the backend will:
- Initialize SQLite database with auto-schema migration
- Create demo tenant and users
- Auto-ingest CloudNexus knowledge base documents

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App
Navigate to `http://localhost:5173`

---

## 🔐 Demo Credentials

| Account | Email | Password | Role |
|:---|:---|:---|:---|
| BD Rep | `demo@cloudnexus.com` | `demo123` | Chat with clients, rate answers |
| Admin | `admin@cloudnexus.com` | `admin123` | Upload docs, resolve gaps, analytics |

---

## 📋 Demo Script

### 🟢 HIGH Confidence (Score ≥ 80%)
Strong, grounded answers with source citations:
1. *"How does authentication work in CloudNexus?"*
2. *"Is CloudNexus GDPR compliant?"*
3. *"What's the pricing for the Professional plan?"*
4. *"Do you support Salesforce integration?"*
5. *"How does auto-scaling work?"*

### 🟡 MEDIUM Confidence (Score 50–79%)
Partial answers with professional follow-up bridge scripts:
1. *"Can we integrate with HubSpot?"*
2. *"What's your AI monitoring feature?"*
3. *"Do you have a mobile app?"*

### 🔴 LOW Confidence (< 50%) — Bridge Response
Graceful deferral — never guesses, preserves client trust:
1. *"What's your quantum computing strategy?"*
2. *"Do you support blockchain integration?"*
3. *"What's your carbon neutrality plan?"*

### 🔧 Knowledge Gap Resolution (Admin)
1. Ask a LOW confidence question as BD Rep
2. Switch to Admin account → see flagged query in dashboard
3. Click "Resolve" → input the correct answer
4. Ask the same question again → now returns HIGH confidence ✅

---

## 📁 Project Structure

```
RAG_PROJECT/
├── backend/
│   ├── main.py               # FastAPI application entry point
│   ├── config.py              # Environment & settings management
│   ├── logging_config.py      # Structured audit logging
│   ├── auth/                  # JWT authentication & middleware
│   ├── ingestion/             # Document parsing, chunking, embedding
│   ├── query/                 # RAG pipeline (retrieve → score → generate)
│   ├── admin/                 # Admin API routes & gap resolution
│   ├── export/                # PDF chat export engine
│   ├── database/              # ORM models & session management
│   ├── knowledge_base/        # Pre-loaded demo documents
│   └── requirements.txt       # Python dependencies
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Auth/          # Login & registration
│       │   ├── Chat/          # BD Rep chat interface
│       │   ├── Admin/         # Admin dashboard & analytics
│       │   ├── SuperAdmin/    # Tenant management panel
│       │   ├── Layout/        # App shell & navigation
│       │   └── common/        # Shared UI components
│       ├── context/           # React auth context
│       └── api/               # Axios API client
├── .env                       # Environment configuration
└── technical_proposal.md      # System design document
```

---

## 🔧 Tech Stack

| Layer | Technology | Purpose |
|:---|:---|:---|
| **LLM** | Groq (Llama 3.3 70B) | Fast inference for answer generation & tone rewriting |
| **Vector DB** | ChromaDB | Tenant-isolated semantic search index |
| **Embeddings** | Ollama / sentence-transformers | Document & query vectorization |
| **Backend** | FastAPI + Uvicorn | Async API with Pydantic v2 validation |
| **Database** | SQLAlchemy (SQLite / PostgreSQL) | Relational data with tenant scoping |
| **Frontend** | React 18 + Vite | Responsive dark-theme dashboard |
| **Auth** | JWT (python-jose) | Stateless token-based authentication |
| **Rate Limiting** | slowapi | Per-IP request throttling |
| **PDF Export** | ReportLab | Compliance-ready chat transcripts |
| **Chunking** | LangChain TextSplitters | Recursive character splitting with overlap |

**Total infrastructure cost: $0** (all free-tier services)

---

## 🐳 Docker Deployment

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment: [POSTGRES_DB=techassist]
  chromadb:
    image: chromadb/chroma:latest
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [db, chromadb]
  frontend:
    build: ./frontend
    ports: ["80:80"]
```

```bash
docker-compose up -d
```

---

## 🧠 Key Design Decisions

| Decision | Rationale |
|:---|:---|
| **Confidence scoring over blind generation** | Prevents hallucination — the #1 risk in client-facing AI |
| **Tenant-isolated ChromaDB collections** | Mathematical guarantee against cross-tenant data leakage |
| **Tone rewriting as a separate LLM pass** | Keeps grounding logic pure while making output business-friendly |
| **Bridge scripts instead of "I don't know"** | BD reps maintain professionalism even on unanswerable questions |
| **Admin gap resolution with auto re-embedding** | Knowledge base improves continuously without developer intervention |

---

## 📄 License

This project is built for educational and portfolio purposes.

---

<p align="center">
  Built with ❤️ using FastAPI, React, ChromaDB, and Groq
</p>
