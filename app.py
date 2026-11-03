"""Streamlit demo UI for the RAG-powered IaC assistant.

Run with: streamlit run app.py

Wraps the same Pipeline used by scripts/ask.py and scripts/benchmark.py — this
file adds no new pipeline logic, just a browser front-end over it.
"""

import json
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ragiac.config import get_settings  # noqa: E402
from ragiac.evaluation.intent import check_intent  # noqa: E402
from ragiac.evaluation.user_study import (  # noqa: E402
    EXPERIENCE_LEVELS,
    SUS_ITEMS,
    TRUST_ITEMS,
    SessionRecord,
    append_record,
    assign_conditions,
    read_records,
)
from ragiac.generation.verifier_feedback import refine  # noqa: E402
from ragiac.pipeline import build_pipeline  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="RAG-Powered IaC Assistant", page_icon="☁️", layout="wide")


@st.cache_resource(show_spinner="Loading pipeline...")
def get_pipeline():
    return build_pipeline(get_settings())


def render_sidebar(pipeline) -> None:
    settings = pipeline.settings
    st.sidebar.header("Configuration")
    st.sidebar.markdown(f"**Mode:** `{settings.ragiac_mode}`")
    st.sidebar.markdown(f"**Region (storage/embeddings):** `{settings.google_cloud_region}`")
    st.sidebar.markdown(f"**Generation location:** `{settings.vertex_generation_location}`")
    if settings.is_gcp_mode:
        st.sidebar.markdown(f"**LLM:** `{settings.vertex_generation_model}`")
        st.sidebar.markdown(f"**Embedder:** `{settings.vertex_embedding_model}`")
    else:
        st.sidebar.info(
            "Running in **local** mode: TF-IDF embeddings + in-memory vector store + a rule-based "
            "template generator, not an LLM (no GCP credentials needed). Output is limited to a few "
            "fixed resource templates. Set RAGIAC_MODE=gcp in .env for real generation."
        )

    n_indexed = len(pipeline.vector_store) if hasattr(pipeline.vector_store, "__len__") else "n/a"
    st.sidebar.markdown(f"**Chunks indexed:** {n_indexed}")

    if st.sidebar.button("Rebuild index from data/knowledge_base", use_container_width=True):
        with st.spinner("Ingesting knowledge base..."):
            n = pipeline.ingest()
        st.sidebar.success(f"Ingested {n} chunks.")
        st.rerun()

    st.sidebar.divider()
    st.sidebar.caption(
        "Validation tooling: "
        + ("terraform ✅" if _binary_available(settings.terraform_binary) else "terraform ❌ not on PATH")
    )
    st.sidebar.caption(
        "conftest/OPA: "
        + ("✅" if _binary_available(settings.conftest_binary) else "❌ not on PATH")
    )


def _binary_available(binary: str) -> bool:
    import shutil

    return shutil.which(binary) is not None


ARM_LABELS = {
    "rag": "RAG (retrieval)",
    "baseline": "Baseline (no retrieval)",
    "conventions": "Conventions (hand-written docs, in prompt)",
    "templates": "Templates (messier internal templates, in prompt)",
}


