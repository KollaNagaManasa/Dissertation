"""Harness for Objective O6 (user evaluation of usability and developer trust), implementing the
design proposed in Section 8.2: 8 participants (4 with under a year of Terraform experience, 4
with two or more), within-subjects and counterbalanced, 4 matched tasks each, comparing the
`assistant` condition against a `manual` (no-assistant) baseline.

This module builds the instrument scoring, counterbalanced task/condition assignment, session
recording and paired analysis so the study is ready to run once approved (Phase 6, per
sections_c.py). It ships no participant data of its own.
"""

import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

EXPERIENCE_LEVELS = ("under_1y", "2y_plus")
CONDITIONS = ("assistant", "manual")

# --- System Usability Scale (Brooke, 1996), cited in sections_c.py references ---

SUS_ITEMS = (
    "I think that I would like to use this system frequently.",
    "I found the system unnecessarily complex.",
    "I thought the system was easy to use.",
    "I think that I would need the support of a technical person to be able to use this system.",
    "I found the various functions in this system were well integrated.",
    "I thought there was too much inconsistency in this system.",
    "I would imagine that most people would learn to use this system very quickly.",
    "I found the system very cumbersome to use.",
    "I felt very confident using the system.",
    "I needed to learn a lot of things before I could get going with this system.",
)
_SUS_POSITIVE = {1, 3, 5, 7, 9}  # odd items (1-indexed) are positively worded, even negatively


def score_sus(responses: list[int]) -> float:
    """responses: 10 Likert ratings (1 strongly disagree .. 5 strongly agree) in item order.
    Returns the standard 0-100 SUS score."""
    if len(responses) != len(SUS_ITEMS):
        raise ValueError(f"expected {len(SUS_ITEMS)} responses, got {len(responses)}")
    if any(not 1 <= r <= 5 for r in responses):
        raise ValueError("SUS responses must be on a 1-5 scale")
    total = sum((r - 1) if (i + 1) in _SUS_POSITIVE else (5 - r) for i, r in enumerate(responses))
    return total * 2.5


# --- Trust in automation (Jian, Bisantz & Drury, 2000), cited in sections_c.py references ---

TRUST_ITEMS = (
    "The system is deceptive.",
    "The system behaves in an underhanded manner.",
    "I am suspicious of the system's intent, action, or outputs.",
    "I am wary of the system.",
    "The system's actions will have a harmful or injurious outcome.",
    "I am confident in the system.",
    "The system provides security.",
    "The system has integrity.",
    "The system is dependable.",
    "The system is reliable.",
    "I can trust the system.",
    "I am familiar with the system.",
)
_TRUST_REVERSE = {1, 2, 3, 4, 5}  # distrust statements, reverse-scored


def score_trust(responses: list[int]) -> float:
    """responses: 12 ratings (1 not at all .. 7 extremely) in item order. Returns the mean item
    score (1-7) after reverse-scoring the distrust items."""
    if len(responses) != len(TRUST_ITEMS):
        raise ValueError(f"expected {len(TRUST_ITEMS)} responses, got {len(responses)}")
    if any(not 1 <= r <= 7 for r in responses):
        raise ValueError("trust responses must be on a 1-7 scale")
    recoded = [(8 - r) if (i + 1) in _TRUST_REVERSE else r for i, r in enumerate(responses)]
    return sum(recoded) / len(recoded)


# --- Counterbalanced within-subjects design ---


@dataclass(frozen=True)
class Participant:
    id: str
    experience: str  # one of EXPERIENCE_LEVELS


def assign_conditions(participant_index: int, n_tasks: int) -> list[str]:
    """Condition per task slot for the participant at `participant_index` (0-based): alternates
    assistant/manual by slot, flipping the starting condition on alternating participants, so
    across any even number of participants each slot and each condition get equal exposure."""
    start = participant_index % 2
    return [CONDITIONS[(start + slot) % 2] for slot in range(n_tasks)]


def build_schedule(participants: list[Participant], task_ids: list[str]) -> list[tuple[Participant, str, str]]:
    """(participant, task_id, condition) for every session in the study."""
    schedule = []
    for idx, p in enumerate(participants):
        conditions = assign_conditions(idx, len(task_ids))
        schedule.extend((p, task_id, cond) for task_id, cond in zip(task_ids, conditions))
    return schedule


# --- Session records ---


@dataclass
class SessionRecord:
    participant_id: str
    experience: str
    task_id: str
    condition: str  # one of CONDITIONS
    success: bool
    time_s: float
    edit_count: int
    sus_responses: list[int] | None = None  # collected once, after the assistant condition
    trust_responses: list[int] | None = None  # collected once per condition
    interview_notes: str = ""


