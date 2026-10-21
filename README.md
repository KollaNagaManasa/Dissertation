# RAG-Powered Assistant for Infrastructure as Code Generation

M.Tech dissertation prototype (BITS Pilani, SEZG628T) — a Retrieval-Augmented Generation
assistant that turns natural-language infrastructure requirements into validated Terraform
for **Google Cloud Platform**, grounded in provider documentation and best-practice templates.

## Cloud/tooling choices (locked in for this prototype)

| Concern              | Choice                                                                 |
|----------------------|-------------------------------------------------------------------------|
| Target IaC / cloud   | Terraform, `google` provider (GCP)                                     |
| Generation LLM       | Vertex AI Gemini `gemini-3.8-flash` (configurable; `2.0-flash` no longer exists, `2.5-flash` shuts down 2026-10-20) |
| Embeddings           | Vertex AI `text-embedding-005` (RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY task types) |
| Vector store         | `InMemoryVectorStore` (exact cosine search over ~1k chunks, persisted to `data/index/`). `VertexVectorSearchStore` is implemented but not provisioned — see "Vector store decision" below |
| Knowledge base       | Public `google` provider docs (`terraform-provider-google` v8.3.0, MPL-2.0) + hand-written org conventions; no customer or production configuration |
| Validation           | `terraform init/validate/plan` (google provider v8.x) + Open Policy Agent (`conftest`) policies + per-task functional-intent checks |
| Baseline for comparison | Same LLM and same target-provider instruction, no retrieval (`generation/baseline_generator.py`) |

These map directly to the "settle the cloud provider, LLM, embedding model and vector store"
action item in the outline's supervisor remarks.

### Vector store decision

The corpus is ~1,000 chunks (~1 MB of docs), so exact in-memory cosine search is instantaneous and
needs no infrastructure. Vertex AI Vector Search is approximate-nearest-neighbour infrastructure
designed for millions of vectors and bills while an index endpoint is deployed — cost and
operational overhead with no retrieval-quality benefit at this scale. The vector store sits behind
a small interface (`vectorstore/base.py`), and `VertexVectorSearchStore` is written so switching is
a configuration change (`VERTEX_VECTOR_INDEX_ID` / `VERTEX_VECTOR_ENDPOINT_ID`) if the knowledge base
grows. State this decision, with this reasoning, in the Mid-Semester Report.

## Region choice: asia-south1 (Mumbai)

Google Cloud has no region in Hyderabad itself. Of its two live India regions, `asia-south1`
(Mumbai) is ~600km from Hyderabad versus ~1,350km for `asia-south2` (Delhi NCR) — meaningfully
lower latency. Asia regions generally carry a premium over the `us-central1` baseline (roughly
15% per a third-party price comparison); no cost reason to prefer Delhi over Mumbai was found, but
the two regions' exact pricing was not compared line by line, so check the price list before
relying on this. `asia-south1` is used as `GOOGLE_CLOUD_REGION` for storage (GCS),
embeddings, and the Vertex AI Vector Search index — and is the default region baked into the
knowledge-base examples (`data/knowledge_base/*.md`) and `org_best_practices.md`, so generated
Terraform defaults to it unless a prompt names another region.

