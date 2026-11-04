"""Final report: abstract, Chapter 1 (Introduction), Chapter 3 (Problem Statement), the evaluation
methodology of Chapter 4 (4.3) and Chapter 6 (Conclusion and Future Scope). Chapter 5 is in
final_results.py. The literature review, system design and implementation are shared with the
mid-semester report (sections_a/b/c.py, called with final=True where the text differs).

The abstract and conclusion quote figures from results/final-01 and results/user_study; they were
written after inspecting those results and must be re-checked if either is re-run."""

import sections_a
import sections_c
import template_review_section
from ragiac.generation.policy_pinning import GENERAL_POLICY, POLICY_FOR_PROVIDER_PAGE

ABSTRACT = """Writing Infrastructure as Code (IaC) by hand is slow and error-prone, and large language models (LLMs) can draft it but often ignore organisational conventions that a plain-language request never states. This dissertation builds and evaluates a Retrieval-Augmented Generation (RAG) assistant that turns natural-language requirements into Terraform for Google Cloud, grounded in provider documentation and organisational conventions, and checks every output with terraform validate and plan, Open Policy Agent policies and functional-intent checks.

At mid-semester (35 tasks, three arms, 525 samples), technical correctness was near ceiling for every arm, but overall pass was 57.0% without retrieval, 78.8% with RAG and 95.2% with the conventions pasted into the prompt, because the conventions were retrieved in only 12% of RAG samples.

The final evaluation (five arms, 875 samples, under all five policies) added a policy-pinning variant that always supplies the relevant policy pages. It reached 93.3%, against 50.9% without retrieval, 67.3% with RAG and 99.4% with pasted conventions, beating RAG on 10 tasks and losing none (p = 0.002). Remaining failures trace to vague policy text, a template defect and a faulty intent check. With eight engineers, the assistant roughly halved median task time (p = 0.039); usability was moderate (SUS 63.8)."""


# ---- Chapter 1 ------------------------------------------------------------------------------------
def introduction(R):
    R.h1("1. Introduction")
    sections_a.background(R)

    R.h2("1.2 Objectives and their final status")
    R.p("The objectives set out in the approved outline, and how each was met, are:")
    R.table(
        ["#", "Objective (from the outline)", "Final status"],
        [
            ["O1", "Study the state of the art in LLM-based code generation and RAG for IaC", "Done (Chapter 2)"],
            ["O2", "Identify common LLM error categories in IaC generation and the knowledge gaps retrieval must close", "Done: taxonomy applied to every sample and mapped onto a published one; detailed failure analysis (Section 5.7)"],
            ["O3", "Design a RAG architecture (ingestion, chunking, embedding, vector storage, retrieval, generation)", "Done (Section 4.1), extended with per-resource policy indexing and policy pinning (Section 4.3.4)"],
            ["O4", "Build a working prototype that generates IaC from natural-language prompts", "Done: runs end to end on Vertex AI (Sections 4.1, 4.2)"],
            ["O5", "Validate output with automated tooling and benchmark against a non-RAG baseline", "Done: final benchmark of five arms and 875 samples, and seven retrieval configurations (Sections 5.1 to 5.6)"],
            ["O6", "User evaluation of usability and developer trust", "Done with stated limitations: eight engineers, 32 task sessions (Section 5.10)"],
        ],
        [1.1, 7.4, 7.5],
        "Objectives and their final status.",
    )

    R.h2("1.3 Response to the mid-semester review")
    R.p(
        "The mid-semester review asked for the evaluation to be strengthened in five specific ways and for the "
        "report to be restructured. Table " + str(R._table_no + 1) + " lists each request, what was done in response "
        "and where it is reported. Where a request could not be met in full, the table says so."
    )
    R.table(
        ["Review comment", "What was done", "Where"],
        [
            ["Improved retrieval of organisational policies", "The policy was indexed per resource type (policy retrieval rose from 12% to 36% of samples), and a policy-pinning arm was built that always places the relevant policy pages in a mandatory prompt section", "4.3.4, 5.4"],
            ["Validation using reviewed internal templates", "An independent review by the platform team was not available in time. The templates were given a documented technical self-review (nine findings, eight corrected) and the final run uses the corrected versions", "4.3.7, 5.5"],
            ["Additional retrieval configuration experiments", "Seven configurations in all: number of chunks (3, 4, 8, 12), per-document cap removed, chunk size 800, and per-resource policy indexing", "4.3.8, 5.6"],
            ["Detailed failure analysis", "Every failure classified by root cause and the configurations behind each cause compared across arms; six case studies, including a policy that does not say what is enforced, a template defect copied into code, and a defect found in the intent checker itself", "5.7"],
            ["User-level assessment of usability, completion time and trust", "Counterbalanced study with eight engineers at two experience levels: SUS, a trust-in-automation scale and time to completion", "4.3.9, 5.10"],
            ["Report writing and chapter structure", "Report reorganised into the six chapters requested and laid out to the WILP guideline", "This report"],
        ],
        [4.2, 9.4, 2.4],
        "Mid-semester review comments and the response to each.",
        font_size=9.5,
    )

    R.h2("1.4 Organisation of this report")
    R.p(
        "Chapter 2 reviews related work. Chapter 3 states the problem, with its scope, assumptions and "
        "constraints. Chapter 4 sets out the methodology: the system design and the reasons for each technology "
        "choice, the implementation, and the evaluation methodology, including the policy-pinning design, the "
        "technical review of the internal templates and the user-evaluation design. Chapter 5 presents and "
        "discusses the results of the final benchmark, the retrieval configuration experiments, the failure "
        "analysis and the user evaluation. Chapter 6 concludes and sets out future work. The appendices give the "
        "task catalogue, the prompts, the policy rules and the run manifest. A glossary of technical terms and a "
        "list of abbreviations follow the references."
    )


