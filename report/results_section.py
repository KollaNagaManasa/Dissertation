"""Report sections 6, 7, 9 and the abstract. Numbers come straight from the stored run; the
interpretive prose lives in commentary.py so it can be written once the numbers are known."""

from collections import Counter, defaultdict
from pathlib import Path

FIG = Path(__file__).resolve().parent / "figures"
ARMS = ("baseline", "conventions", "rag")
NAMES = {"baseline": "Baseline", "conventions": "Conventions in prompt", "rag": "RAG"}

try:  # interpretive text, written after inspecting the results
    import commentary as C  # type: ignore
except ImportError:  # pragma: no cover
    C = None


def _c(key: str, default: str = "") -> str:
    return getattr(C, key, default) if C else default


def widths(n_arms: int, first: float = 6.4) -> list[float]:
    return [first] + [round((16.0 - first) / n_arms, 2)] * n_arms


def fmt(metric: dict | None, with_n: bool = False) -> str:
    if not metric or metric.get("rate") is None:
        return "n/a"
    lo, hi = metric["ci95"]
    text = f"{metric['rate'] * 100:.1f}% [{lo * 100:.0f}-{hi * 100:.0f}]"
    return f"{text} (n={metric['n']})" if with_n else text


def pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


def _paragraphs(R, text: str):
    for block in [b.strip() for b in text.split("\n\n") if b.strip()]:
        R.p(block)


def abstract(R, summary, manifest):
    R.h1("Abstract", page_break=True)
    text = _c("ABSTRACT")
    if text:
        _paragraphs(R, text)
    else:
        R.p("(Abstract to be completed once results are final.)")
    R.signature_block(
        ["Signature of the Student", "Name: Kolla Naga Manasa", "Date:", "Place: Hyderabad"],
        ["Signature of the Supervisor", "Name: Karthik Reddy Charla", "Date:", "Place: Hyderabad"],
    )


