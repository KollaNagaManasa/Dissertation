"""Draws the UML diagrams for the report into report/figures/.\n\nEvery class, method, field and message shown here was checked against the code under src/ragiac; if\nthe code changes, re-check the diagrams.\n\nUsage: py report/make_uml.py\n"""

from pathlib import Path

from matplotlib.patches import Rectangle
from uml import (GREY, INK, SOFT, TINT, actor, arrow, artifact, bar, canvas, class_box, component, diamond, final,
                 initial, line, node3d, note, rbox, rect, save, text, usecase)

FIG_DIR = Path(__file__).resolve().parent / "figures"
FIG_DIR.mkdir(exist_ok=True)
INC = "«include»"


# ---------------------------------------------------------------------------------------------------
def use_case() -> Path:
    W, H = 7.0, 5.75
    fig, ax = canvas(W, H)
    rect(ax, 1.3, 0.15, 4.65, 5.45, fill="white", lw=1.1)
    text(ax, 1.42, 5.44, "RAG-IaC assistant", size=8.5, bold=True, ha="left")

    dev = actor(ax, 0.62, 3.75, "Developer")
    res = actor(ax, 0.62, 1.05, "Researcher")

    cw, ch = 1.95, 0.6
    xa, xb = 2.45, 4.85
    u1 = usecase(ax, xa, 4.85, cw, ch, "Request Terraform\nfor a requirement")
    u2 = usecase(ax, xa, 3.85, cw, ch, "Review validation\nreport")
    u4 = usecase(ax, xa, 2.5, cw, ch, "Run benchmark\n(three arms)")
    u3 = usecase(ax, xa, 1.55, cw, ch, "Build knowledge-\nbase index")
    u5 = usecase(ax, xa, 0.65, cw, ch, "Summarise and\ncompare arms")
    u6 = usecase(ax, xb, 4.95, cw, ch, "Retrieve documentation\ncontext")
    u7 = usecase(ax, xb, 4.15, cw, ch, "Generate Terraform\nwith the LLM")
    u8 = usecase(ax, xb, 3.35, cw, ch, "Validate: terraform\nand policy checks")
    u9 = usecase(ax, xb, 2.5, cw, ch, "Check functional\nintent")
    u10 = usecase(ax, xb, 1.3, cw, ch, "Re-run samples lost to\ninfrastructure failure")

    for a, u in ((dev, u1), (dev, u2), (res, u3), (res, u4), (res, u5)):
        line(ax, [(a.cx + 0.14, a.y + 0.35), (u.x, u.cy)], lw=0.8)

    inc = dict(kind="open", dashed=True, size=6.2)
    arrow(ax, [(u1.R()[0], u1.cy + 0.1), (u6.L()[0], u6.cy - 0.02)], label=INC, label_at=(3.63, 4.93), label_off=(0, 0.08), **inc)
    arrow(ax, [(u1.R()[0], u1.cy - 0.03), (u7.L()[0], u7.cy + 0.03)], label=INC, label_at=(3.63, 4.5), label_off=(0, 0.08), **inc)
    arrow(ax, [(u1.R()[0] - 0.1, u1.cy - 0.2), (u8.L()[0] + 0.04, u8.cy + 0.12)], **inc)
    arrow(ax, [(u4.R()[0] - 0.05, u4.cy + 0.15), (u7.L()[0] + 0.05, u7.cy - 0.16)], **inc)
    arrow(ax, [(u4.R()[0], u4.cy + 0.08), (u8.L()[0] + 0.02, u8.cy - 0.1)], **inc)
    arrow(ax, [(u4.R()[0], u4.cy), (u9.L()[0], u9.cy)], label=INC, label_at=(3.63, 2.5), label_off=(0, -0.1), **inc)
    arrow(ax, [(u10.L()[0] + 0.02, u10.cy + 0.08), (u4.R()[0] - 0.22, u4.y + 0.03)], label="«extend»", label_at=(3.5, 1.72), label_off=(0.05, 0), **inc)

    def system(cx, cy, name):
        b = rect(ax, cx - 0.44, cy - 0.27, 0.88, 0.54, fill=SOFT)
        text(ax, cx, cy + 0.1, "«system»", size=6, color=GREY)
        text(ax, cx, cy - 0.08, name, size=7, bold=True)
        return b

    vx = system(6.5, 4.55, "Vertex AI")
    tf = system(6.5, 3.45, "Terraform")
    cf = system(6.5, 2.45, "Conftest")
    line(ax, [(u6.R()[0], u6.cy), (vx.x, vx.cy + 0.12)], lw=0.8)
    line(ax, [(u7.R()[0], u7.cy), (vx.x, vx.cy - 0.1)], lw=0.8)
    line(ax, [(u8.R()[0] - 0.1, u8.cy + 0.06), (tf.x, tf.cy)], lw=0.8)
    line(ax, [(u8.R()[0] - 0.12, u8.cy - 0.1), (cf.x, cf.cy + 0.06)], lw=0.8)
    path = FIG_DIR / "uml_use_case.png"
    save(fig, path)
    return path