# ---- Chapter 3 ------------------------------------------------------------------------------------
def problem_statement(R):
    R.h1("3. Problem Statement")

    R.h2("3.1 Statement")
    R.p(
        "Given a natural-language infrastructure requirement, generate Terraform for Google Cloud Platform (GCP) "
        "that (a) is well-formed and consistent with the provider's schema, (b) actually implements what was "
        "asked, and (c) complies with organisational policy, which the requirement itself does not state. The "
        "central question is whether retrieval over provider documentation and organisational conventions "
        "improves these outcomes compared with the same model used without retrieval; where it does not, what "
        "kinds of error remain and why; and whether developers find such an assistant usable and trustworthy."
    )

    R.h2("3.2 Why the problem is not solved by retrieval alone")
    R.p(
        "Retrieval ranks documents by their similarity to the request. A request describes a resource (\"a bucket "
        "that keeps old versions for 30 days\"); organisational policy describes rules that apply to many resources "
        "(\"every data store carries an environment label\") and is rarely similar to any single request. The "
        "earlier run of this project (`main-01`) showed the consequence: the general policy document was retrieved "
        "in 12% of RAG samples, and the policy failures concentrated where it was absent. The problem addressed in "
        "the final phase is therefore how to get cross-cutting policy to the model reliably, and whether the model "
        "then follows it."
    )

    R.h2("3.3 Scope, assumptions and constraints")
    R.p(
        "The work designs, implements and evaluates a RAG-based assistant that accepts natural-language "
        "infrastructure requirements and produces Terraform for Google Cloud, grounded in a curated knowledge base "
        "of provider documentation and organisational conventions. Production deployment, multi-cloud coverage "
        "beyond GCP and continuous-integration rollout are outside the scope of this dissertation and are noted "
        "as future work. The assistant never applies infrastructure: generated code is only validated and planned."
    )
    R.p(
        "The work assumes a single target model and provider version at a time (Section 4.3.3), that the "
        "organisation's conventions can be stated in a few short documents, and that automated validators "
        "(Terraform, OPA and a functional-intent check) are a sufficient proxy for correctness for the purposes of "
        "this study. The last assumption was tested in the failure analysis and found to hold with one exception, "
        "an intent check that rejected correct answers (Section 5.7.5). The organisational conventions, internal "
        "templates and policies were written by the author to stand in for a real organisation's documents, "
        "because the host organisation's own documents could not be used. The main constraints were a single "
        "workstation and API quota for all runs, and the availability of colleagues for the user evaluation."
    )


