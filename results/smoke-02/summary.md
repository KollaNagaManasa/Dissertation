# Benchmark summary

- run: `smoke-02` - smoke test after retrieval-hit/plan-input fixes
- model: `gemini-3.8-flash` @ temperature 0.2; embeddings `text-embedding-005`; top_k 8, max 3 chunks/doc, chunk 1500
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 1, terraform plan run: True, commit `adc47f9b4d` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | baseline | rag |
|---|---|---|
| validate pass (init+validate) | 100.0% (65-100) n=7 | 100.0% (65-100) n=7 |
| plan pass | 100.0% (57-100) n=5 | 100.0% (61-100) n=6 |
| OPA violation rate (of evaluable) | 42.9% (16-75) n=7 | 28.6% (8-64) n=7 |
| intent pass | 100.0% (65-100) n=7 | 100.0% (65-100) n=7 |
| functional pass (validate + plan + intent) | 100.0% (65-100) n=7 | 100.0% (65-100) n=7 |
| overall pass (functional + org policy) | 57.1% (25-84) n=7 | 71.4% (36-92) n=7 |
| pass@1 (valid) | 100.0% | 100.0% |
| pass@1 (overall) | 57.1% | 71.4% |
| retrieval hit rate | n/a | 85.7% |

## Paired comparison (per-task overall pass, RAG vs baseline)

RAG better on 1 tasks, baseline better on 0, tied on 6 (of 7); mean delta +0.143; exact sign test p = 1.0000.

## Error categories (share of samples containing the category)

| category | baseline | rag |
|---|---|---|
| POLICY_MISSING_LABELS | 3 (43%) | 2 (29%) |
| POLICY_PUBLIC_ACCESS | 1 (14%) | 0 (0%) |

## By category (overall pass rate)

| group | baseline | rag |
|---|---|---|
| compute | 100% | 100% |
| data | 100% | 100% |
| database | 0% | 0% |
| kubernetes | 0% | 0% |
| network | 100% | 100% |
| serverless | 100% | 100% |
| storage | 0% | 100% |

## By difficulty (overall pass rate)

| group | baseline | rag |
|---|---|---|
| 2 | 0% | 0% |
| 3 | 67% | 83% |

## Requirements that conflict with org policy (reported separately)

- baseline: intent pass 100.0% (21-100) n=1, OPA violation rate 100.0% (21-100) n=1
- rag: intent pass 100.0% (21-100) n=1, OPA violation rate 100.0% (21-100) n=1

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
