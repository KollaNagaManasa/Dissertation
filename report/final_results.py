"""Chapter 5 of the final report (Results and Discussion). Tables and the numbers in the text are
computed at build time from results/final-01 (the final run), the retrieval configuration runs and
results/main-01 (the earlier run, used for comparison). The interpretive sentences were written after
inspecting those results; if a run is repeated they must be re-checked."""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePath

import template_review_section
import user_study_section
from results_section import FIG, fmt, pct

ROOT = Path(__file__).resolve().parent.parent
ARMS = ("baseline", "conventions", "rag", "templates", "rag_policy")
NAMES = {
    "baseline": "Baseline",
    "conventions": "Conventions in prompt",
    "rag": "RAG",
    "templates": "Simulated internal templates",
    "rag_policy": "RAG + pinned policy",
}
POLICY_DOCS = {"org_best_practices.md", "gcs_bucket_policy.md", "cloud_sql_policy.md", "gke_cluster_policy.md"}
EARLIER_CONFIGS = (
    ("main-01", "Default: 8 chunks, cap 3, chunk 1500"),
    ("abl-topk3", "3 chunks"),
    ("abl-nocap", "No per-document cap"),
    ("abl-chunk800", "Chunk size 800"),
    ("abl-policy-retrieval", "Policy indexed per resource type"),
)
FINAL_CONFIGS = (("abl-final-topk4", "4 chunks"), ("final-01", "8 chunks (final run)"), ("abl-final-topk12", "12 chunks"))


# ---- data ------------------------------------------------------------------------------------------
def load_run(run_id):
    run_dir = ROOT / "results" / run_id
    if not (run_dir / "summary.json").exists():
        return None, None, []
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    lines = (run_dir / "samples.jsonl").read_text(encoding="utf-8").splitlines()
    return summary, manifest, [json.loads(line) for line in lines if line.strip()]


def _headline(records, arm=None):
    return [r for r in records if r["category"] != "policy_conflict" and (arm is None or r["arm"] == arm)]


def _policy_retrieved(r):
    return any(PurePath(x["doc_id"].replace("\\", "/")).name in POLICY_DOCS for x in r.get("retrieved") or [])


def _missing_label(r):
    return "POLICY_MISSING_LABELS" in r["errors"]


def _share(n, d):
    return f"{n} of {d} ({n / d * 100:.0f}%)" if d else "n/a"


CAUSES = (
    ("Missing `environment` label", lambda d: d.startswith("policy:") and "is missing" in d and "labels" in d),
    ("Public exposure", lambda d: d.startswith("policy:") and ("public IP" in d or "allUsers" in d or "0.0.0.0/0" in d)),
    ("BigQuery deletion setting not declared", lambda d: "delete_contents_on_destroy" in d),
    ("Bucket retention not declared", lambda d: d.startswith("policy:") and "has no retention_policy" in d),
    ("Other policy rule", None),
    ("Invalid configuration (init/validate)", lambda d: d.startswith(("init:", "validate:"))),
    ("Intent not met", lambda d: d.startswith("intent:")),
)


def _causes(r):
    """Root causes present in a failing sample, from its diagnostics."""
    found = set()
    for d in r["diagnostics"]:
        matched = False
        for name, test in CAUSES:
            if test and test(d):
                found.add(name)
                matched = True
        if d.startswith("policy:") and not matched:
            found.add("Other policy rule")
    if r.get("plan_pass") is False:
        found.add("Plan error")
    return found


def _node_pool(hcl):
    return re.split(r'resource\s+"google_container_node_pool"', hcl, maxsplit=1)[-1]


def _gke01_three_nodes(r):
    """True when the node pool yields three nodes in total: node_count = 1 per zone on a regional pool
    with no node_locations (asia-south1 has three zones)."""
    pool = _node_pool(r["hcl"])
    return bool(re.search(r"(?<![\w])node_count\s*=\s*1\b", pool)) and "node_locations" not in pool


def _gke01_corrected(records, arm):
    rs = _headline(records, arm)
    n = 0
    for r in rs:
        if r["task_id"] != "gke-01":
            n += r["overall_pass"]
            continue
        other_intent = [f for f in r["intent_failures"] if "node_count" not in f]
        intent = _gke01_three_nodes(r) and not other_intent
        n += bool(r["validate_pass"] and r.get("plan_pass") is not False and intent and r["policy_pass"] is not False)
    return n, len(rs)


def widths(n_cols, first):
    """Column widths in cm for a label column plus n equal columns, filling the WILP text width (7 in)."""
    return [first] + [round((17.4 - first) / n_cols, 2)] * n_cols


def _p(x):
    return "n/a" if x is None else f"{x:.4f}"