def results(R, summary, manifest, records, extra=None):
    R.h1("6. Results")
    if not summary or not summary.get("headline"):
        R.p("The benchmark has not produced results yet.")
        return
    H = summary["headline"]
    arms = [a for a in ARMS if a in H]
    n_tasks = H[arms[0]]["tasks"]

    # ---- 6.1 overview ------------------------------------------------------------------------------
    R.h2("6.1 The run")
    infra = sum(1 for r in records if r.get("generation_error") or r.get("validation_error"))
    R.p(
        f"The reported run evaluates {n_tasks} headline tasks under {len(arms)} arms with "
        f"{manifest['samples_per_task']} samples per task per arm ({sum(H[a]['samples'] for a in arms)} headline samples; "
        f"{len(records)} including the policy-conflict tasks), using `{manifest['generation_model']}` at temperature "
        f"{manifest['temperature']}, `terraform plan` enabled, and an index of {manifest['index_chunks']} chunks. "
        f"{infra} sample(s) remain unscored because of infrastructure failure; samples that failed for such reasons during the run were generated again (Section 7). Full settings are in Appendix D."
    )

    # ---- 6.2 headline --------------------------------------------------------------------------------
    R.h2("6.2 Headline metrics")
    rows = []
    for label, key in [
        ("Validate pass (init + validate)", "validate_pass_rate"),
        ("Plan pass (where evaluable)", "plan_pass_rate"),
        ("Intent pass", "intent_pass_rate"),
        ("Functional pass (validate + plan + intent)", "functional_pass_rate"),
        ("OPA violation rate (of evaluable)", "opa_violation_rate"),
        ("Overall pass (functional + policy)", "overall_pass_rate"),
    ]:
        rows.append([label] + [fmt(H[a].get(key)) for a in arms])
    ks = sorted({int(k) for a in arms for k in H[a]["pass_at_k_overall"]})
    for k in ks:
        for label, key in (("valid", "pass_at_k_valid"), ("overall", "pass_at_k_overall")):
            rows.append([f"pass@{k} ({label})"] + [pct(H[a][key].get(str(k))) for a in arms])
    rows.append(["Retrieval hit rate"] + [pct(H[a]["retrieval_hit_rate"]) if a == "rag" else "-" for a in arms])
    R.table(
        ["Metric"] + [NAMES[a] for a in arms],
        rows,
        widths(len(arms), 6.4),
        "Headline metrics. Proportions show the 95% Wilson interval in brackets.",
        align_right_from=1,
    )
    if (FIG / "pass_rates.png").exists():
        R.figure(FIG / "pass_rates.png", 14.5, "Pass rates by arm with 95% confidence intervals.")
    _paragraphs(R, _c("HEADLINE"))

    # ---- 6.3 paired -----------------------------------------------------------------------------------
    task_text = {r["task_id"]: r["requirement"] for r in records}
    comparisons = [
        ("paired_overall_pass", "RAG", "the baseline"),
        ("paired_rag_vs_conventions", "RAG", "the conventions-in-prompt control"),
    ]
    if any(summary.get(k) for k, _, _ in comparisons):
        R.h2("6.3 Paired comparison across tasks")
    for key, first, second in comparisons:
        paired = summary.get(key)
        if not paired:
            continue
        p = paired["sign_test_p"]
        R.p(
            f"Comparing {first} with {second} task by task, {first} had the higher overall pass rate on "
            f"{paired['rag_better']} of {paired['tasks_compared']} tasks, {second} on {paired['baseline_better']}, "
            f"and they tied on {paired['tied']}. The mean per-task difference in overall pass rate is "
            f"{paired['mean_delta_overall_pass'] * 100:+.1f} percentage points"
            + (f" and the exact two-sided sign test gives p = {p:.4f}." if p is not None else ".")
        )
        movers = sorted(paired["per_task_delta"].items(), key=lambda kv: kv[1])
        big = [(t, d) for t, d in movers if abs(d) >= 0.4]
        if big:
            R.table(
                ["Task", "Requirement", f"{first} minus {second.replace('the ', '')}"],
                [[t, task_text.get(t, ""), f"{d * 100:+.0f} pts"] for t, d in big],
                [1.6, 10.6, 3.8],
                f"Tasks with the largest per-task differences between {first} and {second} (at least 40 percentage points).",
                font_size=8.5,
            )
    if any(summary.get(k) for k, _, _ in comparisons):
        _paragraphs(R, _c("PAIRED"))

    # ---- 6.4 errors --------------------------------------------------------------------------------------
    R.h2("6.4 Error analysis")
    codes = sorted(
        {c for a in arms for c in H[a]["error_counts"]},
        key=lambda c: -sum(H[a]["error_counts"].get(c, 0) for a in arms),
    )
    if codes:
        R.table(
            ["Error category"] + [f"{NAMES[a]} (of {H[a]['samples']})" for a in arms],
            [
                [c] + [f"{H[a]['error_counts'].get(c, 0)} ({H[a]['error_counts'].get(c, 0) / H[a]['samples'] * 100:.0f}%)" for a in arms]
                for c in codes
            ],
            widths(len(arms), 6.4),
            "Samples containing each error category. A sample can contain several.",
            align_right_from=1,
        )
        if (FIG / "error_categories.png").exists():
            R.figure(FIG / "error_categories.png", 14.0, "Share of samples containing each error category.")
        diag = defaultdict(Counter)
        for r in records:
            if r["category"] == "policy_conflict":
                continue
            for d in r["diagnostics"]:
                stage, _, msg = d.partition(": ")
                if stage in ("validate", "init", "plan", "intent"):
                    diag[r["arm"]][f"{stage}: {msg[:90]}"] += 1
        merged = Counter()
        for a in arms:
            merged.update(diag[a])
        if merged:
            R.table(
                ["Most frequent non-policy diagnostics"] + [NAMES[a] for a in arms],
                [[d] + [diag[a].get(d, 0) for a in arms] for d, _ in merged.most_common(10)],
                widths(len(arms), 9.0),
                "The most frequent validator and intent diagnostics (policy findings are shown in the previous table).",
                font_size=8.5,
                align_right_from=1,
            )
    flags = {a: H[a].get("flag_counts", {}) for a in arms}
    if any(flags.values()):
        R.p(
            "Informational flags (not counted as failures): "
            + "; ".join(f"{NAMES[a]}: " + (", ".join(f"{k} in {v} samples" for k, v in flags[a].items()) or "none") for a in arms)
            + "."
        )
    _paragraphs(R, _c("ERRORS"))

    # ---- 6.5 retrieval -------------------------------------------------------------------------------------
    R.h2("6.5 Retrieval quality and outcome")
    rag = [r for r in records if r["arm"] == "rag" and r["category"] != "policy_conflict" and r.get("retrieval_hit") is not None]
    if rag:
        full = [r for r in rag if r["retrieval_hit"] >= 1.0]
        part = [r for r in rag if r["retrieval_hit"] < 1.0]

        def rate(rs, key):
            return f"{sum(1 for r in rs if r[key]) / len(rs) * 100:.0f}%" if rs else "n/a"

        R.table(
            ["Retrieval", "Samples", "Functional pass", "Overall pass"],
            [
                ["All needed resource docs retrieved (hit = 1)", len(full), _functional(full), rate(full, "overall_pass")],
                ["Some needed docs missing (hit < 1)", len(part), _functional(part), rate(part, "overall_pass")],
            ],
            [7.6, 2.4, 3.0, 3.0],
            "RAG-arm outcomes by whether documentation for every needed resource was retrieved.",
            align_right_from=1,
        )
    _paragraphs(R, _c("RETRIEVAL"))

    # ---- 6.6 category ----------------------------------------------------------------------------------------
    R.h2("6.6 By category and difficulty")
    cats = summary["by_category"]
    diffs = summary["by_difficulty"]
    R.table(
        ["Category"] + [NAMES[a] for a in arms],
        [[g] + [f"{v.get(a, 0) * 100:.0f}%" if a in v else "n/a" for a in arms] for g, v in cats.items()],
        widths(len(arms), 6.4),
        "Overall pass rate by task category.",
        align_right_from=1,
    )
    if (FIG / "by_category.png").exists():
        R.figure(FIG / "by_category.png", 14.0, "Overall pass rate by task category.")
    R.table(
        ["Difficulty"] + [NAMES[a] for a in arms],
        [[f"Level {g}"] + [f"{v.get(a, 0) * 100:.0f}%" if a in v else "n/a" for a in arms] for g, v in diffs.items()],
        widths(len(arms), 6.4),
        "Overall pass rate by difficulty level.",
        align_right_from=1,
    )
    _paragraphs(R, _c("CATEGORY"))

    # ---- 6.7 policy conflict ----------------------------------------------------------------------------------
    conflict = summary.get("policy_conflict_tasks") or {}
    if conflict:
        R.h2("6.7 Requirements that conflict with organisational policy")
        R.table(
            ["Metric"] + [NAMES[a] for a in arms if a in conflict],
            [
                ["Intent pass (did what was asked)"] + [fmt(conflict[a]["intent_pass_rate"]) for a in arms if a in conflict],
                ["OPA violation rate"] + [fmt(conflict[a]["opa_violation_rate"]) for a in arms if a in conflict],
            ],
            widths(len([a for a in arms if a in conflict]), 6.4),
            "The two tasks that explicitly request policy-forbidden configurations.",
            align_right_from=1,
        )
        _paragraphs(R, _c("CONFLICT"))

    _extra_sections(R, H, extra or {})


