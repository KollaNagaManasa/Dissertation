"""Aggregates per-sample records into the metrics fixed in advance (supervisor remarks):
validate/plan pass rate, OPA policy-violation rate, pass@k — plus functional-intent pass rate,
retrieval hit rate, an error-category breakdown, and a paired RAG-vs-baseline comparison.

Requirements that deliberately conflict with org policy (category "policy_conflict") are excluded
from the headline numbers and reported in their own section, so they can't distort the comparison.
"""

import math
from collections import Counter, defaultdict

from ragiac.evaluation.metrics import group_counts, mean_pass_at_k, wilson_interval
from ragiac.evaluation.taxonomy import NON_MODEL_PLAN_ERRORS as _INFRASTRUCTURE_ERRORS  # not model errors

CONFLICT_CATEGORY = "policy_conflict"


def _functional(r: dict) -> bool:
    """Technically correct: validates, plans (where evaluable) and builds what was asked - i.e.
    overall pass *excluding* org-policy conformance, which depends on conventions the requirement
    never states."""
    return bool(r["validate_pass"] and r.get("plan_pass") is not False and r["intent_pass"])


def _rate(records: list[dict], predicate, denominator: list[dict] | None = None) -> dict:
    pool = records if denominator is None else denominator
    hits = sum(1 for r in pool if predicate(r))
    lo, hi = wilson_interval(hits, len(pool))
    return {"rate": (hits / len(pool)) if pool else None, "n": len(pool), "ci95": [round(lo, 4), round(hi, 4)]}


def _arm_metrics(records: list[dict], ks: list[int]) -> dict:
    planned = [r for r in records if r.get("plan_pass") is not None]
    evaluated = [r for r in records if r.get("policy_evaluated")]
    rag_hits = [r["retrieval_hit"] for r in records if r.get("retrieval_hit") is not None]

    model_errors: Counter = Counter()
    flags: Counter = Counter()
    for r in records:
        for code in set(r.get("errors", [])) - _INFRASTRUCTURE_ERRORS:
            model_errors[code] += 1
        for flag in set(r.get("flags", [])):
            flags[flag] += 1

    valid_counts = group_counts(records, lambda r: r["validate_pass"]).values()
    overall_counts = group_counts(records, lambda r: r["overall_pass"]).values()

    return {
        "samples": len(records),
        "tasks": len({r["task_id"] for r in records}),
        "validate_pass_rate": _rate(records, lambda r: r["validate_pass"]),
        "plan_pass_rate": _rate(planned, lambda r: r["plan_pass"]) if planned else None,
        # Denominator is samples OPA could actually evaluate — unparseable HCL is a syntax
        # failure, not a policy violation.
        "opa_violation_rate": _rate(evaluated, lambda r: not r["policy_pass"]),
        "intent_pass_rate": _rate(records, lambda r: r["intent_pass"]),
        "functional_pass_rate": _rate(records, _functional),
        "overall_pass_rate": _rate(records, lambda r: r["overall_pass"]),
        "pass_at_k_valid": {str(k): mean_pass_at_k(valid_counts, k) for k in ks},
        "pass_at_k_overall": {str(k): mean_pass_at_k(overall_counts, k) for k in ks},
        "retrieval_hit_rate": (sum(rag_hits) / len(rag_hits)) if rag_hits else None,
        "error_counts": dict(model_errors.most_common()),
        "flag_counts": dict(flags.most_common()),
        "mean_gen_latency_s": _mean([r.get("latency_gen_s") for r in records]),
        "mean_deprecation_warnings": _mean([r.get("deprecation_warnings", 0) for r in records]),
    }


