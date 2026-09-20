"""Report sections 3-4: system design, implementation and engineering findings."""

from pathlib import Path

FIG = Path(__file__).resolve().parent / "figures"


def _count_tests() -> str:
    """Number of collected pytest tests, so the report can't drift from the code."""
    import re
    import subprocess
    import sys

    root = Path(__file__).resolve().parent.parent
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=root, capture_output=True, text=True, timeout=120
        ).stdout
        match = re.search(r"(\d+) tests? collected", out)
        return match.group(1) if match else "over a hundred"
    except (OSError, subprocess.SubprocessError):
        return "over a hundred"


def design(R):
    R.h1("3. System Design")

    R.h2("3.1 Design principles")
    R.p("Five principles guided the design, each chosen so that the eventual results can be trusted.")
    R.numbered(
        [
            "**A controlled comparison.** The two experimental arms use the same model, prompt template, target provider version and sampling settings. They differ in one respect only: whether retrieved context is supplied. Any difference in outcome can then be attributed to retrieval.",
            "**Everything is measurable.** Each stage exposes its output so that failures can be attributed to retrieval, generation or validation rather than to the system as a whole.",
            "**Safety by construction.** Generated code is only ever validated and planned, never applied, and planning runs against a dedicated experimentation project.",
            "**Reproducibility.** Every run records the model, temperature, index size, tool versions, source-document release and hashes of the task file and policies, and stores every generated configuration.",
            "**Provenance.** The knowledge base contains only public provider documentation, pinned to a release, and reviewed organisational conventions; no customer or production configuration is used.",
        ]
    )

    R.h2("3.2 Architecture")
    R.p(
        "Figure 1 shows the pipeline. An offline stage builds the knowledge base: documents are cleaned, "
        "split into chunks, embedded and stored in a vector index. At run time a requirement is either passed "
        "through the retriever (RAG arm) or straight to the model (baseline arm); the generated Terraform then "
        "passes through the same validation and evaluation stages regardless of arm."
    )
    R.figure(FIG / "architecture.png", 16.0, "System architecture: offline knowledge-base construction, online generation for the two experimental arms, and identical validation for both.")

    R.h2("3.3 Technology choices")
    R.p(
        "Table 2 lists the choices that the supervisor asked to be settled and stated at this stage, with the "
        "reasoning for each."
    )
    R.table(
        ["Concern", "Choice", "Rationale"],
        [
            ["Cloud and IaC tool", "Google Cloud Platform; Terraform with the `google` provider (`~> 8.0`)", "Terraform is the delivery team's tool; GCP is the cloud used for all experimentation."],
            ["Region", "`asia-south1` (Mumbai) for storage and embeddings", "Google Cloud has no region in Hyderabad. Of its two Indian regions, Mumbai is roughly 600 km away versus roughly 1,350 km for Delhi, and no cost reason to prefer Delhi was identified, so proximity decided it."],
            ["Generation model", "Gemini 3.8 Flash on Vertex AI, global endpoint", "The current general-availability Flash model. `gemini-2.0-flash` no longer exists on Vertex AI and `gemini-2.5-flash` is scheduled to shut down on 20 October 2026, inside this project's timeline. The global endpoint avoids losing access to newer models that are not yet regional."],
            ["Embeddings", "Vertex AI `text-embedding-005` (768 dimensions)", "Supports separate document and query task types, which the model is trained to expect for asymmetric retrieval."],
            ["Vector store", "In-memory exact cosine search, persisted to disk", "See Section 3.3.1."],
            ["Policy engine", "Open Policy Agent via Conftest 0.70.0 (OPA 1.20.2)", "Policy-as-code checks named in the outline; Rego rules are versioned with the code."],
            ["Validation", "Terraform 1.16.2: init, validate, plan", "Standard tool-level verification; plan is read-only."],
        ],
        [3.0, 5.3, 7.7],
        "Technology choices and rationale.",
    )

    R.h3("3.3.1 Vector store decision")
    R.p(
        "The knowledge base is about 1,000 chunks (roughly 1 MB of text). At that size an exact cosine search "
        "over an in-memory matrix returns in well under a millisecond and needs no infrastructure. Vertex AI "
        "Vector Search is an approximate-nearest-neighbour service designed for very large corpora and is billed "
        "while an index endpoint is deployed, so at this scale it would add cost and operational overhead without "
        "improving retrieval quality. The vector store sits behind a small interface and a Vertex AI Vector "
        "Search implementation is already written, so moving to it is a configuration change if the corpus grows "
        "substantially. The decision is therefore an in-memory store for the dissertation, with a documented "
        "migration path."
    )

    R.h2("3.4 Knowledge base")
    R.p(
        "The knowledge base combines two sources. The first is 47 pages of public documentation for the "
        "`google` Terraform provider, taken from release v8.3.0 of the official repository (MPL-2.0 licence). "
        "The pages cover the resources most often needed for common infrastructure: storage, networking, "
        "compute, databases, Kubernetes, serverless, messaging, analytics, security, and platform services such "
        "as Artifact Registry and DNS. Each page is cleaned by removing generated front matter and the import and "
        "timeout sections, which add noise without helping generation; a comment recording the source URL, release "
        "and licence is added to the top."
    )
    R.p(
        "The second source is a set of four short documents written for this project that state organisational "
        "conventions in the form a practitioner would document them: the default region, mandatory `environment` "
        "labels, no public exposure unless explicitly requested, deletion protection and backups for production "
        "data stores, and regional over zonal configurations for production. They stand in for the sanitised "
        "internal templates the supervisor asked to be used; replacing them with reviewed internal templates is "
        "a remaining task (Section 8)."
    )
    R.p(
        "Because retrieved text shapes generated code, the corpus is treated as a trust boundary (Section 2.5). "
        "It is fetched over HTTPS from the official repository at a pinned tag, is regenerated by a script rather "
        "than edited by hand, and contains no customer, production or credential data."
    )

    R.h2("3.5 Chunking and retrieval")
    R.p(
        "Provider documentation is long: a single resource page can run to tens of thousands of characters, and "
        "its most valuable content is a fenced HCL example whose lines must stay together. A plain paragraph "
        "splitter would cut examples at blank lines. The chunker therefore keeps fenced code blocks whole, splits "
        "oversized blocks only at line boundaries and re-fences each piece, and prefixes every chunk with its "
        "heading path (for example, `[google_storage_bucket > Argument Reference]`) so that a chunk from the middle "
        "of a long argument list still identifies the resource it describes. The corpus yields 1,034 chunks with a "
        "1,500-character target."
    )
    R.p(
        "Queries are embedded with the retrieval-query task type and chunks with the retrieval-document type. "
        "The retriever returns the eight most similar chunks with at most three from any single document. The cap "
        "was added after inspection showed that a long page could fill every slot: for a requirement asking for "
        "a VPC with subnets and Cloud NAT, the top eight results came entirely from the NAT and subnetwork pages "
        "and none described the network resource itself. Even with the cap, retrieval remains imperfect, which "
        "is why retrieval quality is measured explicitly (Section 5.4) rather than assumed."
    )

    R.h2("3.6 Generation")
    R.p(
        "The system prompt tells the model it is generating Terraform for GCP, to treat retrieved documentation "
        "as authoritative in preference to its own memory, to say so in a comment when the retrieved context does "
        "not cover something rather than guessing, to include provider and required-provider blocks, and to follow "
        "secure defaults. The baseline prompt is identical except that it omits the retrieval instructions and "
        "states that no reference material is provided. Both prompts name the target provider version constraint, "
        "because otherwise a model that recalls an older provider from memory would be validated against a "
        "different schema from the one the retrieved documents describe, confounding the comparison."
    )
    R.p(
        "Model replies are post-processed to extract the Terraform: models often wrap code in a Markdown fence "
        "and sometimes add commentary, and newer models can return several content parts. Transient quota "
        "errors are retried with exponential backoff and jitter."
    )

    R.h2("3.7 Validation stack")
    R.p("Generated code is checked at three levels, each answering a different question (Table 3).")
    R.table(
        ["Level", "Tool", "Question answered", "Example failure it catches"],
        [
            ["Well-formed", "`terraform init` and `validate`", "Is the code syntactically valid and consistent with the provider schema?", "An argument that does not exist in provider v8"],
            ["Plannable", "`terraform plan` (read-only)", "Can Terraform build an execution plan against the real API?", "An invalid combination of values rejected by the provider"],
            ["Policy-compliant", "OPA through Conftest", "Does it obey organisational policy?", "A bucket with no `environment` label; an `allUsers` IAM grant; a firewall open to 0.0.0.0/0"],
            ["Intent-satisfying", "Task-specific intent checks", "Did it build what was asked?", "A valid, compliant configuration for the wrong resource, or with the wrong retention period"],
        ],
        [2.6, 3.6, 4.9, 4.9],
        "The four validation levels.",
    )
    R.p(
        "Three details matter for the credibility of the measurements. First, plan failures caused by the "
        "environment (missing credentials) or by a variable declared without a default are recorded but not "
        "counted against the model, since they say nothing about the code. Second, when the policy engine cannot "
        "parse a configuration at all, that is recorded as a syntax failure and not as a policy violation. Third, "
        "the policy rules were verified against known-violating and known-compliant configurations, because policy "
        "code can fail silently (Section 4.4)."
    )

    R.h2("3.8 Safety")
    R.p(
        "The system never runs `terraform apply`. Plan runs only against a dedicated experimentation project "
        "and is read-only. Credentials are Application Default Credentials held locally, and no secrets are "
        "stored in the repository."
    )


