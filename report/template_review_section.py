"""Final report: the technical review of the internal templates (answers the examiner's request
for "validation using reviewed internal templates"). The review itself is docs/internal_templates_review.md;
the evidence of its effect on generated code is counted from main-01's stored samples at build time."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PITR_ERROR = "only available for the following [POSTGRES SQLSERVER]"

FINDINGS = [
    ["F1", "Cloud SQL", "High", "Point-in-time recovery advised via `point_in_time_recovery_enabled` for every engine; it is valid only for PostgreSQL and SQL Server (MySQL uses `binary_log_enabled`).", "Rule split by engine"],
    ["F2", "Cloud Storage", "High", "Both lifecycle-rule snippets put two arguments in a single-line block, which is invalid HCL (`terraform init` fails).", "Multi-line blocks"],
    ["F3", "Cloud SQL", "Medium", "Example disables the public IP without a `private_network`, which the API rejects at apply time (passes validate, plan and OPA).", "`private_network` added"],
    ["F4", "GKE", "Medium", "Node pool runs as the Compute Engine default service account, commonly granted project Editor, contrary to the IAM rule.", "Dedicated service account"],
    ["F5", "GKE", "Low", "`node_count` on a regional pool is per zone; the example's 2 creates 6 nodes, which is not stated.", "Stated; example corrected"],
    ["F6", "GKE", "Low", "`remove_default_node_pool` is deprecated in provider v8.9 for new GKE versions.", "Note added"],
    ["F7", "Platform standards", "Low", "Header claimed an export from a real wiki with a named owner; the document is simulated.", "Replaced by a provenance note"],
    ["F8", "Platform standards", "Low", "\"Every resource needs labels\" is wider than the label policy enforces.", "Scope stated"],
    ["F9", "Platform standards", "Info", "Regional pricing claim not verified.", "Left as written"],
]


def _pitr_failures(run_id="main-01", task="sql-02"):
    path = ROOT / "results" / run_id / "samples.jsonl"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["task_id"] != task:
            continue
        n, k = out.get(r["arm"], (0, 0))
        out[r["arm"]] = (n + 1, k + any(PITR_ERROR in d for d in r.get("diagnostics", [])))
    return out


def template_review(R, heading="4.3.7"):
    R.h3(f"{heading} Technical review of the internal templates")
    R.p(
        "The `templates` arm uses four internal-template documents written in the informal style of a team "
        "wiki (`data/internal_templates/`). They were written by the author to simulate real internal "
        "documentation; they are not exports of the organisation's own documents. An independent review by the "
        "organisation's platform team was requested but was not available within the project timeline, so the "
        "templates were given a documented technical self-review instead. The full review record is "
        "`docs/internal_templates_review.md`; this section summarises it."
    )
    R.p(
        "**Method.** Every HCL example in the templates was extracted and run through `terraform init` and "
        "`terraform validate` (Terraform 1.16.2, Google provider v8.9.0) and through `conftest` against all five "
        "organisational policies. Every written rule was then checked against the pinned provider documentation "
        "(v8.3.0), against the other templates and against the Rego policies. Where a defect could affect generated "
        "code, the stored benchmark samples were searched for its effect."
    )
    R.table(
        ["#", "Document", "Severity", "Finding", "Correction"],
        FINDINGS,
        [0.9, 2.6, 1.6, 7.6, 3.1],
        "Findings of the technical review of the internal templates.",
        font_size=8.5,
    )
    counts = _pitr_failures()
    if counts:
        arms = [a for a in ("templates", "conventions", "rag", "baseline") if a in counts]
        R.p(
            "**Effect on generated code.** Finding F1 is visible in the benchmark. On task `sql-02` (a highly "
            "available MySQL instance with backups) in run `main-01`, the samples that failed `terraform plan` with "
            "the error *\"point_in_time_recovery_enabled is only available for the following [POSTGRES SQLSERVER]\"* "
            "were: "
            + "; ".join(f"{a} {counts[a][1]} of {counts[a][0]}" for a in arms)
            + ". The hand-written conventions given to the `conventions` arm contained the same incorrect advice. "
            "The baseline, given no documents, shows that the model makes this mistake on its own some of the time; "
            "the flawed advice made it the norm. "
            "In every `rag` sample for this task, retrieval returned both the flawed conventions page and the "
            "provider page for `google_sql_database_instance`, whose MySQL examples use `binary_log_enabled`; the "
            "model followed the provider page each time. This is a direct case of a defect in an organisational "
            "document being copied into generated infrastructure code when it is the only guidance the model has, "
            "and it is one of the failure cases analysed in Section 5.7.4."
        )
    R.p(
        "**Corrections and their use.** All findings except F9 were corrected in the templates. F1 and F3 were "
        "corrected in the hand-written conventions as well, because they contained the same two defects. After "
        "correction, every template example passes `terraform validate` and all policy checks. The final benchmark "
        "run (`final-01`, Section 5) uses the corrected templates and conventions. This review checks technical "
        "correctness and consistency with the enforced policies. It does not show that the templates match the "
        "organisation's actual practice. That needs an independent review by the platform team, which is listed "
        "under Future Scope."
    )
