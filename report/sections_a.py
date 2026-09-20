"""Report sections 1-2: introduction and literature review."""


def introduction(R):
    R.h1("1. Introduction")

    R.h2("1.1 Background and motivation")
    R.p(
        "Infrastructure as Code (IaC) is now the standard way of provisioning and managing cloud resources: "
        "the desired infrastructure is described declaratively in version-controlled files, and a tool such as "
        "Terraform reconciles the real environment with that description. Writing correct IaC is nevertheless "
        "difficult. Provider schemas are large and change frequently (the Google Cloud provider used in this work "
        "was at major version 8 at the time of writing), resources depend on one another in ways that the "
        "documentation only describes indirectly, and every organisation layers its own conventions and security "
        "policies on top."
    )
    R.p(
        "Large language models (LLMs) can turn a plain-English requirement into a plausible Terraform "
        "configuration, but plausibility is not correctness. A model's knowledge is frozen at training time, so it "
        "tends to produce arguments that have been renamed or removed, omits arguments that are now required, and "
        "knows nothing about the conventions of the organisation it is being used in. Retrieval-Augmented "
        "Generation (RAG) addresses exactly this weakness by placing retrieved, current documentation in the "
        "model's context at generation time instead of relying on what the model memorised."
    )
    R.p(
        "The problem is directly relevant to the author's employer, Caprus IT, where delivery work provisions "
        "infrastructure largely through Terraform and where misconfiguration and the slow onboarding of new "
        "engineers continue to cost time. An assistant that converts plain-language requirements into validated, "
        "policy-compliant IaC would reduce authoring effort and lower the rate of misconfiguration-related incidents."
    )

    R.h2("1.2 Problem statement")
    R.p(
        "Given a natural-language infrastructure requirement, generate Terraform for Google Cloud Platform (GCP) "
        "that (a) is well-formed and consistent with the provider's schema, (b) actually implements what was "
        "asked, and (c) complies with organisational policy. The central research question is whether retrieval "
        "over provider documentation and organisational conventions improves these outcomes compared with the same "
        "model used without retrieval, and, where it does not, what kinds of errors remain."
    )

    R.h2("1.3 Objectives and current status")
    R.p("The objectives set out in the approved outline, and where each stands at the mid-semester point, are:")
    R.table(
        ["#", "Objective (from the outline)", "Status at mid-semester"],
        [
            ["O1", "Study the state of the art in LLM-based code generation and RAG for IaC", "Done for this report (Section 2); continues through the final report"],
            ["O2", "Identify common LLM error categories in IaC generation and the knowledge gaps retrieval must close", "Taxonomy implemented and applied to every benchmark sample (Sections 5.4, 6)"],
            ["O3", "Design a RAG architecture (ingestion, chunking, embedding, vector storage, retrieval, generation)", "Done (Section 3)"],
            ["O4", "Build a working prototype that generates IaC from natural-language prompts", "Done: runs end to end on real GCP services (Sections 3, 4)"],
            ["O5", "Validate output with automated tooling and benchmark against a non-RAG baseline", "Tooling done; full benchmark, control arm, retrieval ablations and a near-greedy run reported (Section 6); chunk-size ablation not run"],
            ["O6", "User evaluation of usability and developer trust", "Designed and proposed (Section 8.2); to be run in Phase 6"],
        ],
        [1.1, 8.2, 6.7],
        "Objectives and their status.",
    )

    R.h2("1.4 Scope")
    R.p(
        "The work designs, implements and evaluates a RAG-based assistant that accepts natural-language "
        "infrastructure requirements and produces Terraform for Google Cloud, grounded in a curated knowledge base "
        "of provider documentation and organisational conventions. Production deployment, multi-cloud coverage "
        "beyond GCP, and continuous-integration rollout are outside the scope of this dissertation and are noted "
        "as future work. The assistant is never used to apply infrastructure: generated code is only validated and "
        "planned."
    )

    R.h2("1.5 Organisation of this report")
    R.p(
        "Section 2 reviews related work. Section 3 describes the system design and the reasoning behind each "
        "technology choice. Section 4 covers implementation, reproducibility and the engineering problems found "
        "and fixed along the way. Section 5 sets out the evaluation methodology, including the metrics, which were "
        "fixed before any results were collected. Sections 6 and 7 present and discuss the results of the first "
        "full benchmark. Section 8 describes the remaining work, including the proposed user evaluation, and "
        "Section 9 concludes."
    )