# ---------------------------------------------------------------------------------------------------
def component_diagram() -> Path:
    W, H = 7.0, 6.35
    fig, ax = canvas(W, H)
    ui = component(ax, 0.2, 5.3, 1.85, 0.85, "Streamlit UI", ["app.py", "ask tab, results viewer"])
    cli = component(ax, 2.45, 5.3, 2.15, 0.85, "Command-line scripts", ["ask, ingest, benchmark", "fetch_provider_docs"])
    ev = component(ax, 5.0, 5.3, 1.85, 0.85, "Evaluation", ["runner, intent, taxonomy", "metrics, summary"])
    component(ax, 1.3, 4.15, 4.4, 0.75, "Pipeline (facade)", ["ingest()  generate_rag()  generate_baseline()", "generate_conventions()  validate()"])
    component(ax, 0.2, 2.5, 1.5, 1.25, "Ingestion", ["loader", "chunker (Markdown-aware)", "provider_docs"])
    ret = component(ax, 1.95, 2.5, 1.5, 1.25, "Retrieval", ["Retriever", "top-k + per-document", "cap"])
    gen = component(ax, 3.7, 2.5, 1.65, 1.25, "Generation", ["RagGenerator", "BaselineGenerator", "ConventionsGenerator", "LLM clients"])
    component(ax, 5.55, 2.5, 1.3, 1.25, "Validation", ["terraform_validator", "opa_validator", "ValidationReport"])
    component(ax, 0.5, 1.3, 1.7, 0.85, "Embeddings", ["VertexEmbedder", "LocalTfidfEmbedder"])
    component(ax, 2.55, 1.25, 1.85, 0.95, "Vector store", ["InMemoryVectorStore", "VertexVectorSearchStore", "(implemented, not provisioned)"])

    def ext(x, w, stereo, name, sub):
        b = rect(ax, x, 0.1, w, 0.75, fill="white")
        text(ax, x + w / 2, 0.72, f"«{stereo}»", size=6, color=GREY)
        text(ax, x + w / 2, 0.55, name, size=7.3, bold=True)
        text(ax, x + w / 2, 0.32, sub, size=6.3)
        return b

    ext(0.2, 1.95, "external", "Vertex AI", "text-embedding-005, Gemini")
    ext(2.35, 1.7, "storage", "Local files", "data/, results/")
    ext(4.2, 1.3, "external", "Terraform CLI", "+ provider plugin")
    ext(5.65, 1.2, "external", "Conftest", "+ Rego policies")

    d = dict(kind="open", dashed=True, size=6.5)
    arrow(ax, [(ui.B(0.5)[0], 5.3), (ui.B(0.5)[0], 5.1), (2.1, 5.1), (2.1, 4.9)], **d)
    arrow(ax, [(3.5, 5.3), (3.5, 4.9)], **d)
    arrow(ax, [(cli.R()[0], 5.85), (ev.x, 5.85)], **d)
    arrow(ax, [(6.4, 5.3), (6.4, 4.52), (5.7, 4.52)], **d)
    arrow(ax, [(1.7, 4.15), (1.7, 3.95), (0.95, 3.95), (0.95, 3.75)], **d)
    arrow(ax, [(2.7, 4.15), (2.7, 3.75)], **d)
    arrow(ax, [(4.5, 4.15), (4.5, 3.75)], **d)
    arrow(ax, [(5.3, 4.15), (5.3, 3.95), (6.2, 3.95), (6.2, 3.75)], **d)
    arrow(ax, [(gen.x, 3.1), (ret.R()[0], 3.1)], label="«use»", label_off=(0, 0.1), **d)
    arrow(ax, [(1.95, 2.5), (1.95, 2.3), (1.35, 2.3), (1.35, 2.15)], **d)
    arrow(ax, [(2.9, 2.5), (2.9, 2.3), (3.5, 2.3), (3.5, 2.2)], **d)
    arrow(ax, [(0.85, 2.5), (0.85, 2.15)], **d)
    arrow(ax, [(1.35, 1.3), (1.35, 0.85)], **d)
    arrow(ax, [(3.2, 1.25), (3.2, 0.85)], **d)
    arrow(ax, [(4.65, 2.5), (4.65, 1.05), (1.85, 1.05), (1.85, 0.85)], **d)  # generation -> Vertex AI (Gemini)
    arrow(ax, [(5.7, 2.5), (5.7, 1.6), (5.1, 1.6), (5.1, 0.85)], **d)
    arrow(ax, [(6.4, 2.5), (6.4, 0.85)], **d)
    path = FIG_DIR / "uml_components.png"
    save(fig, path)
    return path