# ---- chapter -------------------------------------------------------------------------------------
def results(R, run_id="final-01"):
    summary, manifest, records = load_run(run_id)
    H = summary["headline"]
    arms = [a for a in ARMS if a in H]
    earlier = {rid: load_run(rid) for rid, _ in EARLIER_CONFIGS}
    main_summary, _, main_records = earlier["main-01"]

    R.h1("5. Results and Discussion")
    R.p(
        "This chapter reports the final benchmark run, `final-01` (Sections 5.1 to 5.3), then takes the mid-semester "
        "review's requests in turn: policy retrieval and pinning (5.4), the reviewed internal templates (5.5), the "
        "retrieval configuration experiments (5.6), the detailed failure analysis (5.7) and the user evaluation "
        "(5.10). Results from the earlier run, `main-01`, are used only for comparison and are labelled as such."
    )

    # ---- 5.1 ---------------------------------------------------------------------------------------
    R.h2("5.1 The final run")
    infra = sum(1 for r in records if r.get("generation_error") or r.get("validation_error"))
    R.p(
        f"The final run evaluates {H[arms[0]]['tasks']} headline tasks and 2 policy-conflict tasks under {len(arms)} "
        f"arms with {manifest['samples_per_task']} samples per task per arm ({len(records)} samples), using "
        f"`{manifest['generation_model']}` at temperature {manifest['temperature']}, `terraform plan` enabled and an "
        f"index of {manifest['index_chunks']} chunks. It started on {manifest['started_at'][:10]} and ran in one "
        f"session. " + ("No sample was lost to infrastructure failure, so every sample was scored. " if not infra else f"{infra} samples were lost to infrastructure failure and are not scored. ")
        + "The full settings "
        "are in Appendix D."
    )
    R.p("Four things changed between the earlier run and this one, and they make the two runs' overall pass rates not directly comparable:")
    R.bullets(
        [
            "**All five organisational policies are enforced.** The earlier run was scored against the label and public-access rules only; broad service-account roles, declared retention or deletion protection, and hardcoded secrets are now checked as well (Appendix C).",
            "**The policy is indexed per resource type.** The three resource-specific policy documents (Section 4.3.4) are in the index for every retrieving arm.",
            "**The internal templates and the Cloud SQL conventions were corrected** after the technical review (Section 4.3.7).",
            "**A fifth arm, RAG with pinned policy, was added** (Section 4.3.4).",
        ]
    )

    # ---- 5.2 ---------------------------------------------------------------------------------------
    R.h2("5.2 Headline metrics")
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
    for k in sorted({int(k) for a in arms for k in H[a]["pass_at_k_overall"]}):
        rows.append([f"pass@{k} (overall)"] + [pct(H[a]["pass_at_k_overall"].get(str(k))) for a in arms])
    rows.append(["Retrieval hit rate"] + [pct(H[a]["retrieval_hit_rate"]) if H[a].get("retrieval_hit_rate") is not None else "-" for a in arms])
    R.table(
        ["Metric"] + [NAMES[a] for a in arms],
        rows,
        widths(len(arms), 4.6),
        f"Headline metrics of the final run ({H[arms[0]]['samples']} samples per arm). Proportions show the 95% Wilson interval in brackets.",
        align_right_from=1,
        font_size=8.5,
    )
    if (FIG / f"pass_rates_{run_id}.png").exists():
        R.figure(FIG / f"pass_rates_{run_id}.png", 15.0, "Pass rates by arm in the final run, with 95% confidence intervals.")
    o = {a: H[a]["overall_pass_rate"]["rate"] * 100 for a in arms}
    func = [H[a]["functional_pass_rate"]["rate"] * 100 for a in arms]
    R.p(
        f"**Technical correctness is near ceiling in every arm.** Functional pass rates, which require validate, "
        f"plan and intent to pass, range from {min(func):.1f}% to {max(func):.1f}%, with overlapping intervals. No arm "
        "has more than six functional failures in 165 samples, so this run, like the earlier one, gives no evidence "
        "that retrieval improves technical correctness (RQ1)."
    )
    R.p(
        f"**Policy compliance separates the arms.** Overall pass, which adds the five policy checks, is "
        f"{o['baseline']:.1f}% for the baseline, {o['rag']:.1f}% for RAG, {o['templates']:.1f}% for the simulated "
        f"internal templates, {o['rag_policy']:.1f}% for RAG with pinned policy and {o['conventions']:.1f}% for the "
        f"conventions in the prompt. The baseline's pass@5 is {pct(H['baseline']['pass_at_k_overall'].get('5'))}, "
        "hardly above its pass@1: its failures are systematic omissions, not bad luck on a given sample. RAG rises "
        f"from {o['rag']:.1f}% at pass@1 to {pct(H['rag']['pass_at_k_overall'].get('5'))} at pass@5, so for some "
        "tasks it complies on some samples and not others, which is what one would expect if the outcome depends on "
        "whether policy happened to be retrieved."
    )

    # ---- 5.3 ---------------------------------------------------------------------------------------
    R.h2("5.3 Paired comparisons across tasks")
    comparisons = [
        ("paired_overall_pass", "RAG", "Baseline"),
        ("paired_rag_vs_conventions", "RAG", "Conventions in prompt"),
        ("paired_conventions_vs_templates", "Conventions in prompt", "Simulated internal templates"),
        ("paired_rag_policy_vs_rag", "RAG + pinned policy", "RAG"),
        ("paired_rag_policy_vs_conventions", "RAG + pinned policy", "Conventions in prompt"),
    ]
    R.table(
        ["First arm", "Second arm", "First better", "Second better", "Tied", "Mean difference", "Sign test p"],
        [
            [a, b, summary[k]["rag_better"], summary[k]["baseline_better"], summary[k]["tied"],
             f"{summary[k]['mean_delta_overall_pass'] * 100:+.1f} pts", _p(summary[k]["sign_test_p"])]
            for k, a, b in comparisons
            if summary.get(k)
        ],
        [3.4, 3.4, 1.7, 1.8, 1.4, 2.2, 2.1],
        "Paired comparisons of per-task overall pass rate (33 headline tasks; exact two-sided sign test).",
        align_right_from=2,
        font_size=9,
    )
    task_text = {r["task_id"]: r["requirement"] for r in records}
    movers = sorted(summary["paired_rag_policy_vs_rag"]["per_task_delta"].items(), key=lambda kv: -kv[1])
    big = [(t, d) for t, d in movers if abs(d) >= 0.4]
    if big:
        R.table(
            ["Task", "Requirement", "Pinned minus RAG"],
            [[t, task_text.get(t, ""), f"{d * 100:+.0f} pts"] for t, d in big],
            [1.6, 11.4, 3.0],
            "Tasks on which pinning the policy changed the overall pass rate by at least 40 percentage points.",
            font_size=8.5,
        )
    pr = summary["paired_rag_policy_vs_rag"]
    R.p(
        f"Treating each task as one observation gives the same ordering as the pooled rates. Pinning the policy is "
        f"better than RAG on {pr['rag_better']} of {pr['tasks_compared']} tasks and worse on {pr['baseline_better']} "
        f"(p = {pr['sign_test_p']:.3f}), and it is the largest paired difference in the run. The tasks it fixes are "
        "the Cloud SQL, Cloud Storage and GKE tasks, the resource types for which a policy page exists. RAG remains "
        f"better than the baseline on {summary['paired_overall_pass']['rag_better']} tasks and worse on none. The conventions in "
        f"the prompt are better than pinned policy on {summary['paired_rag_policy_vs_conventions']['baseline_better']} "
        "tasks and worse on none, a difference that is not significant (p = "
        f"{summary['paired_rag_policy_vs_conventions']['sign_test_p']:.2f}); two of them are the BigQuery tasks, for "
        "which there is no policy page to pin (Section 5.7.3). The conventions are better than the "
        f"simulated templates on {summary['paired_conventions_vs_templates']['rag_better']} tasks and worse on none "
        f"(p = {summary['paired_conventions_vs_templates']['sign_test_p']:.3f}), discussed in Section 5.5."
    )

    # ---- 5.4 ---------------------------------------------------------------------------------------
    R.h2("5.4 Retrieving versus pinning organisational policy")
    rag, pinned = _headline(records, "rag"), _headline(records, "rag_policy")
    main_rag = _headline(main_records, "rag")
    got = [r for r in rag if _policy_retrieved(r)]
    not_got = [r for r in rag if not _policy_retrieved(r)]
    main_got = [r for r in main_rag if _policy_retrieved(r)]
    conv = _headline(records, "conventions")
    R.table(
        ["Arm (run)", "Policy in the model's context", "Samples missing a label", "Overall pass"],
        [
            ["RAG, general policy only (earlier run)", _share(len(main_got), len(main_rag)), _share(sum(map(_missing_label, main_rag)), len(main_rag)), pct(main_summary["headline"]["rag"]["overall_pass_rate"]["rate"]) + " *"],
            ["RAG, policy indexed per resource", _share(len(got), len(rag)), _share(sum(map(_missing_label, rag)), len(rag)), pct(H["rag"]["overall_pass_rate"]["rate"])],
            ["RAG + pinned policy", f"{len(pinned)} of {len(pinned)} (100%), pinned", _share(sum(map(_missing_label, pinned)), len(pinned)), pct(H["rag_policy"]["overall_pass_rate"]["rate"])],
            ["Conventions in prompt", f"{len(conv)} of {len(conv)} (100%), pasted", _share(sum(map(_missing_label, conv)), len(conv)), pct(H["conventions"]["overall_pass_rate"]["rate"])],
        ],
        [5.0, 4.2, 3.6, 3.2],
        "How the policy reached the model, and the result. * Scored against two of the five policies, so not comparable with the other rows.",
        font_size=9,
    )
    pins = Counter(tuple(r.get("pinned_policies", [])) for r in pinned)
    with_page = sum(n for k, n in pins.items() if len(k) > 1)
    R.p(
        "**Indexing the policy per resource type made it retrievable.** With one general policy document, the "
        f"policy was among the retrieved chunks in {_share(len(main_got), len(main_rag))} RAG samples in the "
        f"earlier run, from {len({r['task_id'] for r in main_got})} tasks. With the three resource-specific "
        f"documents added, it was retrieved in {_share(len(got), len(rag))}, from "
        f"{len({r['task_id'] for r in got})} tasks. That is the improvement the review asked for, but it did not "
        f"translate into compliance. In the final run, RAG samples that retrieved a policy document passed overall "
        f"in {_share(sum(r['overall_pass'] for r in got), len(got))} cases, against "
        f"{_share(sum(r['overall_pass'] for r in not_got), len(not_got))} for samples that did not, and "
        f"{sum(map(_missing_label, got))} of the samples that retrieved a policy document still left out the "
        "label. (Policy documents are retrieved mainly for the label-bearing resource types, where failing is "
        "possible at all, so the two groups are not like for like. But retrieving the policy clearly did not "
        "guarantee following it.) In the earlier run, every one of the few samples that retrieved the policy "
        "complied with it. The difference is that a retrieved chunk is one passage among eight, often a fragment "
        "of the policy page, presented as reference material."
    )
    R.p(
        "**Pinning the policy made it followed.** The policy-pinning arm supplied the general policy in every "
        f"sample and a resource-specific policy page as well in {_share(with_page, len(pinned))} ("
        + ", ".join(f"`{k[1]}` in {n}" for k, n in sorted(pins.items(), key=lambda kv: -kv[1]) if len(k) > 1)
        + "). Not one of its samples was missing a label, against "
        f"{sum(map(_missing_label, rag))} RAG samples, and its overall pass rate is "
        f"{o['rag_policy'] - o['rag']:.1f} percentage points above RAG's. It reached this with at most two policy "
        "pages per request, instead of every convention document. Table "
        f"{R._table_no + 1} shows where the difference lies."
    )
    cats = summary["by_category"]
    R.table(
        ["Category"] + [NAMES[a] for a in arms],
        [[g] + [f"{v.get(a, 0) * 100:.0f}%" if a in v else "n/a" for a in arms] for g, v in cats.items()],
        widths(len(arms), 3.4),
        "Overall pass rate by task category in the final run.",
        align_right_from=1,
        font_size=9,
    )
    if (FIG / f"by_category_{run_id}.png").exists():
        R.figure(FIG / f"by_category_{run_id}.png", 15.0, "Overall pass rate by task category in the final run.")
    R.p(
        "The categories with no applicable policy, or with policy the model already follows (compute, network, "
        "platform, security, serverless, messaging), pass at 90% or more in every arm. The arms differ in storage, "
        f"database, Kubernetes and data. Pinning lifts database from {cats['database'].get('rag', 0) * 100:.0f}% to "
        f"{cats['database'].get('rag_policy', 0) * 100:.0f}%, storage from {cats['storage'].get('rag', 0) * 100:.0f}% "
        f"to {cats['storage'].get('rag_policy', 0) * 100:.0f}% and Kubernetes from "
        f"{cats['kubernetes'].get('rag', 0) * 100:.0f}% to {cats['kubernetes'].get('rag_policy', 0) * 100:.0f}%. It "
        f"leaves data (BigQuery) at {cats['data'].get('rag_policy', 0) * 100:.0f}%, against "
        f"{cats['data'].get('conventions', 0) * 100:.0f}% for the conventions arm: BigQuery has no policy page of its "
        "own to pin, and the general policy does not name the setting the BigQuery rule checks (Section 5.7.3)."
    )

    # ---- 5.5 ---------------------------------------------------------------------------------------
    R.h2("5.5 Validation with the reviewed internal templates")
    tmpl_fail = [r for r in _headline(records, "templates") if not r["overall_pass"]]
    tcauses = Counter(c for r in tmpl_fail for c in _causes(r))
    intent_tasks = {r["task_id"] for r in tmpl_fail if "Intent not met" in _causes(r)}
    main_H = main_summary["headline"]
    pitr_before = template_review_section._pitr_failures("main-01")
    pitr_after = template_review_section._pitr_failures(run_id)
    tc, tn = _gke01_corrected(records, "templates")
    cc, cn = _gke01_corrected(records, "conventions")
    R.p(
        "The templates arm tests whether the conventions-in-prompt result depends on unusually clean, "
        "hand-written conventions. In the earlier run, scored against two policies, it did not: the templates and "
        f"conventions arms were indistinguishable (overall pass {pct(main_H['templates']['overall_pass_rate']['rate'])} "
        f"against {pct(main_H['conventions']['overall_pass_rate']['rate'])}). In the final run, with the reviewed and "
        f"corrected templates and five policies, the templates arm reaches {o['templates']:.1f}% against "
        f"{o['conventions']:.1f}%, and the conventions are better on "
        f"{summary['paired_conventions_vs_templates']['rag_better']} tasks and worse on none."
    )
    R.p(
        f"The templates arm's {len(tmpl_fail)} failing samples contain: "
        + "; ".join(f"{c.lower()} in {n}" for c, n in tcauses.most_common())
        + ". The bucket-retention and BigQuery failures follow from how the templates state the retention rule, "
        "as a one-line note (\"buckets, cloud sql, bigquery -> need either deletion protection or a documented "
        "retention policy\") without saying which arguments satisfy it, whereas the hand-written conventions show "
        "it in worked examples. The intent failures are not template failures at all: "
        + ("all of them are" if intent_tasks == {"gke-01"} else "most of them are")
        + " on task `gke-01`, where the templates arm built the correct three-node pool and the intent check rejected it "
        f"(Section 5.7.5). With that check corrected, the templates arm passes {_share(tc, tn)} and the conventions "
        f"arm {_share(cc, cn)}, so the gap narrows but remains."
    )
    R.p(
        "**Effect of the review.** The review's most serious finding, point-in-time recovery advised for MySQL "
        "(F1), had caused plan failures on task `sql-02` in the earlier run ("
        + "; ".join(f"{NAMES[a].lower()} {pitr_before[a][1]} of {pitr_before[a][0]}" for a in ("templates", "conventions") if a in pitr_before)
        + "). After the correction, "
        + ("no sample in any arm of the final run failed with that error" if not sum(v[1] for v in pitr_after.values()) else f"{sum(v[1] for v in pitr_after.values())} samples of the final run still failed with that error")
        + ". The conclusion is that messier documentation costs some compliance, mainly where a rule is stated "
        "without showing how to meet it, and that defects in organisational documents pass straight into generated "
        "code, which is why the documents need review as much as the generator does."
    )

    # ---- 5.6 ---------------------------------------------------------------------------------------
    R.h2("5.6 Retrieval configuration experiments")
    cols = []
    for rid, label in EARLIER_CONFIGS:
        s, _, recs = earlier[rid]
        if s and "rag" in s["headline"]:
            cols.append((label, s["headline"]["rag"], _headline(recs, "rag"), rid))
    if cols:
        rows = [["Samples"] + [str(c[1]["samples"]) for c in cols]]
        rows.append(["Overall pass"] + [fmt(c[1]["overall_pass_rate"]) + (" *" if c[3] == "abl-policy-retrieval" else "") for c in cols])
        rows.append(["pass@3 (overall)"] + [pct(c[1]["pass_at_k_overall"].get("3")) for c in cols])
        rows.append(["Retrieval hit rate"] + [pct(c[1]["retrieval_hit_rate"]) for c in cols])
        rows.append(["Policy retrieved"] + [f"{sum(map(_policy_retrieved, c[2])) / len(c[2]) * 100:.0f}%" for c in cols])
        rows.append(["Missing a label"] + [f"{sum(map(_missing_label, c[2])) / len(c[2]) * 100:.0f}%" for c in cols])
        R.table(
            ["Metric (RAG arm)"] + [c[0] for c in cols],
            rows,
            widths(len(cols), 3.4),
            "Retrieval configurations of the RAG arm before the final run, scored against the earlier policy set. * Scored against all five policies, so its overall pass is not comparable with the other columns.",
            align_right_from=1,
            font_size=8.5,
        )
        R.p(
            "None of the generic retrieval settings changed the outcome. Three chunks instead of eight lowered the "
            "hit rate slightly, and removing the per-document cap or halving the chunk size left it unchanged; the "
            "overall pass intervals overlap in every case. In all four, the policy was retrieved in at most 12% of "
            "samples and about one sample in five was missing a label. These settings change how much provider "
            "documentation the model sees, not whether the policy is among it, because the requirement text does "
            "not resemble the policy text however many chunks are taken. Indexing the policy per resource type is "
            "the only setting that changed policy retrieval, tripling it, yet the share of samples missing a "
            f"label hardly moved ({rows[-1][1]} with the default setting, {rows[-1][-1]} with per-resource indexing). "
            "Getting the policy retrieved more often was not enough on its own (Section 5.4)."
        )
    fcols = []
    for rid, label in FINAL_CONFIGS:
        s = summary if rid == run_id else load_run(rid)[0]
        if s and "rag_policy" in s["headline"]:
            fcols.append((label, s["headline"]["rag_policy"]))
    if len(fcols) > 1:
        R.table(
            ["Metric (RAG + pinned policy)"] + [c[0] for c in fcols],
            [["Samples"] + [str(c[1]["samples"]) for c in fcols]]
            + [[label] + [fmt(c[1][key]) for c in fcols] for label, key in (
                ("Functional pass", "functional_pass_rate"),
                ("Overall pass", "overall_pass_rate"),
            )]
            + [["pass@1 (overall)"] + [pct(c[1]["pass_at_k_overall"].get("1")) for c in fcols]]
            + [["pass@3 (overall)"] + [pct(c[1]["pass_at_k_overall"].get("3")) for c in fcols]]
            + [["Retrieval hit rate"] + [pct(c[1]["retrieval_hit_rate"]) for c in fcols]],
            widths(len(fcols), 5.0),
            "The policy-pinning arm with different numbers of retrieved chunks, scored against all five policies.",
            align_right_from=1,
            font_size=9,
        )
        overall = [c[1]["overall_pass_rate"]["rate"] * 100 for c in fcols]
        hits = [c[1]["retrieval_hit_rate"] * 100 for c in fcols]
        R.p(
            f"With the policy pinned, the number of retrieved chunks matters little. Overall pass ranges from "
            f"{min(overall):.1f}% to {max(overall):.1f}% across four, eight and twelve chunks, and the retrieval hit "
            f"rate from {min(hits):.1f}% to {max(hits):.1f}%, with overlapping intervals. Once the policy no longer "
            "has to win a place among the retrieved chunks, retrieval only has to find the provider documentation, "
            "which it does at every setting tried. The default of eight chunks is kept: it is not shown to be "
            "better than four or twelve, and neither alternative is shown to be better than it."
        )
    else:
        R.p("(The final retrieval configuration runs with the policy-pinning arm are not available.)")

    # ---- 5.7 ---------------------------------------------------------------------------------------
    failure_analysis(R, summary, records, main_records, arms, run_id)

    # ---- 5.8 ---------------------------------------------------------------------------------------
    R.h2("5.8 By difficulty")
    diffs = summary["by_difficulty"]
    R.table(
        ["Difficulty"] + [NAMES[a] for a in arms],
        [[f"Level {g}"] + [f"{v.get(a, 0) * 100:.0f}%" if a in v else "n/a" for a in arms] for g, v in diffs.items()],
        widths(len(arms), 3.4),
        "Overall pass rate by difficulty level in the final run.",
        align_right_from=1,
        font_size=9,
    )
    R.p(
        f"Difficulty does not order the results: RAG passes {diffs['1'].get('rag', 0) * 100:.0f}% of level 1, "
        f"{diffs['2'].get('rag', 0) * 100:.0f}% of level 2 and {diffs['3'].get('rag', 0) * 100:.0f}% of level 3 "
        "samples. As in the earlier run, most level-2 tasks are storage, database and Kubernetes tasks, where the "
        "policy applies, so difficulty and resource type are confounded in this task set and the category view of "
        "Section 5.4 is the more informative one."
    )

    # ---- 5.9 ---------------------------------------------------------------------------------------
    earlier_checks(R)

    # ---- 5.10 --------------------------------------------------------------------------------------
    user_study_section.user_evaluation(R, heading="5.10")
    R.p(
        "**A caveat from the failure analysis.** Task success in the user evaluation was scored with the benchmark's "
        "intent checks, including the `gke-01` check that rejects the correct three-node configuration "
        "(Section 5.7.5). The session records do not keep the submitted configurations, so the `gke-01` results "
        "cannot be re-scored. A participant who wrote the correct per-zone node count would have been scored as "
        "failing, so the 4 of 4 against 0 of 4 on that task may partly reflect the checker and not the condition."
    )

    discussion(R, summary, records)


