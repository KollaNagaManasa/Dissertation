# Benchmark summary

- run: `main-01` - main run: T=0.8, 5 samples/task, plan on
- model: `gemini-3.8-flash` @ temperature 0.8; embeddings `text-embedding-005`; top_k 8, max 3 chunks/doc, chunk 1500
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 5, terraform plan run: True, commit `adc47f9b4d` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | baseline | conventions | rag | templates |
|---|---|---|---|---|
| validate pass (init+validate) | 99.4% (97-100) n=165 | 97.6% (94-99) n=165 | 98.8% (96-100) n=165 | 98.2% (95-99) n=165 |
| plan pass | 98.5% (95-100) n=135 | 97.4% (93-99) n=153 | 100.0% (98-100) n=154 | 97.4% (93-99) n=152 |
| OPA violation rate (of evaluable) | 42.7% (35-50) n=164 | 0.0% (0-2) n=163 | 20.1% (15-27) n=164 | 0.0% (0-2) n=164 |
| intent pass | 98.2% (95-99) n=165 | 99.4% (97-100) n=165 | 99.4% (97-100) n=165 | 99.4% (97-100) n=165 |
| functional pass (validate + plan + intent) | 97.0% (93-99) n=165 | 95.2% (91-98) n=165 | 98.8% (96-100) n=165 | 95.8% (92-98) n=165 |
| overall pass (functional + org policy) | 57.0% (49-64) n=165 | 95.2% (91-98) n=165 | 78.8% (72-84) n=165 | 95.8% (92-98) n=165 |
| pass@1 (valid) | 99.4% | 97.6% | 98.8% | 98.2% |
| pass@1 (overall) | 57.0% | 95.2% | 78.8% | 95.8% |
| retrieval hit rate | n/a | n/a | 97.0% | n/a |

## Paired comparison (per-task overall pass, RAG vs baseline)

First arm better on 10 tasks, second better on 0, tied on 23 (of 33); mean delta +0.218; exact sign test p = 0.0020.

## Paired comparison (per-task overall pass, RAG vs conventions-in-prompt)

First arm better on 3 tasks, second better on 10, tied on 20 (of 33); mean delta -0.164; exact sign test p = 0.0923.

## Paired comparison (per-task overall pass, hand-written conventions vs reviewed internal templates)

First arm better on 2 tasks, second better on 3, tied on 28 (of 33); mean delta -0.006; exact sign test p = 1.0000.

## Error categories (share of samples containing the category)

| category | baseline | conventions | rag | templates |
|---|---|---|---|---|
| GENERATION_FAILED | 0 (0%) | 0 (0%) | 0 (0%) | 1 (1%) |
| HCL_SYNTAX | 1 (1%) | 2 (1%) | 1 (1%) | 0 (0%) |
| INTENT_ATTRIBUTE_MISMATCH | 3 (2%) | 1 (1%) | 1 (1%) | 0 (0%) |
| INTENT_MISSING_RESOURCE | 0 (0%) | 0 (0%) | 1 (1%) | 0 (0%) |
| INVALID_REFERENCE | 0 (0%) | 0 (0%) | 1 (1%) | 0 (0%) |
| PLAN_ERROR | 2 (1%) | 4 (2%) | 0 (0%) | 4 (2%) |
| POLICY_MISSING_LABELS | 70 (42%) | 0 (0%) | 33 (20%) | 0 (0%) |
| POLICY_PUBLIC_ACCESS | 19 (12%) | 0 (0%) | 0 (0%) | 0 (0%) |

## By category (overall pass rate)

| group | baseline | conventions | rag | templates |
|---|---|---|---|---|
| compute | 100% | 100% | 100% | 100% |
| data | 90% | 100% | 100% | 80% |
| database | 0% | 80% | 16% | 84% |
| kubernetes | 25% | 95% | 75% | 100% |
| messaging | 100% | 90% | 100% | 100% |
| network | 100% | 100% | 100% | 100% |
| platform | 100% | 100% | 100% | 100% |
| security | 100% | 90% | 100% | 90% |
| serverless | 100% | 100% | 100% | 100% |
| storage | 0% | 100% | 70% | 100% |

## By difficulty (overall pass rate)

| group | baseline | conventions | rag | templates |
|---|---|---|---|---|
| 1 | 50% | 98% | 84% | 100% |
| 2 | 40% | 92% | 58% | 90% |
| 3 | 75% | 95% | 91% | 97% |

## Requirements that conflict with org policy (reported separately)

- baseline: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10
- conventions: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10
- rag: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10
- templates: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
