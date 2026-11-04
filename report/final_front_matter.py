"""Front matter and glossary for the final report, laid out per the WILP "Guidelines for the
preparation of a project report" (06.04.2022): cover (Appendix A), title page (Appendix B),
acknowledgements, abstract sheet (Appendix C, abstract <= 200 words, with key words and project
areas), then contents. Facts the repository cannot know are marked [[...]] so they are easy to find
and fill in before submission; build_final_report.py lists any that remain."""

from pathlib import Path

LOGO = Path(__file__).resolve().parent / "assets" / "bits_logo.png"

TITLE = "RAG-Powered Assistant for Infrastructure as Code Generation"
STUDENT = "Kolla Naga Manasa"
STUDENT_ID = "2024TM93519"
DISCIPLINE = "M.Tech. (Software Engineering)"
COURSE = "BITS SEZG628T Dissertation"
ORGANISATION = "Caprus IT Private Limited"
LOCATION = "Hyderabad"
SUPERVISOR = "Karthik Reddy Charla"
SUPERVISOR_DESIGNATION = "Technical Manager, Caprus IT Private Limited"
ADDITIONAL_EXAMINER = "Devoleena Das"
ADDITIONAL_EXAMINER_DESIGNATION = "Accenture Private Limited"
FACULTY_MENTOR = "Ashish Narang"
HEAD_OF_ORGANISATION = "____________________"  # left blank to fill in by hand
DATE_OF_START = "25 July 2026"
DATE_OF_SUBMISSION = ""  # left blank to fill in by hand
DURATION = ""  # left blank to fill in by hand
MONTH_YEAR = "November 2026"

KEY_WORDS = (
    "Retrieval-Augmented Generation; Infrastructure as Code; Terraform; Google Cloud; Large Language Models; "
    "Policy as Code; Open Policy Agent; Developer Trust"
)
PROJECT_AREAS = "Cloud Computing; DevOps; Software Engineering; Applied Artificial Intelligence"


def cover(R):
    """Appendix A: specimen of cover."""
    R.logo(LOGO, width_cm=3.5, after=12)
    R.centred("**BIRLA INSTITUTE OF TECHNOLOGY & SCIENCE, PILANI**", size=13, after=40)
    R.centred("**A REPORT**", size=14, after=10)
    R.centred("**ON**", size=14, after=10)
    R.centred(f"**{TITLE.upper()}**", size=16, after=60)
    R.centred("**BY**", size=14, after=30)
    R.centred(f"**Name of the Student:** {STUDENT}        **ID No.:** {STUDENT_ID}", size=12, after=40)
    R.centred("**AT**", size=14, after=24)
    R.centred(f"**{ORGANISATION}, {LOCATION}**", size=13, after=6)


def title_page(R):
    """Appendix B: specimen of title page."""
    R.page_break()
    R.centred("**BIRLA INSTITUTE OF TECHNOLOGY & SCIENCE, PILANI**", size=13, after=8)
    R.centred(f"**{MONTH_YEAR}**", size=12, after=50)
    R.centred("**A REPORT**", size=14, after=10)
    R.centred("**ON**", size=14, after=10)
    R.centred(f"**{TITLE.upper()}**", size=16, after=50)
    R.centred("**BY**", size=14, after=24)
    R.centred(f"**Name of the Student:** {STUDENT}", size=12, after=4)
    R.centred(f"**ID No.:** {STUDENT_ID}", size=12, after=4)
    R.centred(f"**Discipline:** {DISCIPLINE}", size=12, after=30)
    R.centred("Prepared in partial fulfilment of the", size=12, after=2)
    R.centred(f"WILP Dissertation course ({COURSE})", size=12, after=40)
    R.centred("**AT**", size=14, after=24)
    R.centred(f"**{ORGANISATION}, {LOCATION}**", size=13, after=6)


def acknowledgements(R):
    """Thanks in the order the guideline prescribes: head of organisation, supervisor and additional
    examiner, professional expert / in-charge, faculty mentor, others."""
    R.h1("Acknowledgements", page_break=False)
    R.p(
        f"I thank {HEAD_OF_ORGANISATION} for allowing this dissertation to be carried out at {ORGANISATION} "
        "and for the organisational support it needed."
    )
    R.p(
        f"I am grateful to my supervisor, {SUPERVISOR}, for guidance throughout the project and for the "
        f"freedom to pursue the questions the results raised, and to the additional examiner, "
        f"{ADDITIONAL_EXAMINER}, for reviewing the work."
    )
    R.p(
        f"I thank my faculty mentor, {FACULTY_MENTOR}, for the mid-semester review, whose comments on "
        "policy retrieval, internal templates, retrieval experiments, failure analysis, user assessment and "
        "the structure of this report shaped the final phase of the work."
    )
    R.p(
        "Finally, I thank the eight colleagues from the delivery team who gave their time to take part in the "
        "user evaluation."
    )