# ---------------------------------------------------------------------------------------------------
def class_pipeline() -> Path:
    W, H = 7.0, 5.5
    fig, ax = canvas(W, H)
    pl = class_box(ax, 0.1, 5.4, 2.35, "Pipeline", "dataclass",
                   ["settings", "embedder", "vector_store", "retriever", "rag_generator", "baseline_generator", "conventions_generator"],
                   ["ingest()", "generate_rag(requirement)", "generate_rag_detailed(requirement)", "generate_baseline(requirement)",
                    "generate_conventions(requirement)", "validate(hcl, run_plan, check_opa)"], fs=6.6)
    gx, gw = 2.95, 1.8
    bg = class_box(ax, gx, 5.4, gw, "BaselineGenerator", "dataclass", ["llm"], ["generate(requirement)"])
    cg = class_box(ax, gx, 4.5, gw, "ConventionsGenerator", "dataclass", ["llm", "conventions_text"], ["generate(requirement)"])
    rg = class_box(ax, gx, 3.35, gw, "RagGenerator", "dataclass", ["retriever", "llm"], ["generate_detailed(requirement)", "generate(requirement)"], fs=6.6)
    rt = class_box(ax, gx, 1.95, gw, "Retriever", "dataclass", [], [])
    gn = class_box(ax, 0.1, 2.5, 1.95, "Generation", "dataclass, frozen", ["hcl", "retrieved"], [])
    lx, lw = 5.3, 1.4
    llm = class_box(ax, lx, 4.35, lw, "LLM", "Protocol", [], ["generate(system, user)"], italic_name=True, fs=6.6)
    vl = class_box(ax, lx, 3.05, lw, "VertexLLM", None, [], ["generate(system, user)"], fs=6.6)
    lt = class_box(ax, lx, 2.05, lw, "LocalTemplateLLM", None, [], ["generate(system, user)"], fs=6.6)

    # Pipeline aggregates the three generators (bus at x=2.7)
    for g in (bg, cg, rg):
        y = g.T()[1] - 0.2
        arrow(ax, [(pl.R()[0], y), (g.x, y)], kind="open", tail="diamond")
    # every generator holds an llm (bus at x=5.05, into the LLM protocol)
    ys = [g.T()[1] - 0.14 for g in (bg, cg, rg)]
    for g, y in zip((bg, cg, rg), ys):
        line(ax, [(g.R()[0], y), (5.05, y)], lw=0.8)
    line(ax, [(5.05, ys[0]), (5.05, ys[2])], lw=0.8)
    arrow(ax, [(5.05, llm.T()[1] - 0.3), (llm.x, llm.T()[1] - 0.3)], kind="open")
    line(ax, [(5.05, llm.T()[1] - 0.3), (5.05, ys[0])], lw=0.8)
    text(ax, 4.98, 5.02, "llm", size=6.3, italic=True, ha="right")
    # realisation: implementers -> LLM protocol
    arrow(ax, [(vl.T()[0], vl.T()[1]), (vl.T()[0], llm.B()[1])], kind="triangle", dashed=True)
    arrow(ax, [(lt.R()[0], lt.cy), (6.85, lt.cy), (6.85, llm.cy), (llm.R()[0], llm.cy)], kind="triangle", dashed=True)
    # RagGenerator -> Retriever (association) and -> Generation (creates)
    arrow(ax, [(rg.B()[0], rg.y), (rg.B()[0], rt.T()[1])], kind="open", label="retriever", label_off=(0.32, 0))
    arrow(ax, [(rg.x, rg.y + 0.3), (2.3, rg.y + 0.3), (2.3, gn.y + 0.15), (gn.R()[0], gn.y + 0.15)], kind="open", dashed=True,
          label="«create»", label_at=(2.3, 2.85), label_off=(-0.02, 0.0))
    note(ax, 0.1, 0.15, 6.75, 0.62,
         "Pipeline is assembled by build_pipeline(settings). build_llm() chooses VertexLLM in gcp mode and LocalTemplateLLM in local mode;\n"
         "all three generators share one LLM and differ only in the context they supply (retrieved chunks, all convention documents, or none).", size=6.4)
    path = FIG_DIR / "uml_class_pipeline.png"
    save(fig, path)
    return path