def _mean(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def _sign_test_p(wins: int, losses: int) -> float | None:
    """Exact two-sided sign test on non-tied tasks (H0: each arm equally likely to win)."""
    n = wins + losses
    if n == 0:
        return None
    k = min(wins, losses)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2**n
    return min(1.0, 2 * p)


def _paired(records: list[dict], arm_a: str = "rag", arm_b: str = "baseline") -> dict | None:
    by_task: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_task[r["task_id"]][r["arm"]].append(1 if r["overall_pass"] else 0)
    wins = losses = ties = 0
    deltas = {}
    for task, arms in by_task.items():
        if arm_a not in arms or arm_b not in arms:
            continue
        rag, base = sum(arms[arm_a]) / len(arms[arm_a]), sum(arms[arm_b]) / len(arms[arm_b])
        deltas[task] = round(rag - base, 3)
        wins, losses, ties = wins + (rag > base), losses + (rag < base), ties + (rag == base)
    if not deltas:
        return None
    return {
        "arm_a": arm_a,
        "arm_b": arm_b,
        "tasks_compared": len(deltas),
        "rag_better": wins,
        "baseline_better": losses,
        "tied": ties,
        "sign_test_p": _sign_test_p(wins, losses),
        "mean_delta_overall_pass": round(sum(deltas.values()) / len(deltas), 3),
        "per_task_delta": deltas,
    }


def _breakdown(records: list[dict], key: str) -> dict:
    groups: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        groups[str(r[key])][r["arm"]].append(r)
    return {
        group: {arm: round(sum(1 for r in rs if r["overall_pass"]) / len(rs), 3) for arm, rs in arms.items()}
        for group, arms in sorted(groups.items())
    }


def summarize(records: list[dict], ks: list[int] | None = None) -> dict:
    ks = ks or [1]
    headline = [r for r in records if r["category"] != CONFLICT_CATEGORY]
    conflict = [r for r in records if r["category"] == CONFLICT_CATEGORY]
    arms = sorted({r["arm"] for r in records})

    return {
        "headline": {arm: _arm_metrics([r for r in headline if r["arm"] == arm], ks) for arm in arms if headline},
        "paired_overall_pass": _paired(headline),
        "paired_rag_vs_conventions": _paired(headline, "rag", "conventions") if "conventions" in arms else None,
        "by_category": _breakdown(headline, "category"),
        "by_difficulty": _breakdown(headline, "difficulty"),
        "policy_conflict_tasks": {
            arm: _arm_metrics([r for r in conflict if r["arm"] == arm], ks) for arm in arms if conflict
        },
    }


def _pct(metric: dict | None) -> str:
    if not metric or metric.get("rate") is None:
        return "n/a"
    lo, hi = metric["ci95"]
    return f"{metric['rate'] * 100:.1f}% ({lo * 100:.0f}-{hi * 100:.0f}) n={metric['n']}"


def render_markdown(manifest: dict | None, summary: dict) -> str:
    lines = ["# Benchmark summary", ""]
    if manifest:
        lines += [
            f"- run: `{manifest['run_id']}` {('- ' + manifest['label']) if manifest.get('label') else ''}",
            f"- model: `{manifest['generation_model']}` @ temperature {manifest['temperature']}; "
            f"embeddings `{manifest['embedding_model']}`; top_k {manifest['top_k']}, "
            f"max {manifest['max_chunks_per_doc']} chunks/doc, chunk {manifest['chunk_size']}",
            f"- provider docs `{manifest['provider_docs_tag']}`, target `{manifest['target_provider_constraint']}`, "
            f"terraform {manifest['terraform_version']}, {manifest['conftest_version']}",
            f"- samples/task: {manifest['samples_per_task']}, terraform plan run: {manifest['terraform_plan_run']}, "
            f"commit `{(manifest['git_commit'] or 'n/a')[:10]}` (dirty: {manifest['git_dirty']})",
            "",
        ]

    headline = summary["headline"]
    arms = list(headline)
    lines += ["## Headline metrics (95% Wilson CI in brackets)", "", "| metric | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
    for label, key in [
        ("validate pass (init+validate)", "validate_pass_rate"),
        ("plan pass", "plan_pass_rate"),
        ("OPA violation rate (of evaluable)", "opa_violation_rate"),
        ("intent pass", "intent_pass_rate"),
        ("functional pass (validate + plan + intent)", "functional_pass_rate"),
        ("overall pass (functional + org policy)", "overall_pass_rate"),
    ]:
        lines.append(f"| {label} | " + " | ".join(_pct(headline[a][key]) for a in arms) + " |")
    ks = sorted({int(k) for a in arms for k in headline[a]["pass_at_k_overall"]})
    for k in ks:
        for label, key in [("valid", "pass_at_k_valid"), ("overall", "pass_at_k_overall")]:
            cells = []
            for a in arms:
                v = headline[a][key].get(str(k))
                cells.append("n/a" if v is None else f"{v * 100:.1f}%")
            lines.append(f"| pass@{k} ({label}) | " + " | ".join(cells) + " |")
    lines.append("| retrieval hit rate | " + " | ".join(
        "n/a" if headline[a]["retrieval_hit_rate"] is None else f"{headline[a]['retrieval_hit_rate'] * 100:.1f}%" for a in arms
    ) + " |")

    for key, title in (("paired_overall_pass", "RAG vs baseline"), ("paired_rag_vs_conventions", "RAG vs conventions-in-prompt")):
        paired = summary.get(key)
        if paired:
            lines += [
                "",
                f"## Paired comparison (per-task overall pass, {title})",
                "",
                f"First arm better on {paired['rag_better']} tasks, second better on {paired['baseline_better']}, "
                f"tied on {paired['tied']} (of {paired['tasks_compared']}); mean delta "
                f"{paired['mean_delta_overall_pass']:+.3f}; exact sign test p = "
                f"{'n/a' if paired['sign_test_p'] is None else format(paired['sign_test_p'], '.4f')}.",
            ]

    lines += ["", "## Error categories (share of samples containing the category)", ""]
    all_codes = sorted({c for a in arms for c in headline[a]["error_counts"]})
    if all_codes:
        lines += ["| category | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
        for code in all_codes:
            cells = [
                f"{headline[a]['error_counts'].get(code, 0)} ({headline[a]['error_counts'].get(code, 0) / max(headline[a]['samples'], 1) * 100:.0f}%)"
                for a in arms
            ]
            lines.append(f"| {code} | " + " | ".join(cells) + " |")
    else:
        lines.append("No errors recorded.")

    for title, key in [("By category (overall pass rate)", "by_category"), ("By difficulty (overall pass rate)", "by_difficulty")]:
        lines += ["", f"## {title}", "", "| group | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
        for group, values in summary[key].items():
            lines.append(f"| {group} | " + " | ".join(f"{values.get(a, float('nan')) * 100:.0f}%" if a in values else "n/a" for a in arms) + " |")

    conflict = summary.get("policy_conflict_tasks") or {}
    if conflict:
        lines += ["", "## Requirements that conflict with org policy (reported separately)", ""]
        for arm, m in conflict.items():
            lines.append(f"- {arm}: intent pass {_pct(m['intent_pass_rate'])}, OPA violation rate {_pct(m['opa_violation_rate'])}")
        lines.append("")
        lines.append("A high intent-pass with OPA violations means the model did what was asked and the policy layer overrode it — by design.")
    return "\n".join(lines) + "\n"
