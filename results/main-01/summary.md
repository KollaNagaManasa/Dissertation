# Benchmark summary

- run: `main-01` - main run: T=0.8, 5 samples/task, plan on
- model: `gemini-3.8-flash` @ temperature 0.8; embeddings `text-embedding-005`; top_k 8, max 3 chunks/doc, chunk 1500
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 5, terraform plan run: True, commit `adc47f9b4d` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | baseline | conventions | rag |
|---|---|---|---|
| validate pass (init+validate) | 99.4% (97-100) n=165 | 97.6% (94-99) n=165 | 98.8% (96-100) n=165 |
| plan pass | 98.5% (95-100) n=135 | 97.4% (93-99) n=153 | 100.0% (98-100) n=154 |
| OPA violation rate (of evaluable) | 42.7% (35-50) n=164 | 0.0% (0-2) n=163 | 20.1% (15-27) n=164 |
| intent pass | 98.2% (95-99) n=165 | 99.4% (97-100) n=165 | 99.4% (97-100) n=165 |
| functional pass (validate + plan + intent) | 97.0% (93-99) n=165 | 95.2% (91-98) n=165 | 98.8% (96-100) n=165 |
| overall pass (functional + org policy) | 57.0% (49-64) n=165 | 95.2% (91-98) n=165 | 78.8% (72-84) n=165 |
| pass@1 (valid) | 99.4% | 97.6% | 98.8% |
| pass@1 (overall) | 57.0% | 95.2% | 78.8% |
| pass@3 (valid) | 100.0% | 100.0% | 100.0% |
| pass@3 (overall) | 57.6% | 98.8% | 83.3% |
| pass@5 (valid) | 100.0% | 100.0% | 100.0% |
| pass@5 (overall) | 57.6% | 100.0% | 84.8% |
| retrieval hit rate | n/a | n/a | 97.0% |

## Paired comparison (per-task overall pass, RAG vs baseline)

First arm better on 10 tasks, second better on 0, tied on 23 (of 33); mean delta +0.218; exact sign test p = 0.0020.

## Paired comparison (per-task overall pass, RAG vs conventions-in-prompt)

First arm better on 3 tasks, second better on 10, tied on 20 (of 33); mean delta -0.164; exact sign test p = 0.0923.

## Error categories (share of samples containing the category)

| category | baseline | conventions | rag |
|---|---|---|---|
| HCL_SYNTAX | 1 (1%) | 2 (1%) | 1 (1%) |
| INTENT_ATTRIBUTE_MISMATCH | 3 (2%) | 1 (1%) | 1 (1%) |
| INTENT_MISSING_RESOURCE | 0 (0%) | 0 (0%) | 1 (1%) |
| INVALID_REFERENCE | 0 (0%) | 0 (0%) | 1 (1%) |
| PLAN_ERROR | 2 (1%) | 4 (2%) | 0 (0%) |
| POLICY_MISSING_LABELS | 70 (42%) | 0 (0%) | 33 (20%) |
| POLICY_PUBLIC_ACCESS | 19 (12%) | 0 (0%) | 0 (0%) |
| PROVIDER_INIT | 1 (1%) | 4 (2%) | 1 (1%) |

## By category (overall pass rate)

| group | baseline | conventions | rag |
|---|---|---|---|
| compute | 100% | 100% | 100% |
| data | 90% | 100% | 100% |
| database | 0% | 80% | 16% |
| kubernetes | 25% | 95% | 75% |
| messaging | 100% | 90% | 100% |
| network | 100% | 100% | 100% |
| platform | 100% | 100% | 100% |
| security | 100% | 90% | 100% |
| serverless | 100% | 100% | 100% |
| storage | 0% | 100% | 70% |

## By difficulty (overall pass rate)

| group | baseline | conventions | rag |
|---|---|---|---|
| 1 | 50% | 98% | 84% |
| 2 | 40% | 92% | 58% |
| 3 | 75% | 95% | 91% |

## Requirements that conflict with org policy (reported separately)

- baseline: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10
- conventions: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10
- rag: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