def failure_analysis(R, summary, records, main_records, arms, run_id):
    H = summary["headline"]
    R.h2("5.7 Detailed failure analysis")
    R.p(
        "This section reviews every failing sample of the final run by root cause (Section 4.3.6): first where "
        "the failures are, then six cases, each examined with the configurations that produced it."
    )
    R.h3("5.7.1 Where the failures are")
    R.p(f"Table {R._table_no + 1} counts the failing samples of each arm by cause. A sample can have more than one.")
    fails = {a: [r for r in _headline(records, a) if not r["overall_pass"]] for a in arms}
    counts = {a: Counter(c for r in fails[a] for c in _causes(r)) for a in arms}
    order = [c for c, _ in CAUSES] + ["Plan error"]
    order = [c for c in order if any(counts[a].get(c) for a in arms)]
    R.table(
        ["Root cause"] + [NAMES[a] for a in arms],
        [["Failing samples"] + [len(fails[a]) for a in arms]] + [[c] + [counts[a].get(c, 0) for a in arms] for c in order],
        widths(len(arms), 4.6),
        f"Failing samples by root cause in the final run ({H[arms[0]]['samples']} samples per arm).",
        align_right_from=1,
        font_size=9,
    )
    if (FIG / f"error_categories_{run_id}.png").exists():
        R.figure(FIG / f"error_categories_{run_id}.png", 14.0, "Share of samples containing each error category in the final run.")
    R.p(
        "Almost every failure is a policy failure, and four root causes account for nearly all of them (Cases 1 "
        "to 4). Cases 5 and 6 cover the policy-conflict tasks and the few technical errors."
    )

    # 5.7.2 labels
    R.h3("5.7.2 Case 1: unstated policy that did not reach the model")
    rag_lab = [r for r in _headline(records, "rag") if _missing_label(r)]
    by_cat = Counter(r["category"] for r in rag_lab)
    sql_rag = [r for r in _headline(records, "rag") if r["category"] == "database"]
    R.p(
        f"The most common RAG failure is a missing `environment` label ({len(rag_lab)} samples: "
        + ", ".join(f"{n} {c}" for c, n in by_cat.most_common())
        + "). The requirement never mentions labels, so the model labels a resource only if the policy is in its "
        "context and it treats the policy as binding. Cloud SQL is the clearest case: the database category passes "
        f"at {summary['by_category']['database'].get('rag', 0) * 100:.0f}% for RAG and "
        f"{summary['by_category']['database'].get('rag_policy', 0) * 100:.0f}% with pinned policy. The Cloud SQL "
        "provider pages are long and detailed and fill the retrieved context, so even the resource-specific policy "
        f"page was retrieved in only {_share(sum(map(_policy_retrieved, sql_rag)), len(sql_rag))} RAG samples of the "
        "database tasks; when it is pinned, every sample carries the label. This is the failure the "
        "review's first request was about, and pinning removes it."
    )

    # 5.7.3 bigquery
    R.h3("5.7.3 Case 2: a policy that does not say what is enforced")
    bq = defaultdict(lambda: [0, 0])
    for r in records:
        if r["task_id"] in ("bq-01", "bq-02"):
            bq[r["arm"]][0] += 1
            bq[r["arm"]][1] += any("delete_contents_on_destroy" in d for d in r["diagnostics"])
    R.p(
        "The two BigQuery tasks fail in most samples of every arm except the conventions arm. Samples failing "
        "the BigQuery retention rule: "
        + "; ".join(f"{NAMES[a].lower()} {bq[a][1]} of {bq[a][0]}" for a in arms if a in bq)
        + ". The policy text says that BigQuery datasets \"must have deletion protection or an explicit retention "
        "policy\". The Rego rule that enforces it checks one specific argument, `delete_contents_on_destroy`, "
        "which no organisational document mentions. Task `bq-01` asks for tables that expire after 30 days, and "
        "the configurations set `default_table_expiration_ms` accordingly, which a reader could fairly take as an "
        "explicit retention policy: there, the model arguably followed the policy as written and the check "
        "rejected it. Task `bq-02` asks for no retention at all, and nothing in the policy text tells the model "
        "which setting would satisfy the rule."
    )
    R.p(
        "The conventions-arm samples that pass set `delete_contents_on_destroy = false` explicitly. That arm sees "
        "all four convention documents, whose examples for other resources declare their deletion settings "
        "explicitly, but the data do not show which part of the context prompted it. This is the information-gap "
        "failure described by Jouini [4]: the requirement cannot be met reliably from the text the model is given. "
        "The remedy is in the policy, not the generator: state the enforced argument in the policy text, or "
        "generate the text and the Rego rule from one source (Section 6.2)."
    )

    # 5.7.4 PITR
    R.h3("5.7.4 Case 3: a defect in organisational documentation copied into code")
    pitr = template_review_section._pitr_failures("main-01")
    R.p(
        "In the earlier run, task `sql-02` (a highly available MySQL instance with backups) failed `terraform "
        "plan` with the error *\"point_in_time_recovery_enabled is only available for the following [POSTGRES "
        "SQLSERVER]\"* in "
        + "; ".join(f"{NAMES[a].lower()} {pitr[a][1]} of {pitr[a][0]}" for a in ("templates", "conventions", "rag", "baseline") if a in pitr)
        + " samples. Both the internal templates and the hand-written conventions advised point-in-time recovery "
        "for every engine. The model makes this mistake from its own knowledge too, as the baseline shows, but "
        "with the flawed advice as its only guidance it made it in almost every sample. RAG retrieved the same flawed conventions page and "
        "also the provider page, whose MySQL example uses `binary_log_enabled`, and it followed the provider page "
        "every time. The review found the defect (F1, Section 4.3.7), both documents were corrected, and in the "
        "final run no sample fails this way. A model will reproduce a defect in the only guidance it has, so "
        "organisational documents are part of the system's attack and error surface, as Section 2.5 argued for "
        "poisoned documents."
    )

    # 5.7.5 gke-01
    R.h3("5.7.5 Case 4: an intent check that rejected correct answers")
    pattern = Counter()
    for r in records:
        if r["task_id"] == "gke-01":
            pattern[(r["arm"], _gke01_three_nodes(r), r["intent_pass"])] += 1
    R.p(
        "Task `gke-01` asks for \"a regional GKE cluster in asia-south1 ... plus a separately managed node pool of 3 "
        "e2-standard-4 nodes\". On a regional node pool, `node_count` is the number of nodes *per zone*, and "
        "asia-south1 has three zones, so three nodes in total means `node_count = 1` (or `node_count = 3` with "
        "`node_locations` restricted to one zone). The task's intent check, written by the author, requires "
        "`node_count = 3`, which on a regional pool creates nine nodes. Reviewing the failures showed that the "
        "check has the answer backwards:"
    )
    R.table(
        ["Arm", "Pools with 3 nodes in total (correct)", "Pools with 9 nodes", "Passed the intent check"],
        [
            [NAMES[a],
             sum(n for (arm, three, _), n in pattern.items() if arm == a and three),
             sum(n for (arm, three, _), n in pattern.items() if arm == a and not three),
             sum(n for (arm, _, ok), n in pattern.items() if arm == a and ok)]
            for a in arms
        ],
        [4.6, 4.2, 3.4, 3.8],
        "Node-pool sizes generated for `gke-01`, and which passed the intent check.",
        align_right_from=1,
        font_size=9,
    )
    corrected = {a: _gke01_corrected(records, a) for a in arms}
    R.p(
        "Every sample that passed built nine nodes, and every sample that built the requested three failed. The "
        "templates arm built three nodes in all five samples, because the reviewed GKE template now states that "
        "the count is per zone (finding F5); the other arms mostly set `node_count = 3`. Correcting the "
        "check after the fact would change the pre-specified result, so the headline figures keep the check as it "
        "was, and Table "
        f"{R._table_no + 1} gives the effect of correcting it."
    )
    R.table(
        ["Overall pass"] + [NAMES[a] for a in arms],
        [
            ["As specified (headline)"] + [pct(H[a]["overall_pass_rate"]["rate"]) for a in arms],
            ["With the `gke-01` check corrected"] + [pct(corrected[a][0] / corrected[a][1]) for a in arms],
        ],
        widths(len(arms), 4.6),
        "Sensitivity of the overall pass rate to the `gke-01` intent check.",
        align_right_from=1,
        font_size=9,
    )
    R.p(
        "The correction moves each arm by three percentage points at most and does not change the order of the arms "
        "that matter for the conclusions: pinned policy remains well above RAG and the conventions remain highest. "
        "It does bring the templates arm level with pinned policy. More importantly, it shows that an automated "
        "check written by hand can be wrong in a way no arm's pass rate reveals: the error was only visible because "
        "one arm consistently gave a different answer. The same applies to any organisation's policy checks."
    )

    # 5.7.6 conflict
    R.h3("5.7.6 Case 5: requests that conflict with policy")
    conflict = summary.get("policy_conflict_tasks") or {}
    if conflict:
        R.table(
            ["Metric"] + [NAMES[a] for a in arms if a in conflict],
            [
                ["Intent pass (did what was asked)"] + [fmt(conflict[a]["intent_pass_rate"]) for a in arms if a in conflict],
                ["OPA violation rate"] + [fmt(conflict[a]["opa_violation_rate"]) for a in arms if a in conflict],
            ],
            widths(len([a for a in arms if a in conflict]), 4.6),
            "The two tasks that explicitly request policy-forbidden configurations (a public website bucket and a Cloud SQL instance with a public IP).",
            align_right_from=1,
            font_size=9,
        )
    R.p(
        "When the requirement itself asks for what policy forbids, every arm does what was asked and violates "
        "policy, including the policy-pinning arm, whose prompt says the policy applies unless the requirement "
        "explicitly asks otherwise. No arm refused or warned. This is the intended behaviour of a generator that "
        "serves explicit requests, and it is why the validation layer is needed: the policy check is the only "
        "thing that stops a conflicting request from reaching review unflagged."
    )

    # 5.7.7 technical + taxonomy
    R.h3("5.7.7 Case 6: residual technical errors, and the published taxonomy")
    tech = defaultdict(Counter)
    for a in arms:
        for r in fails[a]:
            for d in r["diagnostics"]:
                stage, _, msg = d.partition(": ")
                if stage in ("init", "validate") or (stage == "plan" and r.get("plan_pass") is False):
                    tech[a][f"{stage}: {msg[:70]}"] += 1
    listed = Counter()
    for a in arms:
        listed.update(tech[a])
    if listed:
        R.table(
            ["Technical diagnostic"] + [NAMES[a] for a in arms],
            [[d] + [tech[a].get(d, 0) for a in arms] for d, _ in listed.most_common(8)],
            widths(len(arms), 6.6),
            "Technical (non-policy, non-intent) diagnostics among the failing samples of the final run.",
            align_right_from=1,
            font_size=8.5,
        )
    R.p(
        "Technical errors are rare: a handful of samples across 825 headline samples fail `terraform init` or "
        "`validate`, for example for an unclosed template interpolation, an undeclared reference or an argument "
        "the provider does not support, and no sample failed `terraform plan` once the point-in-time-recovery "
        "defect was corrected. The counts are too small to compare arms."
    )
    R.p(
        "Mapped onto the taxonomy of Nekrasov et al. [3], the technical categories correspond directly (HCL syntax "
        "to their syntax errors; argument, block, attribute and reference errors to their schema errors), but two "
        "mappings are not clean, and both are informative. Plan errors have no counterpart, because they catch "
        "provider-API constraints that a validate-time taxonomy cannot see. Policy violations have no counterpart "
        "either: the published taxonomy has no organisational-policy dimension, although that is where nearly "
        "every failure in this benchmark falls. The failure analysis adds a further distinction the taxonomy does "
        "not make, between failures of the generator and failures of the documents and checks it is evaluated "
        "against (Cases 2 to 4)."
    )