def class_retrieval() -> Path:
    W, H = 7.3, 5.5
    fig, ax = canvas(W, H)
    lx, cx_, rx, cw = 0.3, 2.75, 5.0, 2.0
    emb = class_box(ax, lx, 5.4, cw, "Embedder", "Protocol", [], ["embed(texts)"], italic_name=True)
    ve = class_box(ax, lx, 4.3, cw, "VertexEmbedder", None, [], ["embed(texts)", "embed_query(text)"])
    lt = class_box(ax, lx, 3.2, cw, "LocalTfidfEmbedder", None, [], ["fit(corpus)", "embed(texts)", "save(path)", "load(path)"])
    vs = class_box(ax, rx, 5.4, cw, "VectorStore", "Protocol", [], ["upsert(chunks, vectors)", "search(vector, top_k)"], italic_name=True)
    im = class_box(ax, rx, 4.25, cw, "InMemoryVectorStore", None, [], ["upsert(chunks, vectors)", "search(vector, top_k)", "clear()", "save()", "load()"])
    vv = class_box(ax, rx, 2.85, cw, "VertexVectorSearchStore", None, [], ["upsert(chunks, vectors)", "search(vector, top_k)"])
    rt = class_box(ax, cx_, 5.3, 1.8, "Retriever", "dataclass", ["embedder", "vector_store", "top_k", "max_per_doc"], ["retrieve(query)", "assemble_context(query)"])
    sc = class_box(ax, cx_, 3.15, 1.8, "ScoredChunk", "dataclass, frozen", ["chunk", "score"], [])
    ch = class_box(ax, cx_, 2.05, 1.8, "Chunk", "dataclass, frozen", ["chunk_id", "doc_id", "source", "text"], [])

    # realisation (dashed, hollow triangle)
    arrow(ax, [(ve.T()[0], ve.T()[1]), (ve.T()[0], emb.B()[1])], kind="triangle", dashed=True)
    arrow(ax, [(lt.x, lt.cy), (0.14, lt.cy), (0.14, emb.cy), (emb.x, emb.cy)], kind="triangle", dashed=True)
    arrow(ax, [(im.T()[0], im.T()[1]), (im.T()[0], vs.B()[1])], kind="triangle", dashed=True)
    arrow(ax, [(vv.R()[0], vv.cy), (7.15, vv.cy), (7.15, vs.cy), (vs.R()[0], vs.cy)], kind="triangle", dashed=True)
    # Retriever holds an Embedder and a VectorStore (roles are the attributes shown in the box)
    arrow(ax, [(rt.x, 5.1), (emb.R()[0], 5.1)], kind="open")
    arrow(ax, [(rt.R()[0], 5.1), (vs.x, 5.1)], kind="open")
    # results
    arrow(ax, [(rt.B()[0], rt.y), (rt.B()[0], sc.T()[1])], kind="open", dashed=True, label="«returns»", label_off=(-0.4, 0.0))
    arrow(ax, [(vs.x, 4.85), (4.78, 4.85), (4.78, sc.cy), (sc.R()[0], sc.cy)], kind="open", dashed=True, label="«returns»", label_at=(4.78, 3.55), label_off=(-0.05, 0), ha="right")
    arrow(ax, [(sc.B()[0], sc.y), (sc.B()[0], ch.T()[1])], kind="open", tail="diamond_filled", label="1", label_off=(0.1, 0.0))
    note(ax, 0.3, 0.15, 6.85, 0.62,
         "Retriever embeds the query (embed_query when the embedder has it, otherwise embed), asks the store for top_k x 5 candidates, then keeps\n"
         "at most max_per_doc chunks per source document until top_k are chosen. Any Embedder or VectorStore can be substituted.", size=6.4)
    path = FIG_DIR / "uml_class_retrieval.png"
    save(fig, path)
    return path


