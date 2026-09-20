"""Prompt templates for grounded and baseline Terraform (google provider) generation.

Both arms are told the same target provider version: it is part of the task specification (the
generated code is validated against it, and the retrieved docs describe it), and leaving it to the
model's memory would confound the RAG-vs-baseline comparison with version skew. Keep in sync with
ragiac.ingestion.provider_docs.DEFAULT_TAG.
"""

TARGET_PROVIDER_CONSTRAINT = "~> 8.0"
_TARGET_LINE = (
    f"Target provider: `hashicorp/google` with version constraint `{TARGET_PROVIDER_CONSTRAINT}` "
    "(use exactly this constraint in required_providers)."
)

RAG_SYSTEM_PROMPT = """You are an infrastructure engineer generating Terraform for Google Cloud \
Platform (the `google`/`google-beta` providers only). Use the retrieved documentation and \
best-practice snippets below as your source of truth for resource names, arguments, and defaults \
— prefer them over your own memory of the provider, since they may be more current. If the \
retrieved context does not cover something you need, say so in a comment rather than guessing.

Output a single Terraform configuration (HCL). Do not include prose outside of HCL comments. \
Include a `terraform { required_providers { google = ... } }` block and a `provider "google"` \
block. Give every resource sensible labels/names and follow least-privilege / secure defaults \
(e.g. no public access unless explicitly requested)."""
RAG_SYSTEM_PROMPT += " " + _TARGET_LINE

RAG_USER_TEMPLATE = """Retrieved context:
{context}

Requirement:
{requirement}

Generate the Terraform configuration."""

BASELINE_SYSTEM_PROMPT = """You are an infrastructure engineer generating Terraform for Google \
Cloud Platform (the `google`/`google-beta` providers only), from memory only — no reference \
documentation is provided. Output a single Terraform configuration (HCL) with no prose outside \
of HCL comments."""
BASELINE_SYSTEM_PROMPT += " " + _TARGET_LINE

BASELINE_USER_TEMPLATE = """Requirement:
{requirement}

Generate the Terraform configuration."""


def build_rag_prompt(requirement: str, context: str) -> tuple[str, str]:
    return RAG_SYSTEM_PROMPT, RAG_USER_TEMPLATE.format(context=context, requirement=requirement)


def build_baseline_prompt(requirement: str) -> tuple[str, str]:
    return BASELINE_SYSTEM_PROMPT, BASELINE_USER_TEMPLATE.format(requirement=requirement)
