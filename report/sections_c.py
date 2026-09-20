"""Report sections 5, 8, references and appendices (results/discussion live in results_section.py)."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CATEGORY_NOTES = {
    "storage": "Cloud Storage buckets: versioning, lifecycle rules, access settings, IAM",
    "database": "Cloud SQL: engine and tier, availability, backups, private IP, users and databases",
    "kubernetes": "GKE clusters and node pools: private nodes, Workload Identity, Autopilot, autoscaling",
    "network": "VPC, subnets, firewall rules, Cloud Router and NAT, global addresses, private DNS",
    "compute": "Compute Engine instances with specific machine, zone, image and service-account settings",
    "serverless": "Cloud Run, including IAM restricted to one invoker; Cloud Scheduler",
    "messaging": "Pub/Sub topics and subscriptions, including dead-letter policy",
    "data": "BigQuery datasets and tables",
    "security": "Secret Manager and Cloud KMS with rotation",
    "platform": "Artifact Registry",
    "policy_conflict": "Requirements that explicitly ask for something organisational policy forbids",
}


def _tasks():
    path = ROOT / "data" / "eval" / "gcp_tasks.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def methodology(R):
    R.h1("5. Evaluation Methodology")
    R.p(
        "The metrics, arms and analysis described in this section were fixed before the benchmark was run, as "
        "the supervisor required."
    )

    R.h2("5.1 Research questions")
    R.numbered(
        [
            "**RQ1 (technical correctness).** Does retrieval increase the proportion of generated configurations that validate, plan and satisfy the stated intent?",
            "**RQ2 (organisational policy).** Does retrieval increase conformance to organisational policy, which the requirement itself never states, and is any gain due to retrieval or simply to the conventions being available to the model?",
            "**RQ3 (errors).** Which error categories dominate, and how does retrieval change their distribution?",
            "**RQ4 (retrieval quality).** How often does retrieval surface documentation for the resources a task needs, and is that associated with success?",
        ]
    )

    R.h2("5.2 Task set")
    tasks = _tasks()
    by_cat = Counter(t["category"] for t in tasks)
    by_diff = Counter(t["difficulty"] for t in tasks)
    headline = [t for t in tasks if t["category"] != "policy_conflict"]
    R.p(
        f"The published IaC benchmarks reviewed target AWS, so a GCP task set was built for this work. It contains "
        f"{len(tasks)} natural-language requirements: {len(headline)} headline tasks and "
        f"{by_cat['policy_conflict']} tasks that deliberately conflict with organisational policy. Difficulty is "
        f"graded 1 to 3: level 1 is a single resource with one or two constraints ({by_diff[1]} tasks), level 2 a "
        f"single resource with several interacting constraints ({by_diff[2]} tasks), and level 3 several related "
        f"resources ({by_diff[3]} tasks). Table 5 summarises the categories; the full list is in Appendix A."
    )
    order = [c for c in CATEGORY_NOTES if c in by_cat]
    R.table(
        ["Category", "Tasks", "Coverage"],
        [[c, by_cat[c], CATEGORY_NOTES[c]] for c in order],
        [3.2, 1.5, 11.3],
        "Task set composition.",
        align_right_from=None,
    )
    R.p(
        "Each task carries a machine-checkable intent specification in the style of IaC-Eval [2]: the resource "
        "types that must be present and assertions on their attributes (for example, that versioning is enabled "
        "and a lifecycle rule moves objects to NEARLINE after 30 days). Specifications allow alternatives where a "
        "requirement can legitimately be met in more than one way (an IAM member or an IAM binding; "
        "`node_count` or `initial_node_count`) and evaluate constant arithmetic, so a correct answer is not "
        "rejected for its form. The two policy-conflict tasks (a publicly readable website bucket and a Cloud SQL "
        "instance with a public IP) are reported separately: a model that does what was asked will violate policy "
        "by design, and mixing them into the headline would confuse the comparison."
    )

    R.h2("5.3 Experimental arms, sampling and metrics")
    R.p(
        "Three arms are compared. **RAG** supplies the eight retrieved chunks as context. The **baseline** uses "
        "the same model, target provider constraint and temperature but no context at all. A third, "
        "**conventions-in-prompt** control uses the RAG prompt with the four organisational-convention documents "
        "pasted in as context and no retrieval, and no provider documentation. The control exists because the "
        "conventions are stated only in the retrieval corpus: without it, any policy-compliance advantage of RAG "
        "over the baseline could simply reflect the model being told the conventions, not retrieval. RAG versus the "
        "control isolates the value of retrieving provider documentation; the control versus the baseline isolates "
        "the value of knowing the conventions."
    )
    R.p(
        "Every task is run five times per arm at temperature 0.8, so that the samples differ and pass@k is "
        "meaningful; the sampling temperature is stored with each run. The run was interrupted once and resumed "
        "with identical settings and code. The first 93 RAG and baseline samples (roughly the first one to two "
        "samples of each task) come from the initial session on 19 September; every remaining sample, and all "
        "samples of the conventions-in-prompt control, were generated interleaved in the resumed session on "
        "20 September. The control therefore has no samples from the earlier session, so drift in service "
        "behaviour between sessions could affect comparisons against it slightly. This is recorded in the run "
        "manifest, and the number of samples affected is small relative to the whole."
    )
    R.table(
        ["Metric", "Definition"],
        [
            ["Validate pass rate", "Proportion of samples for which `terraform init` and `terraform validate` succeed."],
            ["Plan pass rate", "Proportion for which `terraform plan` succeeds, among samples where plan could be evaluated (credential and unset-variable failures excluded)."],
            ["OPA violation rate", "Proportion of samples that violate at least one policy rule, among samples the policy engine could parse."],
            ["Intent pass rate", "Proportion of samples that satisfy the task's intent specification."],
            ["Functional pass rate", "Validates, plans where evaluable, and satisfies intent: technical correctness independent of organisational policy."],
            ["Overall pass rate", "Functional pass and no policy violation."],
            ["pass@k", "Unbiased estimator [9] of the probability that at least one of k samples is overall-correct, averaged over tasks (k = 1, 3, 5)."],
            ["Retrieval hit rate", "Fraction of the resource types a task needs that appear in the retrieved chunks (RAG arm only)."],
        ],
        [4.0, 12.0],
        "Metrics (validate/plan pass rate, OPA violation rate and pass@k were specified by the supervisor; the remainder were added).",
    )
    R.p(
        "Reporting functional and overall pass rates separately is deliberate. Following the observation in [6] "
        "that validity and security are largely orthogonal, and the intent-versus-correctness gap in [3], a single "
        "score would hide whether retrieval helps the model write correct infrastructure, helps it follow "
        "organisational conventions, or both."
    )

    R.h2("5.4 Retrieval quality and the error taxonomy")
    R.p(
        "Every failed sample is mapped to categories derived from what the validators report, so failures can "
        "be counted per arm rather than read one at a time. The categories are grouped by the stage that catches "
        "them: generation failure; provider initialisation; HCL syntax; schema errors (unsupported argument or "
        "block, missing required argument, invalid value, conflicting arguments, invalid reference, expression "
        "error); plan errors; policy violations (missing labels, public access); and intent failures (missing "
        "resource, attribute mismatch). Two informational flags are recorded that are not failures: use of "
        "deprecated arguments and a provider version constraint that differs from the target. Messages that fit no "
        "category fall into an *other* bucket with the raw diagnostic retained, so the taxonomy can be refined "
        "against real data and, in the final report, mapped onto the published taxonomy of Nekrasov et al. [3]."
    )
    R.p(
        "Retrieval quality is measured as the hit rate defined in Table 6: the share of needed resource types "
        "whose documentation appears among the retrieved chunks. Matching on content rather than file names is "
        "necessary because several documents can describe one resource."
    )

    R.h2("5.5 Statistical treatment")
    R.p(
        "Proportions are reported with 95% Wilson score intervals [10], which behave sensibly at small sample sizes "
        "and at 0% and 100%. Because the same 33 tasks are run under both arms, the arms are compared per task: "
        "for each task the mean overall pass rate of each arm is computed, and the number of tasks on which each arm "
        "is better is tested with an exact two-sided sign test. With 33 tasks and one model, differences at the "
        "level of individual categories are indicative rather than conclusive and are described as such."
    )

    R.h2("5.6 Threats to validity")
    R.bullets(
        [
            "**Own task set and specifications.** Tasks and intent checks were written by the author. Specifications could wrongly reject a correct answer or accept an incorrect one. The specifications were revised after early trial runs to allow legitimate alternatives, so those trial tasks are not independent of the task design; the changes were made to the checker's tolerance, never to favour an arm.",
            "**Static intent checking.** Intent is checked on the parsed HCL. Values computed through variables or `for_each` cannot be resolved, so tasks were written to avoid needing that.",
            "**Asymmetry in organisational knowledge.** The organisational conventions live only in the retrieval corpus, so the baseline cannot know them. The policy-compliance advantage of RAG over the baseline is therefore partly an advantage of *having access to* those conventions, not of retrieval as such. The conventions-in-prompt control arm (Section 5.3) exists to separate the two. The conventions themselves were written by the author for this study, so their effect measures the value of stating conventions, not the value of any particular real organisation's documents.",
            "**Single model, single temperature.** Results are for one model at one sampling temperature and should not be generalised across models.",
            "**Model and service drift.** Hosted models change and are retired; the exact model, date and settings are recorded per run.",
            "**Sample size.** 33 tasks with five samples each gives usable but wide intervals; small differences will not be statistically distinguishable.",
            "**Plan evaluability.** Plan is only counted where it could run; excluding non-evaluable samples slightly shrinks the plan denominator.",
        ]
    )


def remaining_work(R):
    R.h1("8. Remaining Work and Plan")

    R.h2("8.1 Remaining technical work")
    R.numbered(
        [
            "**Chunk-size ablation.** The number of retrieved chunks and the per-document cap were varied (Section 6.8), but chunk size was not, because it requires rebuilding and re-embedding the index. This remains to be done, into a separate index so the main run stays reproducible, and its effect related to retrieval hit rate (RQ4).",
            "**Sanitised internal templates.** Replace the hand-written conventions with reviewed internal templates, containing no customer or production data, as the supervisor specified.",
            "**Deeper error analysis.** Manually review a sample of failures per category, refine the taxonomy, and map it onto the published taxonomy [3].",
            "**Optional extensions.** Verifier-feedback refinement in the style of [4], and a poisoning-robustness check of the corpus in the spirit of [7].",
        ]
    )

    R.h2("8.2 Proposed user evaluation")
    R.p(
        "The outline calls for an evaluation of usability and developer trust. The supervisor asked that the "
        "participant count, task set and instrument be stated; the following is proposed and awaits his approval."
    )
    R.table(
        ["Element", "Proposal"],
        [
            ["Participants", "8 engineers from the delivery team, voluntary: 4 with under one year of Terraform experience and 4 with two or more years, to see whether the assistant helps novices and experts differently."],
            ["Design", "Within-subjects and counterbalanced. Each participant completes four tasks matched for difficulty: two with the assistant and two without it (using provider documentation and search as they normally would). Task order and condition are rotated across participants."],
            ["Task set", "Four synthetic tasks per participant drawn from the benchmark task set, spanning difficulty levels 1 to 3. No customer or production information is used."],
            ["Objective measures", "Task success (the same automated validity and intent checks used in the benchmark), time to completion, and the number of edits made to assistant output."],
            ["Subjective instruments", "The System Usability Scale (10 items) [13] after the assistant condition; a trust-in-automation scale (12 items) [14], adapted to code generation; and five semi-structured interview questions on what participants did and did not trust."],
            ["Analysis", "Paired non-parametric comparisons (Wilcoxon signed-rank) given the small sample, with effect sizes and intervals rather than p-values alone; SUS scored in the standard way; interview notes coded thematically."],
            ["Ethics", "Informed consent, anonymised data, organisational permission obtained in advance, and the option to withdraw at any time."],
        ],
        [3.5, 12.5],
        "Proposed user-evaluation design.",
    )

    R.h2("8.3 Timeline")
    R.table(
        ["Phase (from the outline)", "Dates", "Status"],
        [
            ["1. Literature review and problem formulation", "25 Jul - 14 Aug 2026", "Complete"],
            ["2. Abstract/outline submission and evaluation", "15 Aug - 4 Sep 2026", "Complete"],
            ["3. RAG pipeline and knowledge-base design", "5 - 25 Sep 2026", "Complete; technology choices stated in Section 3.3"],
            ["4. Prototype development and mid-semester evaluation", "26 Sep - 16 Oct 2026", "Prototype and first benchmark complete; this report"],
            ["5. Full implementation and validation tooling", "17 Oct - 6 Nov 2026", "Validation tooling brought forward as the supervisor advised; control arm, retrieval-count and per-document-cap ablations and near-greedy run complete; remaining: chunk-size ablation, internal templates"],
            ["6. Benchmarking, user evaluation and final report", "7 - 30 Nov 2026", "Planned: final benchmark, user study (Section 8.2), final report"],
        ],
        [6.3, 3.7, 6.0],
        "Plan of work and status.",
    )

    R.h2("8.4 Risks")
    R.bullets(
        [
            "**Model retirement.** Hosted models are retired on short notice. Mitigated by recording model and date per run and by keeping the model a configuration setting.",
            "**API quota.** A new cloud project has low default quotas and long benchmark runs are throttled. Mitigated by backoff, an embedding cache and resumable runs; a quota-increase request is an option if needed.",
            "**Statistical power.** Wide intervals may limit conclusions. Mitigated by paired analysis and by reporting uncertainty explicitly.",
            "**Participant availability.** The user study depends on colleagues' time. Mitigated by a short, fixed-length session and a small design.",
        ]
    )


REFERENCES = [
    "P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Kuttler, M. Lewis, W.-t. Yih, T. Rocktaschel, S. Riedel and D. Kiela, \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,\" in Advances in Neural Information Processing Systems (NeurIPS), 2020.",
    "P. T. J. Kon et al., \"IaC-Eval: A Code Generation Benchmark for Cloud Infrastructure-as-Code Programs,\" NeurIPS 2024 (Datasets and Benchmarks). Code and data: https://github.com/autoiac-project/iac-eval.",
    "R. Nekrasov, S. Fossati, I. Kumara, D. A. Tamburri and W.-J. van den Heuvel, \"IaC Generation with LLMs: An Error Taxonomy and A Study on Configuration Knowledge Injection,\" arXiv:2512.14792, 2025.",
    "M. Jouini, \"Verifier-First Evaluation of Agentic LLMs for Infrastructure-as-Code Generation,\" arXiv:2607.20478, 2026.",
    "S. Davidson, L. Sun, B. Bhasker, L. Callot and A. Deoras, \"Multi-IaC-Eval: Benchmarking Cloud Infrastructure as Code Across Multiple Formats,\" arXiv:2509.05303, 2025.",
    "F. L. S. Vargas, R. B. Mansilha and D. Kreutz, \"Security-First Evaluation of Text-to-Terraform: Benchmarking LLMs and SLMs for Secure IaC Generation,\" arXiv:2608.02672, 2026.",
    "K. Ye, L. Su and C. Qian, \"ImportSnare: Directed 'Code Manual' Hijacking in Retrieval-Augmented Code Generation,\" arXiv:2509.07941, 2025.",
    "A. A. Khan, M. T. Hasan, K. K. Kemell, J. Rasku and P. Abrahamsson, \"Developing Retrieval Augmented Generation (RAG) based LLM Systems from PDFs: An Experience Report,\" arXiv:2410.15944, 2024.",
    "M. Chen et al., \"Evaluating Large Language Models Trained on Code,\" arXiv:2107.03374, 2021.",
    "E. B. Wilson, \"Probable inference, the law of succession, and statistical inference,\" Journal of the American Statistical Association, vol. 22, no. 158, pp. 209-212, 1927.",
    "HashiCorp, \"Terraform Provider for Google Cloud Platform, release v8.3.0 documentation,\" https://github.com/hashicorp/terraform-provider-google (MPL-2.0).",
    "Open Policy Agent, \"Policy Language (Rego)\" and Conftest documentation, https://www.openpolicyagent.org and https://www.conftest.dev.",
    "J. Brooke, \"SUS: A quick and dirty usability scale,\" in Usability Evaluation in Industry, Taylor & Francis, 1996.",
    "J.-Y. Jian, A. M. Bisantz and C. G. Drury, \"Foundations for an empirically determined scale of trust in automated systems,\" International Journal of Cognitive Ergonomics, vol. 4, no. 1, pp. 53-71, 2000.",
    "Google Cloud, \"Generative AI on Vertex AI: locations and model availability,\" https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations (accessed September 2026).",
]


def references(R):
    R.h1("References")
    for i, ref in enumerate(REFERENCES, start=1):
        para = R.p(f"[{i}]  {ref}", align="left", size=10.5, space_after=4)
        para.paragraph_format.left_indent = None


ABBREVIATIONS = [
    ("ADC", "Application Default Credentials"),
    ("API", "Application Programming Interface"),
    ("CI", "Confidence Interval"),
    ("GCP", "Google Cloud Platform"),
    ("GCS", "Google Cloud Storage"),
    ("GKE", "Google Kubernetes Engine"),
    ("HCL", "HashiCorp Configuration Language"),
    ("IaC", "Infrastructure as Code"),
    ("KB", "Knowledge Base"),
    ("LLM", "Large Language Model"),
    ("OPA", "Open Policy Agent"),
    ("RAG", "Retrieval-Augmented Generation"),
    ("Rego", "The policy language used by Open Policy Agent"),
    ("RQ", "Research Question"),
    ("SUS", "System Usability Scale"),
    ("TF-IDF", "Term Frequency - Inverse Document Frequency"),
    ("WILP", "Work Integrated Learning Programmes"),
]


def abbreviations(R):
    R.h1("Abbreviations")
    R.table(["Abbreviation", "Expansion"], [list(a) for a in ABBREVIATIONS], [3.5, 12.5], "Abbreviations used in this report.")


def appendices(R, manifest):
    R.h1("Appendix A. Task catalogue")
    R.p("All tasks in the benchmark. Difficulty is 1 (single resource, simple) to 3 (several related resources).")
    R.table(
        ["ID", "Category", "Diff.", "Requirement"],
        [[t["id"], t["category"], t["difficulty"], t["requirement"]] for t in _tasks()],
        [1.6, 2.6, 1.1, 10.7],
        "The 35 benchmark tasks.",
        font_size=8.5,
    )

    R.h1("Appendix B. Prompt templates")
    from ragiac.generation import prompts

    R.h3("B.1 Retrieval-augmented arm: system prompt")
    R.code(prompts.RAG_SYSTEM_PROMPT.replace(". ", ".\n"), size=8)
    R.h3("B.2 Baseline arm: system prompt")
    R.code(prompts.BASELINE_SYSTEM_PROMPT.replace(". ", ".\n"), size=8)
    R.h3("B.3 User prompt templates")
    R.code(prompts.RAG_USER_TEMPLATE + "\n\n----\n\n" + prompts.BASELINE_USER_TEMPLATE, size=8)

    R.h1("Appendix C. Organisational policy rules")
    R.p("Rego rules evaluated by Conftest against every generated configuration.")
    R.table(
        ["Rule", "What it forbids"],
        [
            ["Required labels", "A Cloud Storage bucket, Cloud SQL instance or GKE cluster without an `environment` label."],
            ["Public IAM grants", "Any `*_iam_member` or `*_iam_binding` granting access to `allUsers` or `allAuthenticatedUsers`."],
            ["Cloud SQL exposure", "A Cloud SQL instance with a public IP, or an authorised network of `0.0.0.0/0`."],
            ["Open ingress", "An ingress firewall rule open to `0.0.0.0/0`."],
        ],
        [4.0, 12.0],
        "Policy rules.",
    )

    if manifest:
        R.h1("Appendix D. Run manifest of the reported benchmark")
        R.p("The recorded settings of the run whose results are reported in Section 6.")
        R.code(json.dumps({k: v for k, v in manifest.items() if k != "tasks_selected"}, indent=2), size=8)