Generation (Gemini) is the one exception: `VERTEX_GENERATION_LOCATION` defaults to Vertex AI's
`global` endpoint rather than `asia-south1`, because the newest Gemini models sometimes ship
global-only before reaching a given region — pinning generation to `asia-south1` risks silently
losing access to the current model. This only affects where the *inference call* is routed, not
where documents/vectors are stored, so the India data-residency intent is preserved for data at
rest. If the dissertation's scope requires inference to stay in-region too, set
`VERTEX_GENERATION_LOCATION=asia-south1` and confirm the configured Gemini model is listed for
that region in [Vertex AI's generative AI locations](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations) —
if not, `asia-southeast1` (Singapore) is the nearest fallback with full Vertex AI feature parity.

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
  config.py              Settings (env-driven): GCP project/region, models, chunking, top-k, paths
  retry.py               Exponential backoff for Vertex AI 429/503 (fresh projects have low quota)
  ingestion/
    loader.py             Reads docs from GCS or a local dir
    chunker.py             Markdown-aware chunking: fenced HCL kept whole, heading path prefixed
    provider_docs.py       Fetches + cleans public provider docs (pinned release tag)
  embeddings/
    vertex.py              Vertex AI text-embedding-005; batched, retried, cached on disk
    local_tfidf.py          Dependency-light offline fallback (RAGIAC_MODE=local)
  vectorstore/
    in_memory.py            Exact cosine search; idempotent upsert; persisted JSON
    vertex_vector_search.py  Vertex AI Vector Search (implemented, not provisioned)
  retrieval/
    retriever.py            Top-k retrieval with optional per-document cap (diversification)
  generation/
    prompts.py               RAG and baseline prompts (same target-provider instruction)
    llm_vertex.py             Gemini wrapper: temperature, retry, code-fence stripping
    rag_generator.py / baseline_generator.py
    local_template_llm.py      Rule-based stand-in (RAGIAC_MODE=local) - NOT an LLM
  validation/
    terraform_validator.py    init/validate/plan with a shared provider plugin cache
    opa_validator.py           conftest/OPA; distinguishes "violation" from "could not evaluate"
  evaluation/
    intent.py                 Functional-intent checks (did it build the right thing?)
    taxonomy.py                Error taxonomy: validator output -> categories
    metrics.py                  pass@k (unbiased), Wilson CIs, retrieval hit rate
    runner.py                    Task x arm x sample runner, JSONL records, manifest, resume
    summary.py                    Aggregation, paired RAG-vs-baseline comparison, markdown report
  pipeline.py               Wires ingestion -> retrieval -> generation -> validation

scripts/
  fetch_provider_docs.py   Download public provider docs into the knowledge base
  ingest.py                 Build/refresh the vector index (idempotent)
  ask.py                     One requirement -> generated + validated Terraform
  benchmark.py                Full RAG vs baseline benchmark (see "Evaluation")

data/
  knowledge_base/          org conventions (hand-written) + provider_docs/ (fetched, public)
  policies/                 OPA/Rego policies generated Terraform must satisfy
  eval/gcp_tasks.jsonl       35 tasks with functional-intent specs
  cache/                     embedding + terraform-provider caches (gitignored; safe to keep)
results/<run_id>/           manifest.json, samples.jsonl, summary.json, summary.md per benchmark run

tests/                     unit + integration tests (conftest-backed tests skip if it is absent)
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
#   GOOGLE_CLOUD_REGION=asia-south1
#   GCS_BUCKET=<your-bucket>
#   VERTEX_VECTOR_INDEX_ID=<your Vertex AI Vector Search index id>
#   VERTEX_VECTOR_ENDPOINT_ID=<your Vertex AI Vector Search endpoint id>
# and authenticate with: gcloud auth application-default login
```

Terraform validation additionally requires the `terraform` CLI and, for policy checks, `conftest`
(both on PATH) — install these separately; the validators raise a clear error naming the missing
binary rather than failing silently. On Windows:

```powershell
winget install --id Hashicorp.Terraform -e
# conftest has no winget package; download the Windows release zip from
# https://github.com/open-policy-agent/conftest/releases and put conftest.exe on PATH.
```

Note: in RAGIAC_MODE=local, generation comes from `generation/local_template_llm.py` — a
rule-based stand-in (regex/keyword extraction into one of three fixed resource templates), not
an LLM. It's there so there's real, `terraform validate`-able HCL to look at and validate before
Vertex AI credentials are wired up, and its baseline arm deliberately omits the org's best-practice
defaults (labels, private-by-default, `asia-south1`) to roughly illustrate the grounding effect —
but it is NOT a source of the dissertation's actual RAG-vs-baseline benchmark numbers; those
require RAGIAC_MODE=gcp generating with the real LLM, since a template has no failure modes of
its own worth measuring.

## Running

```bash
# 1. Fetch public provider docs into the knowledge base (once; pinned to a release tag)
py scripts/fetch_provider_docs.py

# 2. Build the vector index (idempotent; embeddings are cached in data/cache, so re-runs are cheap)
py scripts/ingest.py

# 3. Ask for infrastructure
py scripts/ask.py "A Pub/Sub topic with a push subscription that delivers to a Cloud Run service"

# 4. Browser UI (ask tab + viewer for stored benchmark runs)
py -m streamlit run app.py
```

## Evaluation

```bash
py scripts/benchmark.py --only gcs-01,sql-01 --samples 2 --plan        # quick smoke test
py scripts/benchmark.py --samples 5 --k 1,3,5 --plan --workers 4 --temperature 0.8 --label "main"  # 35 tasks x 2 arms x 5
py scripts/benchmark.py --resume <id> --arms conventions --samples 5 --k 1,3,5 --plan --workers 4 --temperature 0.8  # add the control arm
py scripts/benchmark.py --resume <id> --redo-errors                   # re-run samples lost to API/tool failures
py scripts/benchmark.py --resume <run_id>                              # continue an interrupted run
py scripts/benchmark.py --summarize <run_id>                           # regenerate summary from records
py scripts/benchmark.py --max-per-doc 0 --label "ablation: no cap"     # retrieval ablations
```

**Metrics (fixed in advance, per the supervisor's remarks):** terraform validate/plan pass rate,
OPA policy-violation rate, pass@k (unbiased estimator, needs `--samples >= k`). Added: functional
intent pass rate, retrieval hit rate (was the provider doc for each needed resource retrieved?), and
95% Wilson intervals. Paired per-task comparisons (RAG vs baseline, RAG vs conventions-in-prompt) with an
exact sign test are included.

**Three arms.** `rag` (retrieved context), `baseline` (no context), and `conventions` (a control: the
org-convention docs pasted into the prompt, no retrieval). The control separates the value of *retrieving*
provider docs from the value of merely *knowing* the org conventions, which otherwise live only in the
retrieval corpus and so are invisible to the baseline.

**Design decisions worth stating in the report**
- *Same task specification for both arms.* Both are told the target provider (`~> 8.0`); the baseline
  differs only in having no retrieved context. Otherwise version skew would confound the comparison.
- *Three levels of correctness.* `terraform validate` = well-formed; OPA = obeys org policy; intent =
  built what was asked. A valid, compliant config for the wrong resource passes the first two.
- *OPA violation rate is over samples OPA could evaluate.* Unparseable HCL is a syntax failure, not a
  policy violation.
- *`terraform plan` is read-only and never applies*, and runs against the experimentation project only.
  Credential/project failures are classed `PLAN_ENVIRONMENT` and not counted against the model.
- *Policy-conflict tasks* (requirements that explicitly ask for what policy forbids, e.g. a public
  website bucket) are reported separately from the headline numbers.
- *Infrastructure failures are never scored.* API/quota failures and terraform tool failures (e.g. the
  provider plugin not loading) are flagged, excluded from error counts, and re-run with `--redo-errors`.
- *Every sample is stored* (generated HCL, retrieved chunks, validator diagnostics, error categories) and
  each run has a manifest (git commit, model, temperature, tool versions, task-file and policy hashes).

**Limitations to state honestly**
- The task set is this project's own (GCP), modelled on IaC-Eval's intent-specification approach.
  IaC-Eval itself is AWS-focused, so results are not comparable to its published numbers.
- Intent specs check attributes statically from HCL; values produced by `for_each`/variables can't be
  resolved, so tasks were written to avoid needing that.
- One LLM, one seed-free sampling temperature, ~35 tasks: report confidence intervals, not just point
  estimates, and treat category-level differences as indicative.
- The error taxonomy is derived from validator output and refined from data; map it onto the published
  taxonomy (arXiv:2512.14792) in the write-up.

## Status

Phase 3/4 (RAG pipeline and prototype) is working end to end on real GCP: ingestion of the public
`google` provider docs, retrieval, Gemini generation, `terraform`/OPA/intent validation, and a
resumable benchmark harness with per-sample records. `RAGIAC_MODE=local` remains for offline
development only.

## Mid-semester report

```bash
py scripts/benchmark.py --summarize main-01 --k 1,3,5     # refresh summary.json/md from stored records
py report/make_figures.py main-01                          # charts into report/figures/
py report/make_uml.py                                    # UML diagrams into report/figures/ (matplotlib; no PlantUML needed)
py report/build_report.py main-01 report/Mid_Semester_Report.docx
```

`report/` builds the report from the repository: front matter and method text live in `sections_*.py`,
Section 6 tables are computed from `results/<run_id>/`, and the interpretive prose is in
`commentary.py`. The document contains a contents field; Word updates it on open. Anything that states a
number about the code (test count, chunk count) is computed or taken from the run manifest.

The document follows the BITS sample report format (`report/assets/bits_logo.png` is the crest taken from it):
cover page, abstract with sign-off block, contents with lists of figures and tables, Arial 12 with 1.5
spacing, capitalised section headings, captions below as "Table N: ...", and a future-plan table.
The UML diagrams (`report/make_uml.py`, on the small kit in `report/uml.py`) are drawn from the classes,
methods and call sequences in `src/ragiac`; re-check them if that code changes.
