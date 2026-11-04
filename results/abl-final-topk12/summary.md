# Benchmark summary

- run: `abl-final-topk12` - final retrieval ablation: rag_policy top_k=12
- model: `gemini-3.8-flash` @ temperature 0.8; embeddings `text-embedding-005`; top_k 12, max 3 chunks/doc, chunk 1500
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 3, terraform plan run: True, commit `c55ebd7331` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | rag_policy |
|---|---|
| validate pass (init+validate) | 100.0% (96-100) n=99 |
| plan pass | 100.0% (96-100) n=95 |
| OPA violation rate (of evaluable) | 6.1% (3-13) n=99 |
| intent pass | 100.0% (96-100) n=99 |
| functional pass (validate + plan + intent) | 100.0% (96-100) n=99 |
| overall pass (functional + org policy) | 93.9% (87-97) n=99 |
| pass@1 (valid) | 100.0% |
| pass@1 (overall) | 93.9% |
| pass@3 (valid) | 100.0% |
| pass@3 (overall) | 93.9% |
| retrieval hit rate | 100.0% |

## Error categories (share of samples containing the category)

| category | rag_policy |
|---|---|
| POLICY_OTHER | 6 (6%) |

## By category (overall pass rate)

| group | rag_policy |
|---|---|
| compute | 100% |
| data | 0% |
| database | 100% |
| kubernetes | 100% |
| messaging | 100% |
| network | 100% |
| platform | 100% |
| security | 100% |
| serverless | 100% |
| storage | 100% |

## By difficulty (overall pass rate)

| group | rag_policy |
|---|---|
| 1 | 100% |
| 2 | 90% |
| 3 | 92% |

## Requirements that conflict with org policy (reported separately)

- rag_policy: intent pass 100.0% (61-100) n=6, OPA violation rate 100.0% (61-100) n=6

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
