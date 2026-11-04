# Benchmark summary

- run: `final-01` - final run: 5 arms incl. rag_policy; self-reviewed templates; corrected Cloud SQL KB doc; all 5 policies
- model: `gemini-3.8-flash` @ temperature 0.8; embeddings `text-embedding-005`; top_k 8, max 3 chunks/doc, chunk 1500
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 5, terraform plan run: True, commit `a63a7f4922` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | baseline | conventions | rag | rag_policy | templates |
|---|---|---|---|---|---|
| validate pass (init+validate) | 98.8% (96-100) n=165 | 100.0% (98-100) n=165 | 98.8% (96-100) n=165 | 99.4% (97-100) n=165 | 99.4% (97-100) n=165 |
| plan pass | 100.0% (97-100) n=126 | 100.0% (98-100) n=151 | 100.0% (98-100) n=150 | 100.0% (98-100) n=155 | 100.0% (98-100) n=155 |
| OPA violation rate (of evaluable) | 48.2% (41-56) n=164 | 0.6% (0-3) n=165 | 32.1% (25-40) n=165 | 6.1% (3-11) n=164 | 9.7% (6-15) n=165 |
| intent pass | 97.6% (94-99) n=165 | 100.0% (98-100) n=165 | 100.0% (98-100) n=165 | 99.4% (97-100) n=165 | 97.0% (93-99) n=165 |
| functional pass (validate + plan + intent) | 97.0% (93-99) n=165 | 100.0% (98-100) n=165 | 98.8% (96-100) n=165 | 99.4% (97-100) n=165 | 96.4% (92-98) n=165 |
| overall pass (functional + org policy) | 50.9% (43-58) n=165 | 99.4% (97-100) n=165 | 67.3% (60-74) n=165 | 93.3% (88-96) n=165 | 86.7% (81-91) n=165 |
| pass@1 (valid) | 98.8% | 100.0% | 98.8% | 99.4% | 99.4% |
| pass@1 (overall) | 50.9% | 99.4% | 67.3% | 93.3% | 86.7% |
| pass@3 (valid) | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| pass@3 (overall) | 51.5% | 100.0% | 72.7% | 93.9% | 93.9% |
| pass@5 (valid) | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| pass@5 (overall) | 51.5% | 100.0% | 75.8% | 93.9% | 97.0% |
| retrieval hit rate | n/a | n/a | 97.0% | 97.0% | n/a |

## Paired comparison (per-task overall pass, RAG vs baseline)

First arm better on 9 tasks, second better on 0, tied on 24 (of 33); mean delta +0.164; exact sign test p = 0.0039.

## Paired comparison (per-task overall pass, RAG vs conventions-in-prompt)

First arm better on 0 tasks, second better on 12, tied on 21 (of 33); mean delta -0.321; exact sign test p = 0.0005.

## Paired comparison (per-task overall pass, hand-written conventions vs simulated internal templates)

First arm better on 7 tasks, second better on 0, tied on 26 (of 33); mean delta +0.127; exact sign test p = 0.0156.

## Paired comparison (per-task overall pass, RAG with pinned policy vs RAG)

First arm better on 10 tasks, second better on 0, tied on 23 (of 33); mean delta +0.261; exact sign test p = 0.0020.

## Paired comparison (per-task overall pass, RAG with pinned policy vs conventions-in-prompt)

First arm better on 0 tasks, second better on 3, tied on 30 (of 33); mean delta -0.061; exact sign test p = 0.2500.

## Error categories (share of samples containing the category)

| category | baseline | conventions | rag | rag_policy | templates |
|---|---|---|---|---|---|
| HCL_SYNTAX | 1 (1%) | 0 (0%) | 0 (0%) | 1 (1%) | 0 (0%) |
| INTENT_ATTRIBUTE_MISMATCH | 4 (2%) | 0 (0%) | 0 (0%) | 1 (1%) | 5 (3%) |
| INVALID_REFERENCE | 0 (0%) | 0 (0%) | 0 (0%) | 0 (0%) | 1 (1%) |
| MISSING_REQUIRED | 0 (0%) | 0 (0%) | 1 (1%) | 0 (0%) | 0 (0%) |
| POLICY_MISSING_LABELS | 69 (42%) | 0 (0%) | 33 (20%) | 0 (0%) | 0 (0%) |
| POLICY_OTHER | 20 (12%) | 1 (1%) | 22 (13%) | 10 (6%) | 16 (10%) |
| POLICY_PUBLIC_ACCESS | 20 (12%) | 0 (0%) | 6 (4%) | 0 (0%) | 0 (0%) |
| UNSUPPORTED_ARGUMENT | 0 (0%) | 0 (0%) | 1 (1%) | 0 (0%) | 0 (0%) |
| VALIDATE_OTHER | 1 (1%) | 0 (0%) | 0 (0%) | 0 (0%) | 0 (0%) |

## By category (overall pass rate)

| group | baseline | conventions | rag | rag_policy | templates |
|---|---|---|---|---|---|
| compute | 100% | 100% | 100% | 100% | 100% |
| data | 0% | 90% | 0% | 0% | 30% |
| database | 0% | 100% | 4% | 100% | 100% |
| kubernetes | 25% | 100% | 75% | 100% | 75% |
| messaging | 90% | 100% | 100% | 100% | 100% |
| network | 100% | 100% | 100% | 100% | 97% |
| platform | 100% | 100% | 100% | 100% | 100% |
| security | 100% | 100% | 100% | 100% | 100% |
| serverless | 100% | 100% | 100% | 100% | 100% |
| storage | 0% | 100% | 50% | 97% | 70% |

## By difficulty (overall pass rate)

| group | baseline | conventions | rag | rag_policy | templates |
|---|---|---|---|---|---|
| 1 | 50% | 100% | 78% | 100% | 96% |
| 2 | 30% | 98% | 40% | 90% | 84% |
| 3 | 68% | 100% | 80% | 91% | 82% |

## Requirements that conflict with org policy (reported separately)

- baseline: intent pass 80.0% (49-94) n=10, OPA violation rate 100.0% (68-100) n=8
- conventions: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10
- rag: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10
- rag_policy: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10
- templates: intent pass 100.0% (72-100) n=10, OPA violation rate 100.0% (72-100) n=10

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
