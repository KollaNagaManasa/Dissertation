# RAG-Powered Assistant for Infrastructure as Code Generation

M.Tech dissertation prototype (BITS Pilani, SEZG628T) — a Retrieval-Augmented Generation
assistant that turns natural-language infrastructure requirements into validated Terraform
for **Google Cloud Platform**, grounded in provider documentation and best-practice templates.

## Cloud/tooling choices (locked in for this prototype)

| Concern              | Choice                                                                 |
|----------------------|-------------------------------------------------------------------------|
| Target IaC / cloud   | Terraform, `google` provider (GCP)                                     |
| Generation LLM       | Vertex AI Gemini (`gemini-2.0-flash` by default, configurable)         |
| Embeddings           | Vertex AI `text-embedding-005`                                         |
| Vector store         | `VertexVectorSearchStore` (Vertex AI Vector Search) in production; `InMemoryVectorStore` (numpy cosine) for local dev/tests |
| Document storage     | Google Cloud Storage bucket (`gs://<bucket>/knowledge_base/...`), with local filesystem fallback for dev |
| Validation           | `terraform validate` / `terraform plan` (via the `google` provider) + Open Policy Agent (`conftest`) policy checks |
| Baseline for comparison | Same LLM, no retrieval (`generation/baseline_generator.py`)         |

These map directly to the "settle the cloud provider, LLM, embedding model and vector store"
action item in the outline's supervisor remarks.

## Architecture

```
Natural-language request
        │
        ▼
  ingestion/  (load + chunk GCP/Terraform docs, from GCS or local ./data/knowledge_base)
        │  (offline, run via scripts/ingest.py)
        ▼
  embeddings/ (Vertex AI text-embedding-005, or local TF-IDF fallback for offline dev)
        │
        ▼
  vectorstore/ (Vertex AI Vector Search, or in-memory numpy store for dev)
        │
        ▼
  retrieval/  (top-k retriever over the vector store)
        │
        ▼
  generation/ (prompts.py grounds the LLM in retrieved chunks; rag_generator.py calls Gemini
               on Vertex AI; baseline_generator.py skips retrieval for the RAG-vs-no-RAG benchmark)
        │
        ▼
  validation/ (terraform_validator.py runs init/validate/plan; opa_validator.py runs conftest
               against data/policies/*.rego; report.py aggregates a pass/fail verdict)
```

Every external call (Vertex AI, GCS, `terraform`, `conftest`) sits behind a small interface in
`base.py` so the pipeline can run end-to-end locally (no GCP credentials, no terraform binary)
for development and unit testing, and swap in the real GCP-backed implementations for the actual
dissertation experiments.

## Project layout

```
src/ragiac/
  config.py              Settings (env-driven): GCP project/region, model names, bucket, paths
  ingestion/
    loader.py             Reads docs from GCS or local dir
    chunker.py             Recursive text chunking
  embeddings/
    base.py                Embedder interface
    vertex.py               Vertex AI text-embedding-005
    local_tfidf.py           Dependency-light offline fallback
  vectorstore/
    base.py                 VectorStore interface
    in_memory.py             numpy cosine-similarity store (dev/tests)
    vertex_vector_search.py   Vertex AI Vector Search (production)
  retrieval/
    retriever.py             top-k retrieval + context assembly
  generation/
    prompts.py                Grounded IaC-generation prompt template
    llm_vertex.py               Vertex AI Gemini wrapper
    rag_generator.py             Retrieval-grounded generation
    baseline_generator.py         Non-RAG baseline (direct LLM)
  validation/
    terraform_validator.py       terraform init/validate/plan wrapper
    opa_validator.py              conftest/OPA policy check wrapper
    report.py                      Aggregated ValidationReport
  pipeline.py                 Wires ingestion -> retrieval -> generation -> validation

scripts/
  ingest.py     Build/refresh the vector index from data/knowledge_base
  ask.py        CLI: natural-language prompt -> generated + validated Terraform
  benchmark.py  RAG vs. non-RAG baseline over data/eval/prompts.jsonl

data/
  knowledge_base/   Seed GCP/Terraform provider docs + best-practice snippets (sanitized, public)
  policies/          OPA/Rego policies generated Terraform must satisfy
  eval/              Benchmark prompt set + expected-resource checklists

tests/            Unit tests for chunker, in-memory vector store, prompts, and validation parsing
```

## Setup

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Local/offline mode (no GCP credentials needed): uses local_tfidf + in_memory store
copy .env.example .env

# Real GCP mode: set in .env
#   RAGIAC_MODE=gcp
#   GOOGLE_CLOUD_PROJECT=<your-project-id>
#   GOOGLE_CLOUD_REGION=us-central1
#   GCS_BUCKET=<your-bucket>
#   VERTEX_VECTOR_INDEX_ID=<your Vertex AI Vector Search index id>
#   VERTEX_VECTOR_ENDPOINT_ID=<your Vertex AI Vector Search endpoint id>
# and authenticate with: gcloud auth application-default login
```

Terraform validation additionally requires the `terraform` CLI and, for policy checks, `conftest`
(both on PATH) — install these separately; the validators raise a clear error naming the missing
binary rather than failing silently.

## Running

```bash
# 1. Build the vector index from data/knowledge_base
py scripts/ingest.py

# 2. Ask for infrastructure
py scripts/ask.py "A GCS bucket for storing invoice PDFs, versioned, with a 30 day lifecycle rule to move to Nearline"

# 3. Benchmark RAG vs. non-RAG baseline
py scripts/benchmark.py --prompts data/eval/prompts.jsonl
```

## Status

This is the Phase 3/4 scaffolding for the dissertation (RAG pipeline + knowledge base design,
prototype development) — see the outline's Plan of Work. Vertex AI Vector Search wiring and the
full OPA policy set are stubbed with clear TODOs pending GCP project provisioning.
