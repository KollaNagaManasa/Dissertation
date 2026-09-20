"""Streamlit demo UI for the RAG-powered IaC assistant.

Run with: streamlit run app.py

Wraps the same Pipeline used by scripts/ask.py and scripts/benchmark.py — this
file adds no new pipeline logic, just a browser front-end over it.
"""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ragiac.config import get_settings  # noqa: E402
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


def render_ask_tab(pipeline) -> None:
    st.subheader("Ask for infrastructure")

    default_requirement = (
        "A GCS bucket for storing invoice PDFs, versioned, with a 30 day lifecycle rule to "
        "move objects to Nearline storage."
    )
    requirement = st.text_area("Natural-language requirement", value=default_requirement, height=100)

    col1, col2, col3 = st.columns([1, 1, 2])
    use_baseline = col1.checkbox("Baseline (no retrieval)", value=False)
    run_validation = col2.checkbox("Run validation", value=True)
    run_plan = col3.checkbox("Include `terraform plan` (needs GCP credentials)", value=False)

    if st.button("Generate", type="primary"):
        if not requirement.strip():
            st.warning("Enter a requirement first.")
            return

        scored_chunks = []
        with st.spinner("Generating Terraform..."):
            if use_baseline:
                hcl = pipeline.generate_baseline(requirement)
            else:
                generation = pipeline.generate_rag_detailed(requirement)  # retrieves once, reuses it
                hcl, scored_chunks = generation.hcl, generation.retrieved

        left, right = st.columns([1, 1])

        with left:
            st.markdown("**Retrieved context** (empty for the baseline arm)" if use_baseline else "**Retrieved context**")
            if use_baseline:
                st.caption("Baseline generation skips retrieval by design — nothing to show here.")
            elif not scored_chunks:
                st.caption("No matches — try rebuilding the index from the sidebar.")
            else:
                for sc in scored_chunks:
                    with st.expander(f"{sc.chunk.doc_id}  ·  score={sc.score:.3f}"):
                        st.text(sc.chunk.text)

        with right:
            st.markdown("**Generated Terraform**")
            st.code(hcl, language="hcl")

        if run_validation:
            st.markdown("---")
            st.markdown("**Validation**")
            try:
                with st.spinner("Running terraform + OPA..."):
                    report = pipeline.validate(hcl, run_plan=run_plan, check_opa=True)
            except FileNotFoundError as e:
                st.error(str(e))
            else:
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


def main() -> None:
    st.title("☁️ RAG-Powered Assistant for Infrastructure as Code Generation")
    st.caption("BITS Pilani M.Tech dissertation prototype · target cloud: Google Cloud Platform (asia-south1)")

    pipeline = get_pipeline()
    render_sidebar(pipeline)

    tab1, tab2 = st.tabs(["Ask", "Benchmark"])
    with tab1:
        render_ask_tab(pipeline)
    with tab2:
        render_benchmark_tab(pipeline)


if __name__ == "__main__":
    main()
