# Benchmark summary

- run: `lowtemp` - near-greedy: temperature 0
- model: `gemini-3.8-flash` @ temperature 0.0; embeddings `text-embedding-005`; top_k 8, max 3 chunks/doc, chunk 1500
- provider docs `v8.3.0`, target `~> 8.0`, terraform 1.16.2, Conftest: 0.70.0
- samples/task: 1, terraform plan run: True, commit `adc47f9b4d` (dirty: True)

## Headline metrics (95% Wilson CI in brackets)

| metric | baseline | conventions | rag |
|---|---|---|---|
| validate pass (init+validate) | 97.0% (85-99) n=33 | 97.0% (85-99) n=33 | 100.0% (90-100) n=33 |
| plan pass | 100.0% (88-100) n=27 | 100.0% (89-100) n=31 | 100.0% (89-100) n=32 |
| OPA violation rate (of evaluable) | 40.6% (26-58) n=32 | 0.0% (0-11) n=32 | 21.2% (11-38) n=33 |
| intent pass | 97.0% (85-99) n=33 | 97.0% (85-99) n=33 | 100.0% (90-100) n=33 |
| functional pass (validate + plan + intent) | 97.0% (85-99) n=33 | 97.0% (85-99) n=33 | 100.0% (90-100) n=33 |
| overall pass (functional + org policy) | 57.6% (41-73) n=33 | 97.0% (85-99) n=33 | 78.8% (62-89) n=33 |
| pass@1 (valid) | 97.0% | 97.0% | 100.0% |
| pass@1 (overall) | 57.6% | 97.0% | 78.8% |
| retrieval hit rate | n/a | n/a | 97.0% |

## Paired comparison (per-task overall pass, RAG vs baseline)

First arm better on 7 tasks, second better on 0, tied on 26 (of 33); mean delta +0.212; exact sign test p = 0.0156.

## Paired comparison (per-task overall pass, RAG vs conventions-in-prompt)

First arm better on 0 tasks, second better on 6, tied on 27 (of 33); mean delta -0.182; exact sign test p = 0.0312.

## Error categories (share of samples containing the category)

| category | baseline | conventions | rag |
|---|---|---|---|
| HCL_SYNTAX | 1 (3%) | 1 (3%) | 0 (0%) |
| INTENT_ATTRIBUTE_MISMATCH | 1 (3%) | 1 (3%) | 0 (0%) |
| MISSING_REQUIRED | 1 (3%) | 0 (0%) | 0 (0%) |
| POLICY_MISSING_LABELS | 13 (39%) | 0 (0%) | 7 (21%) |
| POLICY_PUBLIC_ACCESS | 3 (9%) | 0 (0%) | 0 (0%) |
| PROVIDER_INIT | 1 (3%) | 1 (3%) | 0 (0%) |

## By category (overall pass rate)

| group | baseline | conventions | rag |
|---|---|---|---|
| compute | 100% | 100% | 100% |
| data | 100% | 100% | 100% |
| database | 0% | 80% | 20% |
| kubernetes | 25% | 100% | 75% |
| messaging | 100% | 100% | 100% |
| network | 100% | 100% | 100% |
| platform | 100% | 100% | 100% |
| security | 100% | 100% | 100% |
| serverless | 100% | 100% | 100% |
| storage | 0% | 100% | 67% |

## By difficulty (overall pass rate)

| group | baseline | conventions | rag |
|---|---|---|---|
| 1 | 50% | 100% | 100% |
| 2 | 40% | 90% | 50% |
| 3 | 77% | 100% | 85% |

## Requirements that conflict with org policy (reported separately)

- baseline: intent pass 100.0% (34-100) n=2, OPA violation rate 100.0% (34-100) n=2
- conventions: intent pass 100.0% (34-100) n=2, OPA violation rate 100.0% (34-100) n=2
- rag: intent pass 100.0% (34-100) n=2, OPA violation rate 100.0% (34-100) n=2

A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.