def class_validation() -> Path:
    W, H = 7.0, 5.3
    fig, ax = canvas(W, H)
    vr = class_box(ax, 2.35, 5.2, 2.3, "ValidationReport", "dataclass, frozen", ["terraform_results", "policy_result"],
                   ["terraform_passed", "policy_passed", "overall_passed", "summary()"])
    tr = class_box(ax, 0.1, 3.4, 2.0, "TerraformResult", "dataclass, frozen", ["passed", "stage", "stdout", "stderr"], [])
    ir = class_box(ax, 2.6, 3.4, 1.8, "IntentResult", "dataclass, frozen", ["passed", "failures"], [])
    pr = class_box(ax, 4.9, 3.4, 2.0, "PolicyResult", "dataclass, frozen", ["passed", "violations", "raw_stdout", "raw_stderr", "evaluated"], [])
    cl = class_box(ax, 2.35, 1.75, 2.3, "Classification", "dataclass, frozen", ["errors", "flags", "raw_summaries", "deprecation_warnings"], [])

    by = vr.y - 0.28  # horizontal run below the report box
    arrow(ax, [(vr.x + 0.35, vr.y), (vr.x + 0.35, by), (tr.cx, by), (tr.cx, tr.T()[1])], kind="open", tail="diamond_filled",
          label="1..*", label_at=(1.4, by), label_off=(0, 0.1))
    arrow(ax, [(vr.R()[0] - 0.35, vr.y), (vr.R()[0] - 0.35, by), (pr.cx, by), (pr.cx, pr.T()[1])], kind="open", tail="diamond_filled",
          label="0..1", label_at=(5.6, by), label_off=(0, 0.1))
    d = dict(kind="open", dashed=True)
    arrow(ax, [(cl.T()[0] - 0.8, cl.T()[1]), (tr.cx + 0.4, tr.y)], **d)
    arrow(ax, [(cl.T()[0], cl.T()[1]), (ir.cx, ir.y)], label="«derived from»", label_at=(3.5, 2.55), label_off=(0.62, 0.0), **d)
    arrow(ax, [(cl.T()[0] + 0.8, cl.T()[1]), (pr.cx - 0.4, pr.y)], **d)
    note(ax, 0.1, 0.03, 6.8, 0.62,
         "evaluate_sample() runs validate_terraform() (one TerraformResult per stage: init, validate, plan), check_policies() (PolicyResult) and\n"
         "check_intent(hcl, task.intent) (IntentResult), then classify() maps them onto the error taxonomy (Classification). PolicyResult.evaluated\n"
         "is False when conftest cannot parse the input, so unparseable HCL is counted as a syntax error, not a policy violation.", size=6.4)
    path = FIG_DIR / "uml_class_validation.png"
    save(fig, path)
    return path


