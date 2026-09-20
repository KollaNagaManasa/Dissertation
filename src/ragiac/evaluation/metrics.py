"""Metrics fixed in advance per the supervisor's remarks: validate/plan pass rate, OPA
policy-violation rate, pass@k — plus functional-intent pass rate and retrieval hit rate."""

import math
from collections import defaultdict
from typing import Iterable


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k estimator (Chen et al., 2021): probability that at least one of k samples
    drawn without replacement from n samples (c of them correct) is correct."""
    if k > n:
        raise ValueError("k cannot exceed the number of samples n")
    if n - c < k:
        return 1.0
    return 1.0 - math.prod(1.0 - k / i for i in range(n - c + 1, n + 1))


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval — behaves sensibly at small n and at 0%/100%."""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mean_pass_at_k(per_task_counts: Iterable[tuple[int, int]], k: int) -> float | None:
    """per_task_counts: (n_samples, n_correct) per task. Tasks with fewer than k samples are skipped."""
    values = [pass_at_k(n, c, k) for n, c in per_task_counts if n >= k]
    return sum(values) / len(values) if values else None


def retrieval_hit(expected: list, retrieved_resource_types: Iterable[str]) -> float | None:
    """Fraction of the resources a task needs that the retrieved chunks actually describe.

    `expected` entries are a resource type or a list of acceptable alternatives (e.g. IAM
    _member/_binding); `retrieved_resource_types` are the google_* resource types mentioned in the
    retrieved chunks. Matching on content rather than filenames matters: several files can describe
    one resource (org conventions + provider docs), and one IAM page covers several resource types.
    """
    if not expected:
        return None
    available = set(retrieved_resource_types)
    hits = sum(1 for entry in expected if available & ({entry} if isinstance(entry, str) else set(entry)))
    return hits / len(expected)


def group_counts(records: list[dict], predicate) -> dict[str, tuple[int, int]]:
    """Per-task (n, correct) for `predicate(record)`."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in records:
        counts[r["task_id"]][0] += 1
        counts[r["task_id"]][1] += 1 if predicate(r) else 0
    return {task: (n, c) for task, (n, c) in counts.items()}