def render_ask_tab(pipeline) -> None:
    st.subheader("Ask for infrastructure")

    default_requirement = (
        "A GCS bucket for storing invoice PDFs, versioned, with a 30 day lifecycle rule to "
        "move objects to Nearline storage."
    )
    requirement = st.text_area("Natural-language requirement", value=default_requirement, height=100)

    arm = st.radio("Arm", list(ARM_LABELS), format_func=lambda a: ARM_LABELS[a], horizontal=True)
    col1, col2, col3 = st.columns([1, 1, 1.4])
    run_validation = col1.checkbox("Run validation", value=True)
    run_plan = col2.checkbox("Include `terraform plan`", value=False, help="Needs GCP credentials")
    use_feedback = col3.checkbox(
        "Retry with verifier feedback if invalid", value=False,
        help="One retry round: feeds terraform/OPA diagnostics back to the model (arXiv:2607.20478)",
    )

    if st.button("Generate", type="primary"):
        if not requirement.strip():
            st.warning("Enter a requirement first.")
            return

        scored_chunks = []
        with st.spinner("Generating Terraform..."):
            if arm == "rag":
                generation = pipeline.generate_rag_detailed(requirement)  # retrieves once, reuses it
                hcl, scored_chunks = generation.hcl, generation.retrieved
            elif arm == "baseline":
                hcl = pipeline.generate_baseline(requirement)
            elif arm == "conventions":
                hcl = pipeline.generate_conventions(requirement)
            else:
                hcl = pipeline.generate_templates(requirement)

        left, right = st.columns([1, 1])

        with left:
            st.markdown("**Retrieved context**" if arm == "rag" else "**Retrieved context** (n/a for this arm)")
            if arm != "rag":
                st.caption(f"The {ARM_LABELS[arm]} arm does not retrieve — nothing to show here.")
            elif not scored_chunks:
                st.caption("No matches — try rebuilding the index from the sidebar.")
            else:
                for sc in scored_chunks:
                    with st.expander(f"{sc.chunk.doc_id}  ·  score={sc.score:.3f}"):
                        st.text(sc.chunk.text)

        with right:
            st.markdown("**Generated Terraform**")
            st.code(hcl, language="hcl")

        report = None
        if use_feedback:
            st.markdown("---")
            st.markdown("**Verifier feedback**")
            try:
                with st.spinner("Validating, and retrying once if needed..."):
                    result = refine(hcl, requirement, pipeline.rag_generator.llm, pipeline.settings, run_plan=run_plan)
            except FileNotFoundError as e:
                st.error(str(e))
            else:
                if result.attempts == 1:
                    st.success("First attempt already passed validation — no retry needed.")
                    report = result.first_attempt_report
                else:
                    st.warning("First attempt failed validation; retried once with diagnostics fed back.")
                    st.code(result.first_attempt_report.summary(), language="text")
                    st.markdown("**Fixed Terraform**")
                    st.code(result.hcl, language="hcl")
                    st.markdown("Passed after retry: " + ("✅" if result.passed else "❌ still failing"))
                    report = result.final_report
        elif run_validation:
            st.markdown("---")
            st.markdown("**Validation**")
            try:
                with st.spinner("Running terraform + OPA..."):
                    report = pipeline.validate(hcl, run_plan=run_plan, check_opa=True)
            except FileNotFoundError as e:
                st.error(str(e))

        # Shown for both paths above, reusing whichever report was already computed rather than
        # validating a second time (verifier feedback already ran terraform/OPA once or twice).
        if run_validation and report is not None:
            v1, v2 = st.columns(2)
            with v1:
                if report.terraform_passed:
                    st.success("terraform: PASS")
                else:
                    st.error("terraform: FAIL")
                for r in report.terraform_results:
                    st.text(f"  {r.stage}: {'ok' if r.passed else 'FAILED'}")
                    if not r.passed:
                        st.code(r.stderr or r.stdout, language="text")
            with v2:
                if report.policy_passed:
                    st.success("opa: PASS")
                else:
                    st.error("opa: FAIL")
                if report.policy_result:
                    for v in report.policy_result.violations:
                        st.text(f"  violation: {v}")


