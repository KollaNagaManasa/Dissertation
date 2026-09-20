# Benchmark summary

- run: `abl-nocap` - ablation: no per-document cap
- model: `gemini-3.8-flash` @ temperature 0.8; embeddings `text-embedding-005`; top_k 8, max 0 chunks/doc, chunk 1500
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 3, terraform plan run: True, commit `adc47f9b4d` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | rag |
|---|---|
| validate pass (init+validate) | 96.0% (90-98) n=99 |
| plan pass | 100.0% (96-100) n=90 |
| OPA violation rate (of evaluable) | 19.6% (13-29) n=97 |
| intent pass | 99.0% (94-100) n=99 |
| functional pass (validate + plan + intent) | 96.0% (90-98) n=99 |
| overall pass (functional + org policy) | 78.8% (70-86) n=99 |
| pass@1 (valid) | 96.0% |
| pass@1 (overall) | 78.8% |
| pass@3 (valid) | 100.0% |
| pass@3 (overall) | 84.8% |
| retrieval hit rate | 97.0% |

## Error categories (share of samples containing the category)

| category | rag |
|---|---|
| HCL_SYNTAX | 2 (2%) |
| INTENT_ATTRIBUTE_MISMATCH | 1 (1%) |
| INVALID_REFERENCE | 1 (1%) |
| POLICY_MISSING_LABELS | 19 (19%) |
| PROVIDER_INIT | 2 (2%) |
| UNSUPPORTED_ARGUMENT | 1 (1%) |
| UNSUPPORTED_BLOCK | 1 (1%) |

## By category (overall pass rate)

| group | rag |
|---|---|
| compute | 83% |
| data | 100% |
| database | 13% |
| kubernetes | 75% |
| messaging | 100% |
| network | 94% |
| platform | 100% |
| security | 100% |
| serverless | 100% |
| storage | 83% |

## By difficulty (overall pass rate)

| group | rag |
|---|---|
| 1 | 87% |
| 2 | 53% |
| 3 | 92% |

## Requirements that conflict with org policy (reported separately)

- rag: intent pass 100.0% (61-100) n=6, OPA violation rate 100.0% (61-100) n=6

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