def earlier_checks(R):
    R.h2("5.9 Further checks from the earlier run")
    R.p(
        "Three further checks were made in the earlier phase and are summarised here; their full results are in the "
        "mid-semester report. They were not repeated in the final run."
    )
    low = load_run("lowtemp")[0]
    if low:
        LH = low["headline"]
        R.p(
            "**Near-greedy run.** All arms of the earlier run were repeated once per task at temperature 0. The "
            f"ordering and the size of the gaps were the same as at temperature 0.8 (overall pass: baseline "
            f"{pct(LH['baseline']['overall_pass_rate']['rate'])}, RAG {pct(LH['rag']['overall_pass_rate']['rate'])}, "
            f"conventions {pct(LH['conventions']['overall_pass_rate']['rate'])}), so the findings are not an artefact "
            "of sampling."
        )
    R.p(
        "**Verifier-feedback refinement.** Validator diagnostics from ten failures of the earlier run, covering "
        "every distinct combination of error codes, were fed back to the model for one retry, following [4]. Nine "
        "of ten were fully resolved. In two of the ten, the retry dropped the required provider version constraint "
        "while fixing the reported issue, because that constraint was not part of what the loop validated. "
        "A feedback loop can only protect what it checks."
    )
    R.p(
        "**Poisoning robustness.** One adversarial document posing as an urgent policy update, instructing public "
        "read access on every bucket, was added to a copy of the knowledge base, following [7]. It was retrieved for "
        "five of six storage tasks in each of two runs, but in twelve generations the model never added the public "
        "grant. It did follow the poisoned default region on tasks that left the region unstated. An explicit "
        "requirement outweighed a retrieved document on the security-critical point; this is a small probe, not a "
        "robustness guarantee."
    )