# ---------------------------------------------------------------------------------------------------
def sequence() -> Path:
    W, H = 7.2, 7.75
    fig, ax = canvas(W, H)
    names = ["Developer", "UI / CLI", "Pipeline", "Rag\nGenerator", "Retriever", "Vertex\nEmbedder", "Vector\nStore", "Gemini\n(VertexLLM)", "Terraform\n/ OPA"]
    keys = ["dev", "ui", "pl", "rg", "rt", "emb", "vs", "llm", "val"]
    xs = [0.5 + 0.78 * i for i in range(len(names))]
    X = dict(zip(keys, xs))
    top = H - 0.15
    for x, n in zip(xs, names):
        rect(ax, x - 0.36, top - 0.42, 0.72, 0.42, fill=SOFT if n != "Developer" else "white")
        text(ax, x, top - 0.21, n, size=6.4, bold=True)
        line(ax, [(x, top - 0.42), (x, 0.2)], dashed=True, lw=0.6, color="#777777", z=1)

    # (id, from, to, label, is_return); "self" marks the retriever's own step
    steps = [
        (1, "dev", "ui", "requirement", False), (2, "ui", "pl", "generate_rag_detailed(requirement)", False),
        (3, "pl", "rg", "generate_detailed(requirement)", False), (4, "rg", "rt", "retrieve(requirement)", False),
        (5, "rt", "emb", "embed_query(text)", False), (6, "emb", "rt", "query vector", True),
        (7, "rt", "vs", "search(vector, top_k x 5)", False), (8, "vs", "rt", "scored chunks", True),
        ("self", "rt", "rt", "apply per-document cap", False),
        (9, "rt", "rg", "top_k chunks", True), (10, "rg", "llm", "generate(system, user + context)", False),
        (11, "llm", "rg", "HCL text", True), (12, "rg", "pl", "Generation(hcl, retrieved)", True),
        (13, "pl", "ui", "Generation", True), (14, "ui", "pl", "validate(hcl)", False),
        (15, "pl", "val", "validate_terraform: init, validate, plan", False), (16, "val", "pl", "TerraformResult list", True),
        (17, "pl", "val", "check_policies(hcl)", False), (18, "val", "pl", "PolicyResult", True),
        (19, "pl", "ui", "ValidationReport", True), (20, "ui", "dev", "HCL + verdict", True),
    ]
    step, y = 0.316, top - 0.78
    ypos = {}
    for sid, *_ in steps:
        ypos[sid] = y
        y -= step * (1.15 if sid == "self" else 1)

    # activation bars derived from the messages they span: (participant, first message, last message)
    bars = [("ui", 1, 20), ("pl", 2, 13), ("pl", 14, 19), ("rg", 3, 12), ("rt", 4, 9), ("emb", 5, 6), ("vs", 7, 8),
            ("llm", 10, 11), ("val", 15, 16), ("val", 17, 18)]
    half = 0.035
    for k, a, b in bars:
        y1, y2 = ypos[a] + 0.09, ypos[b] - 0.09
        ax.add_patch(Rectangle((X[k] - half, y2), 2 * half, y1 - y2, fc="white", ec=INK, lw=0.7, zorder=2))
    active = {}
    for k, a, b in bars:
        active.setdefault(k, []).append((ypos[a], ypos[b]))

    def edge(k, y, toward):
        for y1, y2 in active.get(k, []):
            if y2 - 0.001 <= y <= y1 + 0.001:
                return X[k] + (half if toward > X[k] else -half)
        return X[k]

    for sid, a, b, label, ret in steps:
        y = ypos[sid]
        if sid == "self":
            xr = X[a] + half
            arrow(ax, [(xr, y), (xr + 0.3, y), (xr + 0.3, y - 0.17), (xr, y - 0.17)], kind="filled", size=6)
            text(ax, xr + 0.36, y - 0.085, label, size=6.2, ha="left")
            continue
        x1, x2 = edge(a, y, X[b]), edge(b, y, X[a])
        arrow(ax, [(x1, y), (x2, y)], kind="open" if ret else "filled", dashed=ret, size=6)
        ax.text((X[a] + X[b]) / 2, y + 0.09, label, fontsize=6.2, ha="center", va="center", fontstyle="italic" if ret else "normal",
                color=INK, zorder=7, bbox=dict(fc="white", ec="none", pad=0.5))
    note(ax, 4.55, 0.3, 2.55, 0.62, "Embedder and Gemini calls retry with\nexponential backoff on 429 / 503.", size=6.3)
    path = FIG_DIR / "uml_sequence.png"
    save(fig, path)
    return path