def implementation(R):
    R.h1("4. Implementation")

    R.h2("4.1 Code base")
    R.p(
        "The prototype is a Python package organised by pipeline stage: ingestion, embeddings, vector store, "
        "retrieval, generation, validation and evaluation. Every external dependency (Vertex AI, terraform, "
        "conftest) sits behind a small interface, which allows the full pipeline to run offline in a development "
        "mode and lets unit tests substitute fakes. A browser interface built with Streamlit lets a user submit a "
        "requirement and see the retrieved context, the generated Terraform and the validation results side by "
        f"side, and browse stored benchmark runs. The code base has {_count_tests()} automated tests, including "
        "integration tests that run the real policy engine."
    )
    R.p(
        "A rule-based template generator exists so that the pipeline can be exercised without cloud credentials. "
        "It is not a language model, is clearly labelled as such in its output, and none of the results in this "
        "report come from it."
    )

    R.h2("4.2 Reproducibility")
    R.p(
        "Each benchmark run writes a manifest recording the git commit, model, sampling temperature, embedding "
        "model, chunking and retrieval settings, index size, provider-documentation release, target provider "
        "constraint, Terraform and Conftest versions, and hashes of the task file and the policy files. Every "
        "generated configuration, its retrieved chunks and the full validator diagnostics are stored per sample, "
        "and all summary statistics are computed from those stored records, so a table in this report can be "
        "regenerated or audited from the raw data. Runs are resumable, and samples lost to infrastructure "
        "failure can be re-run without touching the rest."
    )

    R.h2("4.3 Local development mode")
    R.p(
        "For offline development the pipeline substitutes a TF-IDF embedder, the in-memory vector store and the "
        "rule-based template generator. This mode is used for testing the plumbing only."
    )

    R.h2("4.4 Engineering problems found and fixed")
    R.p(
        "Building the evaluation infrastructure produced a number of defects, several of which would have "
        "silently distorted results had they not been found. They are recorded here because they show why the "
        "measurement tooling needed its own testing, and because they are candidate entries for the error "
        "analysis of tool-assisted generation."
    )
    R.table(
        ["Problem", "Effect if unnoticed", "Fix"],
        [
            ["Model reply wrapped in a Markdown fence", "`terraform init` fails on every sample, so every sample would count as a syntax error", "Extract the HCL from fenced replies, including replies with surrounding prose or a truncated closing fence"],
            ["Newer model returns several content parts", "Text accessor raises; samples lost or mis-scored", "Join text parts, skip reasoning parts; found during the first full run"],
            ["Model identifier retired (`gemini-2.0-flash`)", "All generation fails with a 404", "Moved to the current GA model and recorded the shutdown date of the alternative"],
            ["Retry caught the wrong exception class for HTTP 429", "No retries; ingestion and generation fail under quota limits", "Catch the REST transport's exception; regression test added"],
            ["Policy rules written for an older Rego syntax and ignoring the parser's list wrapping", "One rule denied every resource, another never fired, so public resources would have passed", "Rules rewritten and tested against known-bad and known-good configurations"],
            ["Re-ingestion appended instead of replacing chunks", "Duplicate chunks skew retrieval", "Idempotent upsert by chunk identifier"],
            ["Retrieval hit measured by filename", "Under-reports retrieval quality, because several files describe one resource", "Match on the resource types the retrieved text actually mentions"],
            ["Variables without defaults counted as plan failures", "Idiomatic code penalised for something plan cannot evaluate", "Classified as not evaluable, alongside credential errors"],
        ],
        [4.6, 5.6, 5.8],
        "Defects found in the tooling and their remedies.",
    )
