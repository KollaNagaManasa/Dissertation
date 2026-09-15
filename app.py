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
            "Running in **local** mode: TF-IDF embeddings + in-memory vector store + a stub "
            "LLM (no GCP credentials needed). Generated Terraform will be a placeholder comment "
            "block, not real code. Set RAGIAC_MODE=gcp in .env for real generation."
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

        with st.spinner("Retrieving context..."):
            scored_chunks = pipeline.retriever.retrieve(requirement)

        with st.spinner("Generating Terraform..."):
            hcl = pipeline.generate_baseline(requirement) if use_baseline else pipeline.generate_rag(requirement)

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
    st.subheader("RAG vs. non-RAG baseline")
    st.caption(
        "Runs every prompt in data/eval/prompts.jsonl through both arms and reports the "
        "terraform validate/plan pass rate and OPA policy-violation rate."
    )

    prompts_path = REPO_ROOT / "data" / "eval" / "prompts.jsonl"
    prompts = [json.loads(line) for line in prompts_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    st.write(f"{len(prompts)} prompts loaded from `{prompts_path.relative_to(REPO_ROOT)}`")

    run_plan = st.checkbox("Include `terraform plan`", value=False, key="bench_plan")

    if st.button("Run benchmark"):
        rows = []
        progress = st.progress(0.0)
        total = len(prompts) * 2

        for i, item in enumerate(prompts):
            for arm, use_baseline in (("RAG", False), ("Baseline", True)):
                hcl = (
                    pipeline.generate_baseline(item["requirement"])
                    if use_baseline
                    else pipeline.generate_rag(item["requirement"])
                )
                try:
                    report = pipeline.validate(hcl, run_plan=run_plan, check_opa=True)
                    terraform_status = "PASS" if report.terraform_passed else "FAIL"
                    opa_status = "PASS" if report.policy_passed else "FAIL"
                except FileNotFoundError as e:
                    terraform_status = opa_status = f"skipped ({e})"

                rows.append(
                    {"id": item["id"], "arm": arm, "terraform": terraform_status, "opa": opa_status}
                )
                progress.progress((i * 2 + (1 if arm == "RAG" else 2)) / total)

        st.dataframe(rows, use_container_width=True)


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