# ---------------------------------------------------------------------------------------------------
def activity() -> Path:
    W, H = 7.0, 9.75
    fig, ax = canvas(W, H)
    cx = 3.5
    aw, ah = 3.2, 0.44
    kw = dict(kind="filled", size=6)

    def action(x, y, label, w=aw, h=ah):
        return rbox(ax, x, y, w, h, label, fill=SOFT, size=6.9)

    def down(a, b):
        arrow(ax, [(a.B()[0], a.y), (b.T()[0], b.T()[1])], **kw)

    # vertical positions, top to bottom
    y_start, y_a1, y_a2, y_d1, y_arm, y_j1 = 9.55, 9.05, 8.35, 7.45, 6.45, 5.7
    y_d2, y_t1, y_t2, y_t3, y_j2 = 5.15, 4.45, 3.9, 3.3, 2.75
    y_cl, y_d3, y_merge, y_tail, y_end = 2.25, 1.55, 1.05, 0.68, 0.2

    # region around the per-sample steps (drawn first, behind the nodes)
    rect(ax, 0.03, 1.2, 6.94, 6.76, fill="none", lw=0.8, ls=(0, (5, 3)), z=0)
    text(ax, 0.13, 7.83, "for each pending (task, arm, sample), on N parallel workers", size=6.5, italic=True, ha="left", color=GREY)

    initial(ax, cx, y_start)
    a1 = action(cx, y_a1, "Load tasks and manifest; skip samples\nalready recorded in samples.jsonl")
    a2 = action(cx, y_a2, "Build the list of pending\n(task, arm, sample) items")
    arrow(ax, [(cx, y_start - 0.09), (cx, a1.T()[1])], **kw)
    down(a1, a2)

    d1 = diamond(ax, cx, y_d1, 1.1, 0.6, "arm?")
    arm_r = action(1.05, y_arm, "RAG: embed the requirement,\nretrieve top-k chunks with\nper-document cap, prompt Gemini", w=1.95, h=0.7)
    arm_c = action(cx, y_arm, "Conventions: prompt Gemini\nwith all four convention\ndocuments, no retrieval", w=1.95, h=0.7)
    arm_b = action(5.95, y_arm, "Baseline: prompt Gemini\nwith the requirement only\n(no context)", w=1.95, h=0.7)
    down(a2, d1)
    arrow(ax, [(d1.L()[0], d1.cy), (arm_r.cx, d1.cy), (arm_r.cx, arm_r.T()[1])], **kw, label="rag", label_at=(1.7, d1.cy), label_off=(0, 0.1))
    arrow(ax, [(d1.B()[0], d1.y), (arm_c.cx, arm_c.T()[1])], **kw, label="conventions", label_off=(0.36, 0.0))
    arrow(ax, [(d1.R()[0], d1.cy), (arm_b.cx, d1.cy), (arm_b.cx, arm_b.T()[1])], **kw, label="baseline", label_at=(5.3, d1.cy), label_off=(0, 0.1))
    bar(ax, cx, y_j1, 5.8)
    for arm in (arm_r, arm_c, arm_b):
        line(ax, [(arm.cx, arm.y), (arm.cx, y_j1)])

    d2 = diamond(ax, cx, y_d2, 1.5, 0.6, "generation\nsucceeded?")
    err = action(6.0, y_d2, "Record\ngeneration_error", w=1.55, h=0.44)
    t1 = action(cx, y_t1, "terraform init, validate and plan")
    t2 = action(cx, y_t2, "conftest policy check (Rego)")
    t3 = action(cx, y_t3, "functional-intent check against the\ntask's specification", h=0.5)
    arrow(ax, [(cx, y_j1 - 0.03), (cx, d2.T()[1])], **kw)
    arrow(ax, [(d2.R()[0], d2.cy), (err.x, err.cy)], **kw, label="no", label_off=(0, 0.1))
    arrow(ax, [(cx, d2.y), (cx, t1.T()[1])], **kw, label="yes", label_off=(0.18, 0))
    down(t1, t2)
    down(t2, t3)
    bar(ax, cx, y_j2, 5.8)
    arrow(ax, [(cx, t3.y), (cx, y_j2 + 0.03)], **kw)
    line(ax, [(err.cx, err.y), (err.cx, y_j2)])

    cl = action(cx, y_cl, "Classify errors (taxonomy) and set\nvalidate, plan, policy, intent and overall flags")
    d3 = diamond(ax, cx, y_d3, 1.7, 0.5, "infrastructure\nfailure?")
    fl = action(6.0, y_d3, "Flag; not scored;\nre-run later", w=1.6, h=0.44)
    ap = action(1.0, y_d3, "Append record\nto samples.jsonl", w=1.7, h=0.44)
    arrow(ax, [(cx, y_j2 - 0.03), (cx, cl.T()[1])], **kw)
    down(cl, d3)
    arrow(ax, [(d3.R()[0], d3.cy), (fl.x, fl.cy)], **kw, label="yes", label_off=(0, 0.1))
    arrow(ax, [(d3.L()[0], d3.cy), (ap.R()[0], ap.cy)], **kw, label="no", label_off=(0, 0.1))

    # both outcomes merge below the region, then the run-level steps
    line(ax, [(ap.cx, ap.y), (ap.cx, y_merge), (fl.cx, y_merge), (fl.cx, fl.y)])
    tail = action(cx, y_tail, "After all samples: summarise (rates, Wilson intervals, pass@k, paired sign test) into summary.json and summary.md;\n"
                  "--redo-errors drops flagged samples and repeats them", w=6.6, h=0.5)
    arrow(ax, [(cx, y_merge), (cx, tail.T()[1])], **kw)
    final(ax, cx, y_end)
    arrow(ax, [(cx, tail.y), (cx, y_end + 0.13)], **kw)
    path = FIG_DIR / "uml_activity.png"
    save(fig, path)
    return path


