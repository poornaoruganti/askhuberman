# Ask Huberman 🧠

**Turn 450+ long-form podcast episodes into a searchable, citable knowledge base.**

Ask Huberman is a production RAG platform that ingests every episode of a long-form podcast (60,000+ minutes of transcript), indexes it at the sub-chapter level, and answers natural-language questions with **timestamp-accurate, clickable citations** straight to the moment in the video where the claim was made — not just a link to a 2-hour video and good luck.

```
"What does he say about cold exposure and dopamine?"
        │
        ▼
┌───────────────────┐        streamed answer, token by token
│   Ask Huberman UI  │ ◀───────────────────────────────────────┐
└─────────┬──────────┘                                          │
          │ POST /api/v1/chat (SSE)                              │
          ▼                                                      │
┌───────────────────┐   retrieve → rerank → generate      ┌──────┴──────┐
│   FastAPI backend   │ ─────────────────────────────────▶ │ Gemini 2.5  │
│  (rate-limited)     │                                     │   Flash     │
└─────────┬───────────┘                                     └─────────────┘
          │ vector search + metadata filter
          ▼
┌───────────────────┐
│  Pinecone index     │  ← embeddings written here by the ingestion pipeline
└─────────────────────┘
```

---

## Why this exists

Podcast/video knowledge is trapped in a linear format. Ask Huberman rebuilds it as a queryable knowledge base: ask a question in plain English, get an answer synthesized from the actual transcripts, with every claim traceable to `youtube.com/watch?v=...&t=<seconds>`.

---

## What's actually in this repo

This is a monorepo with two independent systems that share one Pinecone index:

| Directory | What it is | Runtime |
|---|---|---|
| [`data-ingestion-pipeline/`](data-ingestion-pipeline) | Event-driven pipeline that turns a new YouTube video into searchable vectors | Azure Functions (Durable Functions orchestration) |
| [`rag/`](rag) | Standalone, provider-agnostic RAG library — retrieval, reranking, generation, prompts | Python package, imported by the API |
| [`api/`](api) | Chat API that streams grounded, cited answers over SSE | FastAPI + Gunicorn/Uvicorn |
| [`web/`](web) | Chat UI | Next.js 16 / React 19 |

---

## 1. Data Ingestion Pipeline — zero-touch, event-driven

**No cron jobs polling YouTube.** A new upload triggers the entire pipeline automatically within seconds via **WebSub (PubSubHubbub) push notifications**.

```
YouTube channel publishes a video
          │
          ▼
 WebSub push ──▶ youtube_webhook (HTTP trigger, HMAC-verified)
          │
          ▼
   Azure Service Bus queue  (dedupe on video_id, retry w/ backoff)
          │
          ▼
 Durable Functions Orchestrator ── fully resumable, checkpointed at every step
          │
   ┌──────┴──────────────────────────────────────────────────────────────┐
   │ 1. fetch_transcript_to_blob   — pull transcript + YouTube metadata    │
   │ 2. chunk_transcript_to_blob   — chapter-aware, token-aware chunking   │
   │ 3. generate_approval_token + send_approval_email  ── HUMAN GATE       │
   │      ⏸  waits for external approve/reject event (24h timeout)        │
   │ 4. embed_chunks_to_blob       — Gemini embeddings (3072-dim)          │
   │ 5. upsert_embeddings_to_pinecone                                     │
   │ 6. send_notification_email    — success/failure summary              │
   └────────────────────────────────────────────────────────────────────┘
          │
          ▼
   Every step's state persisted to Azure Table Storage
   (pipeline_status, transcript_status, chunk_status, approval_status,
    embedding_status, upsert_status — independently queryable/resumable)
```

**Notable engineering details:**
- **Human-in-the-loop safety gate** — before anything gets embedded and made publicly queryable, a reviewer gets an email with a signed, hashed approval token and 24-hour expiry window. Reject it, and the video never enters the index.
- **Chapter-aware chunking** ([`custom_chunkking.py`](data-ingestion-pipeline/src/shared/custom_chunkking.py)) — parses YouTube description timestamps into chapters, groups transcript lines by chapter, and for any chapter too large for the embedding model, recursively splits it into token-bounded, sentence-aligned windows with forward overlap — so no chunk ever straddles a topic boundary or gets cut mid-sentence.
- **A resubscribe timer** renews the WebSub subscription every 24 hours (subscriptions expire), so ingestion keeps running with zero manual intervention indefinitely.
- **Idempotent by design** — Service Bus dedupe on `video_id`, `tenacity`-backed retries with exponential backoff on every external call.

---

## 2. The RAG Stack — `rag/`

A clean, interface-driven retrieval package (`retrievers/`, `rerankers/`, `generators/`, `embeddings/`, `query_rewriters/`, `injection_detection/` — each behind an ABC so any provider can be swapped in). Currently wired in production:

```
query
  │
  ▼
Pinecone dense retrieval (top_k, metadata filters, namespace-scoped)
  │
  ▼
Cohere rerank-v3 (cross-encoder reranking, fails open to raw retrieval order if Cohere errors)
  │
  ▼
Gemini 2.5 Flash generation — strictly grounded, YAML-driven system prompt:
  • must cite every factual claim with the source document ID
  • must say "I don't have enough information" rather than hallucinate
  • must surface contradictions between sources instead of picking one
  │
  ▼
async token stream ──▶ SSE
```

`query_rewriters/` and `injection_detection/` ship as ready-to-wire interfaces — the pipeline (`RAGPipeline.run_stream`) already has the extension points (`detect → rewrite → search → rerank → generate`), so plugging in a rewriter or a prompt-injection guard is a one-line change in [`api/dependencies.py`](api/dependencies.py), no pipeline surgery required.

Every citation returned to the client carries the exact chapter title and a `timestamp_url` pointing at the second the claim was made — this is threaded through from chunk metadata at ingestion time, all the way to the "Sources" panel in the UI.

---

## 3. API — `api/`

FastAPI service, one real endpoint that matters:

```
POST /api/v1/chat
```

- **Streams via Server-Sent Events** — `citation` events (sources found) fire before generation starts, then `content` events stream the answer token-by-token, so the UI shows sources instantly and the answer fills in live instead of a multi-second blank-screen wait.
- **Rate limited with Redis** (`fastapi-limiter`) — 10 requests/minute and 100/day per client, enforced at the dependency level.
- Containerized as a multi-stage Docker build (builder → slim runtime, non-root user, Gunicorn + Uvicorn workers).

## 4. Web — `web/`

Next.js 16 / React 19 chat interface.
- `useChatStream` hook reads the raw `ReadableStream`, incrementally parses SSE frames, and updates the last message in place — so the UI mutates in O(1) per chunk instead of re-rendering the whole thread.
- Citations render as a "Sources" grid under each answer, linking straight to the cited timestamp.
- `AbortController`-based stop generation.

---

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS 4, `react-markdown` |
| API | FastAPI, Uvicorn/Gunicorn, `fastapi-limiter` + Redis |
| RAG | Google Gemini 2.5 Flash (generation), Gemini `embedding-001` (3072-dim embeddings), Cohere `rerank-english-v3.0`, Jinja2-templated YAML prompts |
| Vector store | Pinecone (serverless) |
| Ingestion orchestration | Azure Durable Functions, Azure Service Bus, Azure Blob Storage, Azure Table Storage, Azure Communication Services (email) |
| Infra | Docker (multi-stage builds), deployed on Azure |

---

## Repo layout

```
askhuberman/
├── api/                        # FastAPI chat service
│   ├── routes/chat.py          # SSE /api/v1/chat endpoint
│   ├── dependencies.py         # wires the RAG pipeline (DI/singleton factory)
│   └── server.py                # app factory, CORS, Redis-backed rate limiter
├── rag/                        # provider-agnostic RAG library
│   ├── retrievers/pinecone.py
│   ├── rerankers/cohere.py
│   ├── generators/gemini.py
│   ├── embeddings/gemini.py
│   ├── query_rewriters/base.py  # pluggable, not yet wired
│   ├── injection_detection/base.py # pluggable, not yet wired
│   ├── prompts/templates/qa.yaml
│   └── pipelines/rag_pipeline.py
├── data-ingestion-pipeline/     # Azure Durable Functions app
│   ├── src/triggers/            # youtube_webhook, approval_webhook, resubscribe_timer
│   ├── src/orchestrators/       # ingest_orchestrator.py (the durable state machine)
│   ├── src/activities/          # one file per orchestrator step
│   └── src/shared/               # chunking, embeddings, blob/table/service-bus helpers
└── web/                         # Next.js chat UI
    └── src/{app,components,hooks,lib}
```

---

## Running it locally

### 1. RAG API (`api/` + `rag/`)

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create `.env` files for `rag/` and `api/` (see settings classes for required keys):

- `rag/.env` → `GEMINI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `NAMESPACE`, `COHERE_API_KEY`
- `api/.env` → `REDIS_URL`

```bash
uvicorn api.server:app --reload --port 8000
```

### 2. Web UI (`web/`)

```bash
cd web
npm install
npm run dev
```

Update the `apiEndpoint` in [`src/app/page.tsx`](web/src/app/page.tsx) to point at your local API (`http://localhost:8000/api/v1/chat`).

### 3. Ingestion pipeline (`data-ingestion-pipeline/`)

Requires the [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local) and a `local.settings.json` with (see [`src/shared/settings.py`](data-ingestion-pipeline/src/shared/settings.py) for the full list):

`SERVICE_BUS_FQDN`, `YOUTUBE_API`, `WEBSUB_SECRET`, `BLOB_ACCOUNT_URL`, `TABLE_ACCOUNT_URL`, `GEMINI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `COMMUNICATION_SERVICES_ENDPOINT`, `SENDER_EMAIL_ADDRESS`, `APPROVER_EMAIL_ADDRESS`, `APPROVAL_SECRET_KEY`, `HOST_URL`

```bash
cd data-ingestion-pipeline
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
func start
```

---

## License

MIT — see [LICENSE](LICENSE).