def literature(R):
    R.h1("2. Literature Review")

    R.h2("2.1 Retrieval-Augmented Generation")
    R.p(
        "Lewis et al. [1] introduced Retrieval-Augmented Generation as a way of combining a generator's "
        "parametric memory (knowledge stored in model weights) with a non-parametric memory: a dense index of "
        "documents that is queried at inference time and whose results condition the output. Two properties make "
        "the approach attractive for infrastructure code. The knowledge source can be updated without retraining the "
        "model, which matters when provider schemas change every few weeks, and the retrieved passages give "
        "generated output a traceable provenance. Khan et al. [8] report the practical side of building such "
        "systems, describing the end-to-end pipeline from data collection and preprocessing through retrieval "
        "indexing to response generation and the technical problems that arise at each stage. The present system "
        "follows the same staged decomposition."
    )

    R.h2("2.2 LLMs for infrastructure code and their benchmarks")
    R.p(
        "IaC-Eval [2] is, to our knowledge, the first dedicated benchmark for LLM-generated Terraform. It "
        "contains 458 human-curated scenarios and goes beyond syntax by checking whether a generated configuration "
        "satisfies an explicit intent specification. Its released tooling targets AWS, with other providers left as "
        "future work. This design, in which validity and intent are separate questions, is the model for the "
        "intent checks used in this work. Multi-IaC-Eval [5] extends evaluation across AWS CloudFormation, "
        "Terraform and CDK and reports that modern LLMs achieve success rates above 95% in generating syntactically "
        "valid IaC across formats, while semantic alignment and complex infrastructure patterns remain difficult. "
        "Taken together, these results show that syntactic validity is close to saturated for strong models and is "
        "therefore an insufficient measure of quality on its own."
    )

    R.h2("2.3 Error taxonomies and knowledge injection")
    R.p(
        "The closest prior work to this dissertation is that of Nekrasov et al. [3], who propose an error taxonomy "
        "for LLM-generated Terraform and enhance IaC-Eval with cloud emulation and automated error analysis. They "
        "compare knowledge-injection strategies that progress from naive RAG to Graph RAG with semantic enrichment "
        "and inter-resource dependency modelling. Their reported baseline LLM success is 27.1% overall; with "
        "knowledge injection, technical validation success rises to 75.3% and overall success to 62.6%. They "
        "identify a \"Correctness-Congruence Gap\": models become proficient coders but remain limited as "
        "architects in satisfying nuanced user intent. This is the reason the present evaluation reports "
        "well-formedness and intent satisfaction as separate quantities rather than a single score."
    )

    R.h2("2.4 Verifier-based evaluation and policy compliance")
    R.p(
        "Jouini [4] evaluates seven agentic strategies for Terraform generation on a 186-task benchmark using "
        "three verifier stages: terraform validate, terraform plan and OPA policy evaluation. Active retrieval "
        "raised the pass@1 of one small open model from 14.0% to 45.7% by reducing validation failures, and "
        "iterative refinement with verifier feedback reached 62.9% and 84.4% pass@1 for two further models. A "
        "finding that bears directly on this design is that 79% of the OPA failures remaining after refinement "
        "were information-gap failures that could be resolved when the policy text was visible to the model. "
        "That supports placing organisational conventions in the retrieval corpus, which is what this work does, "
        "and it motivates the same three verifier stages here."
    )
    R.p(
        "Vargas et al. [6] benchmark seven proprietary and open models on secure AWS Terraform generation across "
        "17 scenarios using Checkov and Trivy. They conclude that code validity and security are largely "
        "orthogonal properties and that prompt engineering alone is insufficient, so automated scanning remains "
        "necessary. The consequence for the present study is that technical correctness and policy compliance "
        "are reported as distinct dimensions (Section 5.3) so that the effect of retrieval on each can be seen "
        "separately."
    )

    R.h2("2.5 Risks introduced by retrieval")
    R.p(
        "Retrieval also adds an attack surface. Ye et al. [7] describe ImportSnare, an attack in which poisoned "
        "documentation steers a retrieval-augmented code generator toward malicious dependencies; they report "
        "attack success rates above 50% for some popular libraries and success even at a poisoning ratio as low "
        "as 0.01%. Although their setting is package recommendation rather than infrastructure, the lesson "
        "transfers: whatever enters the knowledge base can shape the generated code. This work therefore "
        "restricts the corpus to a pinned release of the official provider documentation plus a small set of "
        "reviewed organisational conventions, and accepts no user-contributed content (Section 3.4)."
    )

    R.h2("2.6 Gap addressed by this work")
    R.p(
        "In the literature reviewed for this report, evaluation of LLM-generated Terraform is concentrated on "
        "AWS, and we did not find a GCP-specific benchmark. Existing studies also tend to report a single "
        "success figure; the combination of separate technical, intent and organisational-policy measurements, "
        "a per-sample error taxonomy, and a paired retrieval-versus-no-retrieval comparison on the same model "
        "and prompt is the contribution attempted here, for Google Cloud. The task set built for this purpose "
        "(Section 5.2) follows IaC-Eval's intent-specification approach but is a new, GCP-specific set of 35 "
        "tasks, so its results are not directly comparable to figures published for the AWS benchmarks."
    )
