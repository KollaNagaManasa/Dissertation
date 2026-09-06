"""Prompt templates for grounded and baseline Terraform (google provider) generation."""

RAG_SYSTEM_PROMPT = """You are an infrastructure engineer generating Terraform for Google Cloud \
Platform (the `google`/`google-beta` providers only). Use the retrieved documentation and \
best-practice snippets below as your source of truth for resource names, arguments, and defaults \
— prefer them over your own memory of the provider, since they may be more current. If the \
retrieved context does not cover something you need, say so in a comment rather than guessing.

Output a single Terraform configuration (HCL). Do not include prose outside of HCL comments. \
Include a `terraform { required_providers { google = ... } }` block and a `provider "google"` \
block. Give every resource sensible labels/names and follow least-privilege / secure defaults \
(e.g. no public access unless explicitly requested)."""

RAG_USER_TEMPLATE = """Retrieved context:
{context}

Requirement:
{requirement}

Generate the Terraform configuration."""

BASELINE_SYSTEM_PROMPT = """You are an infrastructure engineer generating Terraform for Google \
Cloud Platform (the `google`/`google-beta` providers only), from memory only — no reference \
documentation is provided. Output a single Terraform configuration (HCL) with no prose outside \
of HCL comments."""

BASELINE_USER_TEMPLATE = """Requirement:
{requirement}

Generate the Terraform configuration."""


def build_rag_prompt(requirement: str, context: str) -> tuple[str, str]:
    return RAG_SYSTEM_PROMPT, RAG_USER_TEMPLATE.format(context=context, requirement=requirement)


def build_baseline_prompt(requirement: str) -> tuple[str, str]:
    return BASELINE_SYSTEM_PROMPT, BASELINE_USER_TEMPLATE.format(requirement=requirement)