def _functional(records) -> str:
    if not records:
        return "n/a"
    ok = sum(1 for r in records if r["validate_pass"] and r.get("plan_pass") is not False and r["intent_pass"])
    return f"{ok / len(records) * 100:.0f}%"


def discussion(R, summary, manifest):
    R.h1("7. Discussion")
    text = _c("DISCUSSION")
    if text:
        _paragraphs(R, text)
    else:
        R.p("(Discussion to be completed once results are final.)")


def conclusion(R):
    R.h1("9. Conclusion")
    text = _c("CONCLUSION")
    if text:
        _paragraphs(R, text)
    else:
        R.p("(Conclusion to be completed once results are final.)")


def _extra_sections(R, H, extra):
    """6.8 retrieval ablations and 6.9 near-greedy run, from separate stored runs."""
    ablations = [
        (label, extra[rid]["headline"]["rag"])
        for rid, label in (("abl-topk3", "Top 3 chunks"), ("abl-nocap", "No per-document cap"))
        if extra.get(rid) and "rag" in extra[rid].get("headline", {})
    ]
    if ablations and "rag" in H:
        R.h2("6.8 Retrieval ablations")
        R.p(
            "Two retrieval settings were varied one at a time on the RAG arm, holding everything else fixed: the number "
            "of retrieved chunks (default 8, here 3) and the per-document cap (default 3 chunks per source document, here "
            "removed). The ablation runs use three samples per task rather than five, so pass@1 and pass@3 are the figures "
            "that can be compared across columns. Chunk size was not varied: doing so means rebuilding the index and "
            "re-embedding the corpus, which would overwrite the index the main run used (Section 8)."
        )
        cols = [("Default: 8 chunks, cap 3 (main run)", H["rag"])] + ablations
        rows = [["Samples"] + [str(c[1]["samples"]) for c in cols]]
        for label, key in (
            ("Validate pass", "validate_pass_rate"),
            ("Intent pass", "intent_pass_rate"),
            ("Overall pass", "overall_pass_rate"),
            ("OPA violation rate (of evaluable)", "opa_violation_rate"),
        ):
            rows.append([label] + [fmt(c[1].get(key)) for c in cols])
        rows.append(["pass@1 (overall)"] + [pct(c[1]["pass_at_k_overall"].get("1")) for c in cols])
        rows.append(["pass@3 (overall)"] + [pct(c[1]["pass_at_k_overall"].get("3")) for c in cols])
        rows.append(["Retrieval hit rate"] + [pct(c[1]["retrieval_hit_rate"]) for c in cols])
        R.table(
            ["Metric"] + [c[0] for c in cols],
            rows,
            widths(len(cols), 5.2),
            "RAG arm under different retrieval settings. Proportions show the 95% Wilson interval in brackets.",
            align_right_from=1,
            font_size=9,
        )
        _paragraphs(R, _c("ABLATION"))

    low = extra.get("lowtemp")
    if low and low.get("headline"):
        LH = low["headline"]
        larms = [a for a in ARMS if a in LH]
        R.h2("6.9 Near-greedy run (temperature 0)")
        R.p(
            "To complement the sampled run, all arms were run once per task at temperature 0. This is a near-greedy "
            "setting, not a guarantee of determinism, because hosted models can still vary between calls. With one sample "
            "per task, pass@1 equals the pass rate."
        )
        R.table(
            ["Metric"] + [NAMES[a] for a in larms],
            [["Samples"] + [str(LH[a]["samples"]) for a in larms]]
            + [
                [label] + [fmt(LH[a].get(key)) for a in larms]
                for label, key in (
                    ("Validate pass", "validate_pass_rate"),
                    ("Intent pass", "intent_pass_rate"),
                    ("Functional pass", "functional_pass_rate"),
                    ("Overall pass (pass@1)", "overall_pass_rate"),
                    ("OPA violation rate (of evaluable)", "opa_violation_rate"),
                )
            ],
            widths(len(larms), 6.4),
            "Headline metrics at temperature 0, one sample per task.",
            align_right_from=1,
        )
        _paragraphs(R, _c("LOWTEMP"))