# ---- Chapter 4.3 ----------------------------------------------------------------------------------
def methodology(R):
    R.h2("4.3 Evaluation Methodology")
    R.p(
        "The metrics, the baseline, RAG and conventions arms and the analysis described here were fixed before the "
        "earlier benchmark run (`main-01`), as the supervisor required. The templates arm was added to that run later. "
        "The policy-pinning arm, the template review and the "
        "additional retrieval experiments were added after the mid-semester review, in response to its comments "
        "and to what the earlier run showed. They were evaluated on freshly generated samples in the final run "
        "(`final-01`), but they were designed with knowledge of the earlier results, which is stated as a threat "
        "to validity in Section 4.3.11."
    )

    R.h3("4.3.1 Research questions")
    R.numbered(
        [
            "**RQ1 (technical correctness).** Does retrieval increase the proportion of generated configurations that validate, plan and satisfy the stated intent?",
            "**RQ2 (organisational policy).** Does retrieval increase conformance to organisational policy, which the requirement never states, and is any gain due to retrieval or simply to the conventions being available to the model?",
            "**RQ3 (errors).** Which error categories dominate, what causes them, and how does retrieval change their distribution?",
            "**RQ4 (retrieval).** How often does retrieval surface the documentation a task needs, including the policy, and which retrieval configuration works best?",
            "**RQ5 (users).** Do developers complete tasks faster or more successfully with the assistant, and how usable and trustworthy do they find it?",
        ]
    )

    sections_c.task_set(R, "4.3.2")

    R.h3("4.3.3 Experimental arms and sampling")
    R.p(
        "Five arms are compared, all using the same model, temperature, target provider constraint and task set. "
        "They differ only in the context the model is given:"
    )
    R.table(
        ["Arm", "Context given to the model", "Question it answers"],
        [
            ["Baseline", "None", "What the model does from its own knowledge"],
            ["RAG", "The eight chunks most similar to the requirement, at most three per document, from provider documentation and organisational policy", "What retrieval adds"],
            ["Conventions in prompt", "The four hand-written convention documents pasted in whole; no retrieval and no provider documentation", "What knowing the conventions adds, without retrieval"],
            ["Simulated internal templates", "As above, but with the four wiki-style internal templates in place of the conventions", "Whether the conventions result survives messier documentation"],
            ["RAG + pinned policy", "The RAG context, plus the general policy and the policy page for each resource type retrieved, in a mandatory section of the prompt", "Whether policy reaches the model and is followed when it is not left to ranking"],
        ],
        [3.4, 7.8, 4.8],
        "The five experimental arms.",
        font_size=9.5,
    )
    R.p(
        "Every task is run five times per arm at temperature 0.8, so that the samples differ and pass@k is "
        "meaningful. All five arms of the final run were generated interleaved in one session, from one commit "
        "and one index, so drift in the hosted model between arms is not a concern within the run. The retrieval "
        "configuration experiments use three samples per task, so their pass@1 and pass@3 are the figures that "
        "can be compared with the main run."
    )

    R.h3("4.3.4 Retrieving and pinning organisational policy")
    R.p(
        "The earlier run showed that policy was retrieved too rarely (Section 3.2). Two changes were made in "
        "response. First, the policy was **indexed per resource type**: three short documents were "
        "added to the knowledge base that restate the policy for Cloud Storage, Cloud SQL and GKE in that "
        "resource's own vocabulary, so that each competes for retrieval with the provider pages of the same "
        "resource rather than one general page competing with all of them. This is part of the index for every "
        "retrieving arm in the final run."
    )
    R.p(
        "Second, a **policy-pinning** arm (`rag_policy`, `src/ragiac/generation/policy_pinning.py`) takes policy "
        "out of the ranking altogether. It retrieves exactly as the RAG arm does, then selects policy pages by rule "
        f"rather than by similarity: the general policy (`{GENERAL_POLICY}`) always, and the resource-specific "
        "policy page for every resource type whose provider page appears among the retrieved chunks (Table "
        f"{R._table_no + 1}). The selected pages are placed whole in a separate prompt section headed "
        "\"Organisational policy (mandatory)\", any retrieved chunks from those pages are dropped from the "
        "ordinary context to avoid duplication, and the system prompt adds one sentence stating that the policy "
        "section is mandatory unless the requirement explicitly asks for something different (Appendix B.4)."
    )
    pages = {}
    for page, policy in POLICY_FOR_PROVIDER_PAGE.items():
        pages.setdefault(policy, []).append(f"`{page}`")
    R.table(
        ["Retrieved provider page", "Policy page pinned"],
        [[", ".join(v), f"`{k}`"] for k, v in pages.items()] + [["(any request)", f"`{GENERAL_POLICY}`"]],
        [10.0, 6.0],
        "How the policy-pinning arm selects policy pages.",
    )
    R.p(
        "The design keeps the prompt short: at most two policy pages are pinned for a single-resource request, "
        "instead of pasting every convention document as the conventions arm does, so it would still work for an "
        "organisation whose conventions are too long to paste whole. Its weakness is that it relies on a "
        "hand-maintained mapping, so a resource type with no policy page of its own (BigQuery, here) gets only "
        "the general policy. Section 5.7.3 shows the effect of that."
    )

    R.h3("4.3.5 Metrics")
    sections_c.metrics_table(R, caption="Metrics.")
    R.p(
        "Reporting functional and overall pass rates separately is deliberate. Following the observation in [6] "
        "that validity and security are largely orthogonal, and the intent-versus-correctness gap in [3], a single "
        "score would hide whether a change helps the model write correct infrastructure, helps it follow "
        "organisational conventions, or both."
    )

    R.h3("4.3.6 Error taxonomy, retrieval quality and failure analysis")
    R.p(
        "Every failed sample is mapped to error categories derived from what the validators report, grouped by "
        "the stage that catches them: generation failure; provider initialisation; HCL syntax; schema errors "
        "(unsupported argument or block, missing required argument, invalid value, conflicting arguments, invalid "
        "reference, expression error); plan errors; policy violations (missing labels, public access, other "
        "policy); and intent failures (missing resource, attribute mismatch). Messages that fit no category fall "
        "into an *other* bucket with the raw diagnostic kept. The taxonomy is mapped onto the published taxonomy of "
        "Nekrasov et al. [3] (Section 5.7.7)."
    )
    R.p(
        "Two retrieval measures are used. The **hit rate** is the share of the resource types a task needs whose "
        "provider documentation appears among the retrieved chunks. The **policy retrieval rate** is the share of "
        "samples in which at least one policy document was among the retrieved chunks. The first measures whether "
        "the model was given the right reference material, the second whether it was given the rules."
    )
    R.p(
        "The detailed failure analysis goes beyond the counts. Every failing sample of the final run was assigned "
        "to a root cause from its diagnostics. For each root cause, the generated configurations were then read and "
        "compared across all arms on the affected tasks, to find what differed between passing and failing "
        "samples. Where a root cause pointed at the evaluation itself (an intent check or a "
        "policy rule), its effect is reported as a sensitivity analysis next to the pre-specified result, which is "
        "never changed after the fact."
    )

    template_review_section.template_review(R, heading="4.3.7")

    R.h3("4.3.8 Retrieval configuration experiments")
    R.p(
        "Retrieval settings were varied one at a time, holding everything else fixed. Before the mid-semester "
        "review, the RAG arm was run with three chunks instead of eight, without the per-document cap, with an "
        "800-character chunk size (in a separately embedded index) and with the per-resource policy documents "
        "added. Those runs were scored against the earlier policy set, so their overall pass rates are comparable "
        "with each other and with `main-01` but not with the final run. For the final phase, the policy-pinning arm "
        "was run again with four and with twelve chunks, to check whether its result depends on the amount of "
        "retrieved context once policy no longer has to win a place in it. All configuration runs use three "
        "samples per task."
    )

    R.h3("4.3.9 User evaluation design")
    R.p(
        "The user evaluation measures usability, time to completion and developer trust (objective O6). The design "
        "below was set out in the mid-semester report and run as described, except where Section 5.10 states "
        "otherwise. The harness (instrument scoring, counterbalanced assignment, session recording and paired "
        "analysis) is in `src/ragiac/evaluation/user_study.py`."
    )
    R.table(
        ["Element", "Design"],
        [
            ["Participants", "8 engineers from the delivery team, voluntary: 4 with under one year of Terraform experience and 4 with two or more years."],
            ["Design", "Within-subjects and counterbalanced. Each participant completes four tasks: two with the assistant and two without it, using provider documentation and search as they normally would. Condition order alternates across participants."],
            ["Tasks", "Four tasks from the benchmark set (`gcs-01`, `gke-01`, `net-03`, `sql-03`), spanning difficulty levels 1 to 3. No customer or production information is used."],
            ["Objective measures", "Task success (the benchmark's automated validity and intent checks) and time to completion. The number of edits to the assistant's output was planned but not recorded."],
            ["Instruments", "System Usability Scale (10 items) [13] and a 12-item trust-in-automation scale [14], adapted to code generation, after the assistant condition; five semi-structured interview questions."],
            ["Analysis", "Exact Wilcoxon signed-rank tests on per-participant means, with rank-biserial effect sizes; SUS and trust scored in the standard way."],
            ["Ethics", "Informed consent, anonymised data, organisational permission, and the option to withdraw at any time."],
        ],
        [3.5, 12.5],
        "User-evaluation design.",
        font_size=9.5,
    )

    R.h3("4.3.10 Statistical treatment")
    R.p(
        "Proportions are reported with 95% Wilson score intervals [10], which behave sensibly at small sample sizes "
        "and at 0% and 100%. Because the same 33 headline tasks are run under every arm, arms are compared per "
        "task: for each task the mean overall pass rate of each arm is computed, and the number of tasks on which "
        "each arm is better is tested with an exact two-sided sign test. Five such comparisons are reported for the "
        "final run, so a single p-value near 0.05 should be read with that in mind. In the user evaluation, each "
        "participant contributes one pair of per-condition means to an exact Wilcoxon signed-rank test."
    )

    R.h3("4.3.11 Threats to validity")
    R.bullets(
        [
            "**Own task set, specifications and policies.** Tasks, intent checks, conventions and policies were written by the author. The failure analysis found one intent check that rejected correct answers (Section 5.7.5); others may exist that were not exposed by any arm's output.",
            "**Designed after seeing the earlier results.** The policy-pinning arm and the per-resource policy documents were designed in response to the earlier run, on the same task set. They were evaluated on new samples, but the task set is not independent of the design.",
            "**Simulated organisational documents.** The conventions, internal templates and policies stand in for a real organisation's. The template review checked their technical correctness, not whether they match real practice (Section 4.3.7).",
            "**Static intent checking.** Intent is checked on the parsed HCL; values computed through variables or `for_each` cannot be resolved, so tasks were written to avoid needing that.",
            "**One model, one temperature.** Results are for Gemini 3.8 Flash at temperature 0.8 (with a temperature 0 check in the earlier run) and should not be generalised to other models.",
            "**Sample size.** 33 headline tasks with five samples each give usable but wide intervals; category-level differences are indicative.",
            "**User evaluation.** Eight participants, a manual condition that some participants ran with a general-purpose AI assistant, and only two counterbalancing sequences (Section 5.10).",
        ]
    )


