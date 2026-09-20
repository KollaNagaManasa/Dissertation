# Benchmark summary

- run: `abl-topk3` - ablation: top_k=3
- model: `gemini-3.8-flash` @ temperature 0.8; embeddings `text-embedding-005`; top_k 3, max 3 chunks/doc, chunk 1500
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 3, terraform plan run: True, commit `adc47f9b4d` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | rag |
|---|---|
| validate pass (init+validate) | 97.0% (91-99) n=99 |
| plan pass | 100.0% (96-100) n=91 |
| OPA violation rate (of evaluable) | 23.5% (16-33) n=98 |
| intent pass | 100.0% (96-100) n=99 |
| functional pass (validate + plan + intent) | 97.0% (91-99) n=99 |
| overall pass (functional + org policy) | 73.7% (64-81) n=99 |
| pass@1 (valid) | 97.0% |
| pass@1 (overall) | 73.7% |
| pass@3 (valid) | 100.0% |
| pass@3 (overall) | 78.8% |
| retrieval hit rate | 94.4% |

## Error categories (share of samples containing the category)

| category | rag |
|---|---|
| HCL_SYNTAX | 1 (1%) |
| POLICY_MISSING_LABELS | 22 (22%) |
| POLICY_PUBLIC_ACCESS | 3 (3%) |
| PROVIDER_INIT | 3 (3%) |

## By category (overall pass rate)

| group | rag |
|---|---|
| compute | 100% |
| data | 100% |
| database | 0% |
| kubernetes | 50% |
| messaging | 100% |
| network | 94% |
| platform | 100% |
| security | 100% |
| serverless | 100% |
| storage | 78% |

## By difficulty (overall pass rate)

| group | rag |
|---|---|
| 1 | 83% |
| 2 | 53% |
| 3 | 82% |

## Requirements that conflict with org policy (reported separately)

- rag: intent pass 100.0% (61-100) n=6, OPA violation rate 100.0% (61-100) n=6

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