def append_record(path: Path, record: SessionRecord) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def read_records(path: Path) -> list[SessionRecord]:
    if not path.exists():
        return []
    return [
        SessionRecord(**json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# --- Paired analysis (exact for small n, matching the exact small-sample tests already used in
# evaluation/summary.py; a tie-corrected normal approximation covers larger n) ---


def _signed_ranks(diffs: list[float]) -> list[float]:
    order = sorted(range(len(diffs)), key=lambda i: abs(diffs[i]))
    ranks = [0.0] * len(diffs)
    i = 0
    while i < len(order):
        j = i
        while j < len(order) and abs(diffs[order[j]]) == abs(diffs[order[i]]):
            j += 1
        avg_rank = (i + 1 + j) / 2  # average of the (1-indexed) ranks i+1..j
        for idx in order[i:j]:
            ranks[idx] = avg_rank
        i = j
    return ranks


def _std_normal_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def wilcoxon_signed_rank(x: list[float], y: list[float]) -> dict:
    """Two-sided Wilcoxon signed-rank test on paired samples `x`, `y` (tied pairs are dropped, per
    convention). `n <= 20` uses an exact permutation test over all 2**n sign assignments of the
    ranks; above that, a tie-corrected normal approximation with continuity correction."""
    diffs = [a - b for a, b in zip(x, y) if a != b]
    n = len(diffs)
    if n == 0:
        return {"n": 0, "w_plus": None, "w_minus": None, "p_value": None, "rank_biserial": None}

    ranks = _signed_ranks(diffs)
    total = sum(ranks)
    w_plus = sum(r for r, d in zip(ranks, diffs) if d > 0)
    rank_biserial = (2 * w_plus / total - 1) if total else 0.0

    if n <= 20:
        le = ge = 0
        for mask in range(2**n):
            s = sum(ranks[i] for i in range(n) if (mask >> i) & 1)
            le += s <= w_plus
            ge += s >= w_plus
        p_value = min(1.0, 2 * min(le, ge) / 2**n)
    else:
        mean = n * (n + 1) / 4
        tie_correction = sum(t**3 - t for t in Counter(ranks).values()) / 48
        variance = n * (n + 1) * (2 * n + 1) / 24 - tie_correction
        z = (abs(w_plus - mean) - 0.5) / math.sqrt(variance) if variance > 0 else 0.0
        p_value = min(1.0, 2 * (1 - _std_normal_cdf(z)))

    return {
        "n": n,
        "w_plus": round(w_plus, 2),
        "w_minus": round(total - w_plus, 2),
        "p_value": round(p_value, 4),
        "rank_biserial": round(rank_biserial, 3),
    }


def _paired_by_participant(records: list[SessionRecord], metric: str) -> tuple[list[float], list[float]]:
    """Per-participant mean of `metric` under each condition, paired by participant. Each
    participant does each task under only one condition (see `assign_conditions`), so the unit of
    pairing is the participant, not the (participant, task); participants missing either condition
    are left out."""
    by_participant: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_participant[r.participant_id][r.condition].append(float(getattr(r, metric)))
    xs, ys = [], []
    for values in by_participant.values():
        if values[CONDITIONS[0]] and values[CONDITIONS[1]]:
            xs.append(sum(values[CONDITIONS[0]]) / len(values[CONDITIONS[0]]))
            ys.append(sum(values[CONDITIONS[1]]) / len(values[CONDITIONS[1]]))
    return xs, ys


def compare_time(records: list[SessionRecord]) -> dict:
    return wilcoxon_signed_rank(*_paired_by_participant(records, "time_s"))


def compare_edit_count(records: list[SessionRecord]) -> dict:
    return wilcoxon_signed_rank(*_paired_by_participant(records, "edit_count"))


def compare_success(records: list[SessionRecord]) -> dict:
    """Wilcoxon signed-rank on each participant's success rate under each condition (binary
    per-task success has no within-task pair to run McNemar on in this design)."""
    return wilcoxon_signed_rank(*_paired_by_participant(records, "success"))


# --- Instrument + demographic summaries ---


def demographics_summary(participants: list[Participant]) -> dict:
    return dict(Counter(p.experience for p in participants))


def summarize_sus(records: list[SessionRecord]) -> dict:
    scores = [score_sus(r.sus_responses) for r in records if r.sus_responses]
    return {"n": len(scores), "mean": round(sum(scores) / len(scores), 1) if scores else None}


def summarize_trust(records: list[SessionRecord], condition: str | None = None) -> dict:
    filtered = [r for r in records if r.trust_responses and (condition is None or r.condition == condition)]
    scores = [score_trust(r.trust_responses) for r in filtered]
    return {"n": len(scores), "mean": round(sum(scores) / len(scores), 2) if scores else None}


def render_report(participants: list[Participant], records: list[SessionRecord]) -> str:
    lines = ["# User evaluation summary", ""]
    lines.append(f"- participants: {len(participants)} ({demographics_summary(participants)})")
    lines.append(f"- sessions recorded: {len(records)}")
    sus = summarize_sus(records)
    lines.append(f"- SUS (assistant condition): mean {sus['mean']} (n={sus['n']})")
    for cond in CONDITIONS:
        trust = summarize_trust(records, cond)
        lines.append(f"- trust-in-automation ({cond}): mean {trust['mean']} (n={trust['n']})")

    lines += ["", "## Paired comparisons (assistant vs manual)", ""]
    time_cmp = compare_time(records)
    edit_cmp = compare_edit_count(records)
    success_cmp = compare_success(records)
    lines.append(
        f"- time to completion: Wilcoxon W+={time_cmp['w_plus']}, p={time_cmp['p_value']}, "
        f"rank-biserial r={time_cmp['rank_biserial']} (n={time_cmp['n']})"
    )
    lines.append(
        f"- edit count: Wilcoxon W+={edit_cmp['w_plus']}, p={edit_cmp['p_value']}, "
        f"rank-biserial r={edit_cmp['rank_biserial']} (n={edit_cmp['n']})"
    )
    lines.append(
        f"- task success rate: Wilcoxon W+={success_cmp['w_plus']}, p={success_cmp['p_value']}, "
        f"rank-biserial r={success_cmp['rank_biserial']} (n={success_cmp['n']})"
    )
    return "\n".join(lines) + "\n"