def render_benchmark_tab(pipeline) -> None:
    st.subheader("Benchmark runs: RAG vs. non-RAG baseline")
    st.caption(
        "Viewer for runs written by `py scripts/benchmark.py` (results/<run_id>/). Runs take long "
        "and hit API quotas, so they are launched from the CLI, not from this page."
    )

    results_dir = REPO_ROOT / pipeline.settings.results_dir
    runs = sorted((p for p in results_dir.glob("*/samples.jsonl")), reverse=True) if results_dir.exists() else []
    if not runs:
        st.info("No runs yet. Try: `py scripts/benchmark.py --only gcs-01,sql-01 --samples 2`")
        return

    run_dir = st.selectbox("Run", [p.parent for p in runs], format_func=lambda p: p.name)
    manifest_path, summary_path = run_dir / "manifest.json", run_dir / "summary.json"
    records = [json.loads(line) for line in (run_dir / "samples.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        st.caption(
            f"{m['generation_model']} @ T={m['temperature']} · top_k={m['top_k']} · "
            f"{m['samples_per_task']} sample(s)/task · plan run: {m['terraform_plan_run']} · "
            f"commit {(m['git_commit'] or 'n/a')[:8]} · {m['label'] or 'no label'}"
        )

    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        headline = summary.get("headline", {})
        rows = []
        for label, key in [
            ("validate pass", "validate_pass_rate"),
            ("plan pass", "plan_pass_rate"),
            ("OPA violation rate", "opa_violation_rate"),
            ("intent pass", "intent_pass_rate"),
            ("functional pass", "functional_pass_rate"),
            ("overall pass", "overall_pass_rate"),
        ]:
            row = {"metric": label}
            for arm, metrics in headline.items():
                cell = metrics.get(key)
                row[arm] = "n/a" if not cell or cell["rate"] is None else f"{cell['rate'] * 100:.0f}%  (n={cell['n']})"
            rows.append(row)
        st.dataframe(rows, use_container_width=True, hide_index=True)

        errors = {arm: metrics["error_counts"] for arm, metrics in headline.items()}
        codes = sorted({c for counts in errors.values() for c in counts})
        if codes:
            st.markdown("**Error categories** (samples containing each)")
            st.dataframe(
                [{"category": c, **{arm: errors[arm].get(c, 0) for arm in errors}} for c in codes],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.warning("No summary.json for this run yet (run still in progress?).")

    st.markdown("**Samples**")
    st.dataframe(
        [
            {
                "task": r["task_id"],
                "arm": r["arm"],
                "sample": r["sample_idx"],
                "overall": "PASS" if r["overall_pass"] else "fail",
                "validate": r["validate_pass"],
                "policy": r["policy_pass"] if r["policy_evaluated"] else "n/a",
                "intent": r["intent_pass"],
                "errors": ", ".join(r["errors"]),
            }
            for r in records
        ],
        use_container_width=True,
        hide_index=True,
    )

    chosen = st.selectbox("Inspect a sample", [f"{r['task_id']} / {r['arm']} / #{r['sample_idx']}" for r in records])
    record = next(r for r in records if f"{r['task_id']} / {r['arm']} / #{r['sample_idx']}" == chosen)
    st.write(record["requirement"])
    st.code(record["hcl"] or "(no output)", language="hcl")
    for line in record["diagnostics"] + record["intent_failures"] + record["policy_violations"]:
        st.text(line)


# Four tasks spanning difficulty 1-3, per the proposed design (sections_c.py 6.2.1). Same four for
# every participant, matched for difficulty rather than drawn at random, so sessions are comparable.
STUDY_TASK_IDS = ["gcs-01", "net-03", "sql-03", "gke-01"]

INTERVIEW_QUESTIONS = [
    "What, if anything, made you trust the assistant's output?",
    "What, if anything, made you distrust or want to double-check the assistant's output?",
    "Was there a moment you caught a mistake in its output, or missed one? What happened?",
    "How did using the assistant compare to writing Terraform yourself for these tasks?",
    "Would you use this assistant for real work? Why or why not?",
]

STUDY_SESSIONS_PATH = REPO_ROOT / "results" / "user_study" / "sessions.jsonl"


def _load_study_tasks() -> list[dict]:
    by_id = {}
    with (REPO_ROOT / "data" / "eval" / "gcp_tasks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["id"] in STUDY_TASK_IDS:
                by_id[d["id"]] = d
    return [by_id[tid] for tid in STUDY_TASK_IDS]


def _reset_study_state() -> None:
    for key in list(st.session_state):
        if key.startswith("study_"):
            del st.session_state[key]


def render_user_study_tab(pipeline) -> None:
    st.subheader("User study: usability and developer trust")
    st.caption(
        "For peers taking part in the proposed evaluation (Section 6.2.1 of the report). Each "
        f"participant does {len(STUDY_TASK_IDS)} tasks, two with the assistant and two without, in a "
        f"rotating order, then two short surveys and five questions. Results are written to "
        f"`{STUDY_SESSIONS_PATH.relative_to(REPO_ROOT)}`; nothing leaves this machine."
    )

    if "study_participant" not in st.session_state:
        st.markdown("**Start a session**")
        pid = st.text_input("Your participant ID (e.g. your initials)")
        exp = st.radio(
            "Terraform experience", list(EXPERIENCE_LEVELS),
            format_func=lambda e: {"under_1y": "Under 1 year", "2y_plus": "2+ years"}[e],
        )
        if st.button("Start", type="primary", disabled=not pid.strip()):
            existing = read_records(STUDY_SESSIONS_PATH)
            participant_index = len({r.participant_id for r in existing})
            st.session_state.study_participant = {"id": pid.strip(), "experience": exp}
            st.session_state.study_schedule = assign_conditions(participant_index, len(STUDY_TASK_IDS))
            st.session_state.study_task_idx = 0
            st.session_state.study_pending = []
            st.session_state.study_stage = "task"
            st.rerun()
        return

    participant = st.session_state.study_participant
    schedule = st.session_state.study_schedule
    tasks = _load_study_tasks()
    idx = st.session_state.study_task_idx
    stage = st.session_state.study_stage

    st.success(f"Participant **{participant['id']}** ({participant['experience']}) — task {min(idx + 1, len(tasks))} of {len(tasks)}")
    if st.button("Abandon this session (discard, start over)"):
        _reset_study_state()
        st.rerun()

    if stage == "task" and idx < len(tasks):
        task = tasks[idx]
        condition = schedule[idx]
        st.markdown(f"### Task {idx + 1} — condition: **{condition}**")
        st.write(task["requirement"])

        if "study_task_start" not in st.session_state:
            st.session_state.study_task_start = time.monotonic()

        if condition == "assistant":
            # The text_area's value lives in st.session_state[f"text_{idx}"] once the widget has
            # rendered once; passing `value=` again on a later rerun is silently ignored by
            # Streamlit, so the generated HCL must be written directly into that key instead.
            if st.button("Generate with the assistant"):
                st.session_state[f"text_{idx}"] = pipeline.generate_rag(task["requirement"])
            final_hcl = st.text_area(
                "Generated Terraform — edit if needed, then submit this as your final answer",
                height=220, key=f"text_{idx}",
            )
        else:
            st.caption("Write this yourself (using provider documentation and search as you normally would) — no assistant for this task.")
            final_hcl = st.text_area("Your Terraform", height=220, key=f"text_{idx}")

        edit_count = st.number_input("How many times did you revise this before submitting?", min_value=0, value=0, key=f"edits_{idx}")

        if st.button("Submit task", type="primary", disabled=not final_hcl.strip()):
            elapsed = time.monotonic() - st.session_state.study_task_start
            try:
                report = pipeline.validate(final_hcl, run_plan=False, check_opa=True)
                success = report.overall_passed and check_intent(final_hcl, task.get("intent")).passed
            except FileNotFoundError:
                success = False
            st.session_state.study_pending.append(
                {
                    "task_id": task["id"], "condition": condition, "success": success,
                    "time_s": round(elapsed, 1), "edit_count": int(edit_count),
                }
            )
            del st.session_state.study_task_start
            done = [p["condition"] for p in st.session_state.study_pending]
            if done.count(condition) == 2:
                st.session_state.study_stage = f"trust_{condition}"
            else:
                st.session_state.study_task_idx += 1
            st.rerun()
        return

    if stage.startswith("trust_"):
        condition = stage.split("_", 1)[1]
        st.markdown(f"### Quick survey: after the **{condition}** tasks")
        sus_responses = None
        if condition == "assistant":
            st.write("**System Usability Scale** (1 = strongly disagree, 5 = strongly agree)")
            sus_responses = [st.slider(item, 1, 5, 3, key=f"sus_{i}") for i, item in enumerate(SUS_ITEMS)]
        st.write("**Trust in automation**, for the tasks you just did (1 = not at all, 7 = extremely)")
        trust_responses = [st.slider(item, 1, 7, 4, key=f"trust_{condition}_{i}") for i, item in enumerate(TRUST_ITEMS)]
        if st.button("Continue", type="primary"):
            for p in reversed(st.session_state.study_pending):
                if p["condition"] == condition:
                    p["trust_responses"] = trust_responses
                    p["sus_responses"] = sus_responses
                    break
            if idx + 1 == len(tasks):
                st.session_state.study_stage = "interview"
            else:
                st.session_state.study_task_idx += 1
                st.session_state.study_stage = "task"
            st.rerun()
        return

    if stage == "interview":
        st.markdown("### A few questions")
        notes = [st.text_area(q, key=f"interview_{i}") for i, q in enumerate(INTERVIEW_QUESTIONS)]
        if st.button("Finish and save", type="primary"):
            STUDY_SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
            combined_notes = "\n".join(f"Q: {q}\nA: {a}" for q, a in zip(INTERVIEW_QUESTIONS, notes))
            for i, p in enumerate(st.session_state.study_pending):
                append_record(
                    STUDY_SESSIONS_PATH,
                    SessionRecord(
                        participant_id=participant["id"],
                        experience=participant["experience"],
                        task_id=p["task_id"],
                        condition=p["condition"],
                        success=p["success"],
                        time_s=p["time_s"],
                        edit_count=p["edit_count"],
                        sus_responses=p.get("sus_responses"),
                        trust_responses=p.get("trust_responses"),
                        interview_notes=combined_notes if i == len(st.session_state.study_pending) - 1 else "",
                    ),
                )
            st.success("Saved — thank you!")
            _reset_study_state()

    st.divider()
    with st.expander("Researcher view: sessions saved so far"):
        saved = read_records(STUDY_SESSIONS_PATH)
        if not saved:
            st.caption("No sessions saved yet.")
        else:
            participants = sorted({r.participant_id for r in saved})
            st.write(f"{len(participants)} participant(s), {len(saved)} session row(s).")
            st.dataframe(
                [
                    {
                        "participant": r.participant_id, "experience": r.experience, "task": r.task_id,
                        "condition": r.condition, "success": r.success, "time_s": r.time_s,
                        "edits": r.edit_count, "has_sus": r.sus_responses is not None,
                        "has_trust": r.trust_responses is not None,
                    }
                    for r in saved
                ],
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "For the scored summary (SUS, trust, paired comparisons) once enough sessions are in, run: "
                "`py -c \"from pathlib import Path; from ragiac.evaluation.user_study import "
                "read_records, render_report, Participant; r = read_records(Path('results/user_study/"
                "sessions.jsonl')); p = list({x.participant_id: Participant(x.participant_id, "
                "x.experience) for x in r}.values()); print(render_report(p, r))\"`"
            )


def main() -> None:
    st.title("☁️ RAG-Powered Assistant for Infrastructure as Code Generation")
    st.caption("BITS Pilani M.Tech dissertation prototype · target cloud: Google Cloud Platform (asia-south1)")

    pipeline = get_pipeline()
    render_sidebar(pipeline)

    tab1, tab2, tab3 = st.tabs(["Ask", "Benchmark", "User study"])
    with tab1:
        render_ask_tab(pipeline)
    with tab2:
        render_benchmark_tab(pipeline)
    with tab3:
        render_user_study_tab(pipeline)


if __name__ == "__main__":
    main()
