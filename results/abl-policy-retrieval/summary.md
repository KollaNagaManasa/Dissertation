# Benchmark summary

- run: `abl-policy-retrieval` - ablation: resource-tagged policy docs for retrieval
- model: `gemini-3.8-flash` @ temperature 0.8; embeddings `text-embedding-005`; top_k 8, max 3 chunks/doc, chunk 1500
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 5, terraform plan run: True, commit `2fb4fcde8e` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | rag |
|---|---|
| validate pass (init+validate) | 98.8% (96-100) n=165 |
| plan pass | 100.0% (97-100) n=149 |
| OPA violation rate (of evaluable) | 32.5% (26-40) n=163 |
| intent pass | 99.4% (97-100) n=165 |
| functional pass (validate + plan + intent) | 98.8% (96-100) n=165 |
| overall pass (functional + org policy) | 66.7% (59-73) n=165 |
| pass@1 (valid) | 98.8% |
| pass@1 (overall) | 66.7% |
| retrieval hit rate | 97.0% |

## Error categories (share of samples containing the category)

| category | rag |
|---|---|
| HCL_SYNTAX | 2 (1%) |
| INTENT_ATTRIBUTE_MISMATCH | 1 (1%) |
| POLICY_MISSING_LABELS | 31 (19%) |
| POLICY_OTHER | 22 (13%) |

## By category (overall pass rate)

| group | rag |
|---|---|
| compute | 100% |
| data | 0% |
| database | 16% |
| kubernetes | 75% |
| messaging | 100% |
| network | 100% |
| platform | 100% |
| security | 100% |
| serverless | 93% |
| storage | 40% |

## By difficulty (overall pass rate)

| group | rag |
|---|---|
| 1 | 78% |
| 2 | 44% |
| 3 | 75% |

## Requirements that conflict with org policy (reported separately)

- rag: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