def discussion(R, summary, records):
    H = summary["headline"]
    o = {a: H[a]["overall_pass_rate"]["rate"] * 100 for a in H}
    R.h2("5.11 Discussion")
    R.p(
        "**Answers to the research questions.** For **RQ1**, retrieval has no measurable effect on technical "
        "correctness, because every arm is near ceiling on this task set. For **RQ2**, retrieval improves policy "
        f"compliance over the baseline ({o['baseline']:.1f}% to {o['rag']:.1f}% overall pass), but most of the gain "
        "available comes from the policy reaching the model in a form it treats as binding: pinning it gives "
        f"{o['rag_policy']:.1f}% and pasting all conventions {o['conventions']:.1f}%. For **RQ3**, nearly all errors "
        "are omissions of unstated policy; their root causes are policy that was not in the context, policy text "
        "that does not say what is enforced, a defect in the documents, and in one case the check itself. For "
        "**RQ4**, retrieval finds the provider documentation reliably at every setting tried (hit rate about 97%), "
        "generic settings do not change policy retrieval, per-resource indexing triples it, and with the policy "
        "pinned the amount of retrieved context hardly matters. For **RQ5**, engineers were faster with the "
        "assistant, rated its usability as moderate and trusted it above neutral, but the study cannot show a gain "
        "in task success."
    )
    R.p(
        "**Why pinning works and retrieval does not.** Policy is cross-cutting: it applies to a request without "
        "resembling it. Similarity search is the wrong tool for selecting it, and even a retrieved policy chunk is "
        "presented as one reference passage among several. Selecting policy by rule from what was retrieved, and "
        "presenting it as mandatory, solves both problems while keeping the prompt short. The conventions-in-prompt "
        "arm remains slightly better on this task set because it gives the model every convention and every "
        "worked example, which on the BigQuery tasks led it to declare the deletion setting explicitly, though "
        "the data do not show which part of the context did so. That advantage holds only while the conventions are short enough "
        "to paste whole; pinning is the design that scales."
    )
    R.p(
        "**What an organisation should take from this.** The quality of the written policy matters as much as how "
        "it is delivered. A rule that names the setting it checks is followed; a rule written as a principle is "
        "interpreted, and the interpretation may not be the one the check enforces. Organisational documents need "
        "the same review as code, because the model copies their defects. And automated policy checks remain "
        "necessary in every configuration tested, both because no arm reaches 100% and because every arm builds "
        "what it is asked for even when the request breaks policy."
    )
    R.p(
        "**Threats to validity.** These are listed in Section 4.3.11. The ones that matter most for this chapter "
        "are that the policy-pinning arm was designed after seeing the earlier run's results, on the same task set; "
        "that the conventions, templates and policies were written by the author; that the failure analysis found "
        "one defective intent check, which means others could exist; and that the user evaluation's manual condition "
        "was not controlled for AI use. With one model, 33 headline tasks and five comparisons, the category-level "
        "and paired results are best read as consistent directions with stated uncertainty."
    )