# ---------------------------------------------------------------------------------------------------
def deployment() -> Path:
    W, H = 7.0, 5.3
    fig, ax = canvas(W, H)
    node3d(ax, 0.15, 0.2, 4.1, 4.75, "Developer workstation", "device", fill="#f5f7fb")
    text(ax, 0.25, 4.55, "Windows 11", size=6.5, color=GREY, ha="left")
    node3d(ax, 0.35, 2.4, 3.7, 1.95, "Python 3.14 virtual environment", "execution environment", fill=TINT, depth=0.07)
    artifact(ax, 0.5, 3.15, 1.65, 0.5, "ragiac package\n(pipeline, evaluation)")
    artifact(ax, 2.3, 3.15, 1.65, 0.5, "Streamlit UI\n(app.py)")
    artifact(ax, 0.5, 2.55, 3.45, 0.42, "scripts: fetch_provider_docs, ingest, ask, benchmark")
    artifact(ax, 0.35, 1.45, 1.75, 0.6, "conftest 0.70\n+ Rego policies")
    tf = artifact(ax, 2.3, 1.45, 1.75, 0.6, "terraform CLI 1.16\n+ plugin cache")
    text(ax, 0.35, 2.2, "«executable»", size=6, color=GREY, ha="left")
    rect(ax, 0.35, 0.4, 3.7, 0.75, fill="white")
    text(ax, 0.45, 1.02, "«filesystem»", size=6, color=GREY, ha="left")
    text(ax, 0.45, 0.82, "data/knowledge_base   data/index (vectors)   data/cache", size=6.6, ha="left")
    text(ax, 0.45, 0.6, "results/<run>/ (samples.jsonl, summary.json)", size=6.6, ha="left")

    node3d(ax, 4.75, 3.05, 2.05, 1.9, "Google Cloud", "cloud, project rag-iac-dissertation", fill="#f5f7fb", fs=7)
    artifact(ax, 4.9, 3.95, 1.75, 0.55, "Vertex AI\ntext-embedding-005")
    artifact(ax, 4.9, 3.25, 1.75, 0.55, "Vertex AI\nGemini 3.8 Flash")
    node3d(ax, 4.75, 1.65, 2.05, 1.05, "Terraform Registry", "external", fill="#f5f7fb", fs=7)
    artifact(ax, 4.9, 1.75, 1.75, 0.45, "google provider ~> 8.0")
    node3d(ax, 4.75, 0.2, 2.05, 1.0, "GitHub", "external", fill="#f5f7fb", fs=7)
    artifact(ax, 4.9, 0.3, 1.75, 0.5, "provider docs v8.3.0\n(fetched once)")

    arrow(ax, [(4.05, 3.9), (4.75, 3.9)], kind="open", tail="open", label="HTTPS: embeddings,\ngeneration (ADC)", label_at=(4.4, 3.9), label_off=(0.02, 0.26), size=6.2)
    arrow(ax, [(tf.R()[0], tf.cy), (4.75, 2.15)], kind="open", label="provider\ndownload", label_at=(4.4, 1.85), label_off=(0.0, -0.3), size=6.2)
    arrow(ax, [(4.25, 0.7), (4.75, 0.7)], kind="open", label="HTTPS", label_at=(4.5, 0.7), label_off=(0, 0.1), size=6.2)
    path = FIG_DIR / "uml_deployment.png"
    save(fig, path)
    return path


ALL = (use_case, component_diagram, class_pipeline, class_retrieval, class_validation, sequence, activity, deployment)

if __name__ == "__main__":
    for fn in ALL:
        print("wrote", fn())
