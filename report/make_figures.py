"""Generates report figures into report/figures/.

Usage: py report/make_figures.py [run_id]
The architecture diagram is static; result charts are drawn from results/<run_id>/summary.json.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = Path(__file__).resolve().parent / "figures"
COLORS = {"baseline": "#8c8c8c", "conventions": "#c98a1a", "rag": "#1f5fa8"}
LABELS = {"baseline": "Baseline (no retrieval)", "conventions": "Conventions in prompt", "rag": "RAG"}


def _box(ax, x, y, w, h, text, fc="#eaf1fb", ec="#1f5fa8", fontsize=8.5, dashed=False):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06", fc=fc, ec=ec, lw=1.3,
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, wrap=True)
    return (x, y, w, h)


def _arrow(ax, a, b, style="-|>", color="#333333", ls="-", rad=0.0):
    ax.add_patch(
        FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=11, lw=1.2, color=color, linestyle=ls,
                        connectionstyle=f"arc3,rad={rad}")
    )


def architecture() -> Path:
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    ax.set_xlim(0, 10.5)
    ax.set_ylim(0, 6.6)
    ax.axis("off")

    ax.text(0.05, 6.35, "Offline: knowledge-base construction", fontsize=10, fontweight="bold", color="#1f5fa8")
    k = [
        _box(ax, 0.05, 5.15, 2.2, 0.9, "Public google-provider docs\n(v8.3.0, 47 pages)\n+ org conventions", fc="#f4f4f4", ec="#555"),
        _box(ax, 2.75, 5.15, 2.2, 0.9, "Markdown-aware chunker\nHCL kept whole,\nheading-path prefix"),
        _box(ax, 5.45, 5.15, 2.2, 0.9, "Vertex AI\ntext-embedding-005\n(document task type)"),
        _box(ax, 8.15, 5.15, 2.3, 0.9, "Vector index\n1,034 chunks\n(exact cosine search)"),
    ]
    for a, b in zip(k, k[1:]):
        _arrow(ax, (a[0] + a[2], a[1] + a[3] / 2), (b[0], b[1] + b[3] / 2))

    ax.text(0.05, 4.7, "Online: generation (two arms)", fontsize=10, fontweight="bold", color="#1f5fa8")
    req = _box(ax, 0.05, 3.55, 1.9, 0.85, "Natural-language\nrequirement", fc="#f4f4f4", ec="#555")
    ret = _box(ax, 2.4, 3.55, 2.2, 0.85, "Retriever\ntop-8 chunks, <=3 per doc\n(query task type)")
    pro = _box(ax, 5.05, 3.55, 2.1, 0.85, "Prompt builder\ncontext + requirement\n+ target provider ~> 8.0")
    llm = _box(ax, 7.6, 3.55, 2.85, 0.85, "Gemini 3.8 Flash (Vertex AI)\ntemperature 0.8, retried on 429", fc="#fff3d6", ec="#b7791f")
    _arrow(ax, (req[0] + req[2], 3.975), (ret[0], 3.975))
    _arrow(ax, (ret[0] + ret[2], 3.975), (pro[0], 3.975))
    _arrow(ax, (pro[0] + pro[2], 3.975), (llm[0], 3.975))
    _arrow(ax, (9.3, 5.15), (3.5, 4.4), color="#1f5fa8", ls="--", rad=0.0)
    ax.text(6.3, 4.85, "similarity search", fontsize=8, color="#1f5fa8", rotation=-9)
    ax.text(3.5, 3.2, "RAG arm", fontsize=8, color="#1f5fa8", ha="center", style="italic")

    base = _box(ax, 2.4, 2.55, 4.75, 0.5, "Baseline arm: identical prompt and model, retrieval skipped", fc="#f4f4f4", ec="#777", dashed=True, fontsize=8)
    _arrow(ax, (1.0, 3.55), (2.4, 2.8), color="#777", ls="--", rad=0.2)
    _arrow(ax, (7.15, 2.8), (8.6, 3.55), color="#777", ls="--", rad=0.2)

    ax.text(0.05, 1.95, "Validation and evaluation (identical for both arms; flows right to left)", fontsize=10, fontweight="bold", color="#1f5fa8")
    green = dict(fc="#e8f5e9", ec="#2e7d32", fontsize=7.6)
    hcl = _box(ax, 8.6, 0.55, 1.85, 1.0, "Generated\nTerraform (HCL)", fc="#f4f4f4", ec="#555", fontsize=8.5)
    v1 = _box(ax, 6.45, 0.55, 1.85, 1.0, "terraform init,\nvalidate, plan\n(read-only)", **green)
    v2 = _box(ax, 4.3, 0.55, 1.85, 1.0, "OPA / conftest\norg policy:\nlabels, public access", **green)
    v3 = _box(ax, 2.15, 0.55, 1.85, 1.0, "Functional-intent\nchecks: did it build\nwhat was asked?", **green)
    rec = _box(ax, 0.0, 0.55, 1.85, 1.0, "Error taxonomy +\nper-sample record\n+ run manifest", fc="#f4f4f4", ec="#555", fontsize=7.6)
    _arrow(ax, (9.9, 3.55), (9.9, 1.55), color="#b7791f")
    for left, right in ((v1, hcl), (v2, v1), (v3, v2), (rec, v3)):
        _arrow(ax, (right[0], 1.05), (left[0] + left[2], 1.05))

    path = FIG_DIR / "architecture.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def _summary(run_id: str) -> dict | None:
    p = ROOT / "results" / run_id / "summary.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def pass_rates(summary: dict) -> Path:
    metrics = [
        ("validate pass_rate", "validate_pass_rate", "Validates\n(init+validate)"),
        ("intent", "intent_pass_rate", "Builds what\nwas asked"),
        ("functional", "functional_pass_rate", "Functional\n(validate+plan\n+intent)"),
        ("overall", "overall_pass_rate", "Overall\n(+ org policy)"),
    ]
    arms = [a for a in ("baseline", "conventions", "rag") if a in summary["headline"]]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    width = 0.8 / max(len(arms), 1)
    for i, arm in enumerate(arms):
        vals, lo, hi = [], [], []
        for _, key, _ in metrics:
            m = summary["headline"][arm][key]
            vals.append(m["rate"] * 100)
            lo.append(m["rate"] * 100 - m["ci95"][0] * 100)
            hi.append(m["ci95"][1] * 100 - m["rate"] * 100)
        xs = [j + (i - (len(arms) - 1) / 2) * width for j in range(len(metrics))]
        ax_bars = ax.bar(xs, vals, width, yerr=[lo, hi], capsize=3, color=COLORS[arm], label=LABELS[arm])
        for rect, v in zip(ax_bars, vals):
            ax.text(rect.get_x() + rect.get_width() / 2, 2, f"{v:.0f}%", ha="center", va="bottom", color="white", fontsize=8, fontweight="bold")
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels([m[2] for m in metrics], fontsize=8.5)
    ax.set_ylabel("Pass rate (%)")
    ax.set_ylim(0, 105)
    ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(arms))
    ax.spines[["top", "right"]].set_visible(False)
    path = FIG_DIR / "pass_rates.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def error_categories(summary: dict) -> Path | None:
    arms = [a for a in ("baseline", "conventions", "rag") if a in summary["headline"]]
    codes = sorted({c for a in arms for c in summary["headline"][a]["error_counts"]})
    if not codes:
        return None
    totals = {a: summary["headline"][a]["samples"] for a in arms}
    order = sorted(codes, key=lambda c: -sum(summary["headline"][a]["error_counts"].get(c, 0) for a in arms))[:10]
    fig, ax = plt.subplots(figsize=(8, 0.55 * len(order) + 1.2))
    height = 0.8 / max(len(arms), 1)
    for i, arm in enumerate(arms):
        vals = [summary["headline"][arm]["error_counts"].get(c, 0) / totals[arm] * 100 for c in order]
        ys = [j + (i - (len(arms) - 1) / 2) * height for j in range(len(order))]
        ax.barh(ys, vals, height, color=COLORS[arm], label=LABELS[arm])
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Share of samples containing the error (%)")
    ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(arms))
    ax.spines[["top", "right"]].set_visible(False)
    path = FIG_DIR / "error_categories.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def by_category(summary: dict) -> Path:
    arms = [a for a in ("baseline", "conventions", "rag") if a in summary["headline"]]
    groups = list(summary["by_category"])
    fig, ax = plt.subplots(figsize=(8.5, 4))
    width = 0.8 / max(len(arms), 1)
    for i, arm in enumerate(arms):
        vals = [summary["by_category"][g].get(arm, 0) * 100 for g in groups]
        xs = [j + (i - (len(arms) - 1) / 2) * width for j in range(len(groups))]
        ax.bar(xs, vals, width, color=COLORS[arm], label=LABELS[arm])
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Overall pass rate (%)")
    ax.set_ylim(0, 105)
    ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(arms))
    ax.spines[["top", "right"]].set_visible(False)
    path = FIG_DIR / "by_category.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    print("wrote", architecture())
    run_id = sys.argv[1] if len(sys.argv) > 1 else "main-01"
    summary = _summary(run_id)
    if summary and summary.get("headline"):
        print("wrote", pass_rates(summary))
        print("wrote", error_categories(summary))
        print("wrote", by_category(summary))
    else:
        print(f"no summary for {run_id} yet - result charts skipped")


if __name__ == "__main__":
    main()
