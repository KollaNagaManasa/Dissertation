# Benchmark summary

- run: `abl-chunk800` - ablation: chunk_size=800 (vs default 1500)
- model: `gemini-3.8-flash` @ temperature 0.8; embeddings `text-embedding-005`; top_k 8, max 3 chunks/doc, chunk 800
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 3, terraform plan run: True, commit `3680efdcdd` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | rag |
|---|---|
| validate pass (init+validate) | 99.0% (94-100) n=99 |
| plan pass | 100.0% (96-100) n=93 |
| OPA violation rate (of evaluable) | 21.4% (14-31) n=98 |
| intent pass | 99.0% (94-100) n=99 |
| functional pass (validate + plan + intent) | 99.0% (94-100) n=99 |
| overall pass (functional + org policy) | 77.8% (69-85) n=99 |
| pass@1 (valid) | 99.0% |
| pass@1 (overall) | 77.8% |
| retrieval hit rate | 98.0% |

## Error categories (share of samples containing the category)

| category | rag |
|---|---|
| HCL_SYNTAX | 1 (1%) |
| INTENT_ATTRIBUTE_MISMATCH | 1 (1%) |
| POLICY_MISSING_LABELS | 21 (21%) |
| POLICY_PUBLIC_ACCESS | 1 (1%) |

## By category (overall pass rate)

| group | rag |
|---|---|
| compute | 100% |
| data | 100% |
| database | 13% |
| kubernetes | 50% |
| messaging | 100% |
| network | 100% |
| platform | 100% |
| security | 100% |
| serverless | 100% |
| storage | 83% |

## By difficulty (overall pass rate)

| group | rag |
|---|---|
| 1 | 90% |
| 2 | 60% |
| 3 | 82% |

## Requirements that conflict with org policy (reported separately)

- rag: intent pass 100.0% (61-100) n=6, OPA violation rate 100.0% (61-100) n=6

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