def abstract_sheet(R, abstract_text: str):
    """Appendix C: specimen of abstract sheet. The abstract itself is limited to 200 words."""
    words = len(abstract_text.split())
    if words > 200:
        raise ValueError(f"The WILP guideline limits the abstract to 200 words; this one has {words}.")
    R.page_break()
    R.centred(f"**{MONTH_YEAR}**", size=11, after=10)
    R.centred("**BIRLA INSTITUTE OF TECHNOLOGY AND SCIENCE, PILANI (RAJASTHAN)**", size=12, after=2)
    R.centred("**WILP Division**", size=12, after=18)
    R.labelled("Organization", f"{ORGANISATION}        **Location:** {LOCATION}")
    R.labelled("Duration", f"{DURATION}        **Date of Start:** {DATE_OF_START}")
    R.labelled("Date of Submission", DATE_OF_SUBMISSION)
    R.labelled("Title of the Project", TITLE)
    R.labelled("ID No./Name of the student", f"{STUDENT_ID} / {STUDENT}")
    R.labelled(
        "Name(s) and Designation(s) of Supervisor and Additional Examiner",
        f"{SUPERVISOR}, {SUPERVISOR_DESIGNATION} (Supervisor); {ADDITIONAL_EXAMINER}, "
        f"{ADDITIONAL_EXAMINER_DESIGNATION} (Additional Examiner)",
    )
    R.labelled("Name of the Faculty mentor", FACULTY_MENTOR)
    R.labelled("Key Words", KEY_WORDS)
    R.labelled("Project Areas", PROJECT_AREAS)
    R.labelled("Abstract", "")
    for block in [b.strip() for b in abstract_text.split("\n\n") if b.strip()]:
        para = R.p(block)
        para.paragraph_format.line_spacing = 1.15
    R.signature_block(
        ["Signature of Student", f"Name: {STUDENT}", "Date:"],
        ["Signature of Supervisor", f"Name: {SUPERVISOR}", "Date:"],
    )


GLOSSARY = [
    ("Arm", "One generation strategy compared in the benchmark (baseline, RAG, conventions-in-prompt, templates, RAG with pinned policy)."),
    ("Chunk", "A fragment of a knowledge-base document, embedded and stored as one unit for retrieval."),
    ("Conftest", "A command-line tool that evaluates Open Policy Agent (Rego) policies against configuration files."),
    ("Embedding", "A numeric vector representing the meaning of a text, used to find similar texts."),
    ("Functional pass", "A sample that passes terraform validate, terraform plan and the task's intent check."),
    ("Hit rate (retrieval)", "The share of resource types a task needs whose documentation appears in the retrieved chunks."),
    ("Infrastructure as Code (IaC)", "Describing cloud infrastructure in version-controlled declarative files instead of manual set-up."),
    ("Intent check", "An automated check that a configuration contains the resources and settings the requirement asked for."),
    ("Knowledge base", "The documents the assistant retrieves from: pinned provider documentation and organisational conventions."),
    ("Large language model (LLM)", "A neural network trained on large text corpora that generates text, including code, from a prompt."),
    ("Open Policy Agent (OPA)", "A general-purpose policy engine; policies are written in the Rego language."),
    ("Overall pass", "A functional pass that also has no organisational-policy violation."),
    ("pass@k", "The probability that at least one of k samples for a task passes, estimated without bias from n >= k samples."),
    ("Pinned policy", "Organisational policy text placed in a fixed, mandatory section of the prompt rather than ranked by retrieval."),
    ("Policy as code", "Organisational rules expressed as machine-checkable policies (here, Rego) rather than prose."),
    ("Provider (Terraform)", "The plugin that maps Terraform resources onto a cloud's API; here hashicorp/google."),
    ("Retrieval-Augmented Generation (RAG)", "Generating text with retrieved documents placed in the model's context."),
    ("Sign test", "A non-parametric test of whether one arm wins more paired comparisons than the other."),
    ("System Usability Scale (SUS)", "A 10-item questionnaire giving a usability score from 0 to 100."),
    ("terraform plan", "Terraform's dry run, which checks a configuration against the provider and the cloud API without changing anything."),
    ("terraform validate", "Terraform's static check of syntax and provider schema."),
    ("Vertex AI", "Google Cloud's managed machine-learning platform, used here for embeddings and Gemini generation."),
    ("Wilcoxon signed-rank test", "A non-parametric test for paired measurements, used here for the user evaluation."),
    ("Wilson interval", "A confidence interval for a proportion that behaves well for small samples and extreme rates."),
]


def glossary(R):
    R.h1("Glossary")
    R.p("Technical terms used in this report. Abbreviations are listed separately.")
    R.table(["Term", "Meaning"], [list(g) for g in GLOSSARY], [4.6, 10.4], "Glossary of technical terms.", font_size=9.5)