# ---- Chapter 6 ------------------------------------------------------------------------------------
def conclusion(R):
    R.h1("6. Conclusion and Future Scope")
    R.h2("6.1 Conclusion")
    R.p(
        "This dissertation built a RAG assistant that generates Terraform for Google Cloud from natural-language "
        "requirements and validates every output with Terraform, Open Policy Agent policies and intent checks. It "
        "was evaluated in a final benchmark of 35 tasks, five arms and 875 samples, in six further retrieval "
        "configuration runs, and with eight engineers. Every sample is stored with its retrieved context and "
        "diagnostics, so every figure in this report can be traced back to the generated code."
    )
    R.p(
        "**Technical correctness was not the problem.** The model wrote configurations that validate, plan and do "
        "what was asked in 96% to 100% of samples in every arm, with or without retrieval. On this task set, the "
        "value of grounding is not in fixing malformed code."
    )
    R.p(
        "**Policy was the problem, and getting policy to the model was most of the solution.** Without any "
        "organisational context, half of all configurations broke policy. Retrieval helped (overall pass 50.9% to "
        "67.3%) but left a large gap, because policy applies to every request without resembling any of them, so "
        "similarity search ranks it poorly. Indexing the policy per resource type tripled how often it was "
        "retrieved, but a retrieved policy chunk was still often not followed. Pinning the relevant policy pages in "
        "a mandatory prompt section closed most of the gap (93.3%), without pasting every document into the prompt. "
        "Pasting all the conventions in did slightly better again (99.4%), which is the practical choice while "
        "conventions are short."
    )
    R.p(
        "**The remaining failures point at the documents and the checks, not the model.** A rule written in prose "
        "that does not name the setting its enforcement checks (BigQuery retention) was missed in most samples of "
        "every arm that had only the prose. A defect in an internal template (point-in-time recovery for MySQL) was copied into "
        "generated code until the template was corrected. And one intent check rejected the correct answer and "
        "accepted a wrong one. For an organisation, this means that the quality of its written conventions and of "
        "its policy checks matters as much as the generator, and that automated policy validation remains "
        "essential: every arm built what was asked even when the request itself broke policy."
    )
    R.p(
        "**Engineers were faster with the assistant and moderately satisfied with it.** In the user evaluation, "
        "seven of eight participants completed tasks faster with the assistant, and the median time roughly halved. "
        "Usability was moderate (SUS 63.8) and trust above neutral. The comparison was weakened by uncontrolled AI "
        "use in the manual condition and by the small sample, so it shows a consistent direction rather than a "
        "reliable size of effect."
    )

    R.h2("6.2 Future scope")
    R.bullets(
        [
            "**Independent review of the internal templates.** Have the organisation's platform team review the templates and conventions against actual practice, which the technical self-review could not establish (Section 4.3.7).",
            "**A controlled repeat of the user evaluation.** Control and record tool use in the manual condition, record edits to the assistant's output, measure trust in both conditions, use a Latin-square task assignment, and conduct the interviews live (Section 5.10).",
            "**Policy written for enforcement.** Generate the policy pages and the Rego rules from one source, so that every enforced setting is named in the text the model sees (Section 5.7.3).",
            "**Policy pinning without a hand-written mapping.** Select policy pages from the resource types named in the request or in a first draft of the configuration, so that new resource types are covered automatically.",
            "**Verifier feedback at scale.** Run the verifier-feedback arm, already implemented, as a full benchmark arm combined with policy pinning; the earlier probe resolved nine of ten failures in one retry (Section 5.9).",
            "**Broader evaluation.** Further models, more tasks per category (including more data and analytics tasks), a second cloud provider, and apply-time validation in a sandbox project to catch errors that only the cloud API detects.",
            "**Corrected intent checks.** Correct the `gke-01` intent check to count nodes across zones and audit the other multi-zone checks in the same way (Section 5.7.5).",
        ]
    )

    R.h2("6.3 Plan of work as completed")
    R.p("The phases below are those of the approved outline.")
    R.table(
        ["Sl No", "Phases", "Start Date - End Date", "Work done", "Status"],
        [
            ["1", "Literature review and problem formulation", "25 Jul 2026 - 14 Aug 2026", "Review of LLM code generation, RAG and IaC benchmarks; problem formulated", "COMPLETED"],
            ["2", "Abstract / outline submission and evaluation", "15 Aug 2026 - 04 Sep 2026", "Dissertation outline prepared and submitted", "COMPLETED"],
            ["3", "RAG pipeline and knowledge-base design", "05 Sep 2026 - 25 Sep 2026", "Cloud, LLM, embedding model and vector store chosen; ingestion, retrieval, generation and validation designed", "COMPLETED"],
            ["4", "Prototype development and mid-semester evaluation", "26 Sep 2026 - 16 Oct 2026", "Working prototype on Vertex AI, first full benchmark, mid-semester report", "COMPLETED"],
            ["5", "Full implementation and validation tooling", "17 Oct 2026 - 06 Nov 2026", "Validation tooling, control and templates arms, retrieval ablations, near-greedy run, error analysis, verifier feedback, poisoning check, policy pinning, template review", "COMPLETED"],
            ["6", "Benchmarking, user evaluation and final report", "07 Nov 2026 - 30 Nov 2026", "Final benchmark and retrieval experiments, user evaluation with eight engineers, final report", "COMPLETED"],
        ],
        [1.2, 3.4, 3.3, 5.8, 2.3],
        "Plan of work and status.",
        font_size=9.5,
    )
