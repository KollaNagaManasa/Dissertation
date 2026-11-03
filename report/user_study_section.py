"""Section 5.x of the final report: the user evaluation (objective O6). Every number is computed from
results/user_study/sessions.jsonl at build time via ragiac.evaluation.user_study; the prose states
the study's validity problems alongside the results, because they limit what the numbers can show."""

from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from ragiac.evaluation.user_study import (
    CONDITIONS,
    EXPERIENCE_LEVELS,
    compare_success,
    compare_time,
    read_records,
    score_sus,
    score_trust,
)

SESSIONS = Path(__file__).resolve().parent.parent / "results" / "user_study" / "sessions.jsonl"
EXP_NAME = {"under_1y": "Under 1 year", "2y_plus": "2 years or more"}
COND_NAME = {"assistant": "Assistant", "manual": "Manual"}


def _p(x):
    return "n/a" if x is None else f"{x:.3f}"


def user_evaluation(R, heading="5.13"):
    records = read_records(SESSIONS)
    if not records:
        return
    participants = sorted({r.participant_id for r in records})
    by_exp = defaultdict(set)
    for r in records:
        by_exp[r.experience].add(r.participant_id)
    tasks = sorted({r.task_id for r in records})

    R.h2(f"{heading} User evaluation: usability, completion time and developer trust")
    R.p(
        f"The user evaluation (objective O6) was run with {len(participants)} engineers from the delivery team: "
        f"{len(by_exp['under_1y'])} with under one year of Terraform experience and {len(by_exp['2y_plus'])} with two "
        f"years or more. Each completed the same {len(tasks)} tasks from the benchmark set "
        f"({', '.join(f'`{t}`' for t in tasks)}), two with the assistant and two without it, in a counterbalanced "
        f"within-subjects design ({len(records)} sessions in total). Task success was scored with the same automated "
        "validity and intent checks used in the benchmark. Time to completion was recorded per task. After the "
        "assistant condition each participant completed the System Usability Scale (SUS) [13] and a 12-item "
        "trust-in-automation questionnaire [14], followed by five semi-structured interview questions."
    )
    R.p(
        "**How the manual condition was actually run.** The design called for the manual condition to use provider "
        "documentation and web search only. In practice, some participants used a general-purpose AI assistant "
        "during the manual condition. Use of other tools was not controlled or recorded per session, so it is not "
        "known which manual sessions were affected. The comparison below is therefore between *the project's "
        "assistant* and *participants' own unrestricted working practice, which for some included a general-purpose "
        "AI assistant*, not between the assistant and no assistant. This is the most important limitation of the "
        "user evaluation and is discussed further below."
    )

    # ---- objective measures ----------------------------------------------------------------------
    rows = []
    for exp in (*EXPERIENCE_LEVELS, None):
        group = [r for r in records if exp is None or r.experience == exp]
        for cond in CONDITIONS:
            cs = [r for r in group if r.condition == cond]
            if not cs:
                continue
            rows.append([
                EXP_NAME.get(exp, "All participants"),
                COND_NAME[cond],
                f"{sum(r.success for r in cs)} / {len(cs)}",
                f"{median(r.time_s for r in cs):.0f}",
                f"{mean(r.time_s for r in cs):.0f}",
            ])
    R.table(
        ["Group", "Condition", "Tasks succeeded", "Median time (s)", "Mean time (s)"],
        rows,
        [4.2, 2.6, 3.0, 3.1, 3.1],
        "User evaluation: task success and time to completion by condition and experience level.",
        align_right_from=2,
        font_size=9.5,
    )

    per_task = defaultdict(lambda: defaultdict(list))
    for r in records:
        per_task[r.task_id][r.condition].append(r)
    R.table(
        ["Task", "Assistant: succeeded", "Assistant: median s", "Manual: succeeded", "Manual: median s"],
        [
            [t]
            + [
                cell
                for cond in CONDITIONS
                for cell in (
                    f"{sum(r.success for r in per_task[t][cond])} / {len(per_task[t][cond])}",
                    f"{median(r.time_s for r in per_task[t][cond]):.0f}" if per_task[t][cond] else "n/a",
                )
            ]
            for t in tasks
        ],
        [2.6, 3.3, 3.3, 3.3, 3.3],
        "User evaluation results per task.",
        align_right_from=1,
        font_size=9.5,
    )

    time_cmp, success_cmp = compare_time(records), compare_success(records)
    R.table(
        ["Measure (assistant vs manual)", "Pairs", "W+", "p (exact, two-sided)", "Rank-biserial r"],
        [
            ["Mean time per participant", time_cmp["n"], time_cmp["w_plus"], _p(time_cmp["p_value"]), time_cmp["rank_biserial"]],
            ["Success rate per participant", success_cmp["n"], success_cmp["w_plus"], _p(success_cmp["p_value"]), success_cmp["rank_biserial"]],
        ],
        [5.6, 1.6, 1.6, 3.6, 3.6],
        "Paired Wilcoxon signed-rank tests, one pair per participant (tied pairs dropped). A negative r means lower values with the assistant.",
        align_right_from=1,
        font_size=9.5,
    )

    a_time = [r.time_s for r in records if r.condition == "assistant"]
    m_time = [r.time_s for r in records if r.condition == "manual"]
    faster = sum(1 for a, m in zip(*_per_participant(records, "time_s")) if a < m)
    R.p(
        f"**Completion time.** Tasks done with the assistant took a median of {median(a_time):.0f} s against "
        f"{median(m_time):.0f} s for the manual condition. {faster} of {time_cmp['n']} participants were faster on "
        f"average with the assistant (Wilcoxon p = {_p(time_cmp['p_value'])}, r = {time_cmp['rank_biserial']}). "
        "This is the clearest result of the user evaluation, but two qualifications apply. The absolute times are "
        "short for writing Terraform by hand, which is consistent with some manual sessions having used a "
        "general-purpose AI assistant, as described above. And with eight participants, the result shows a "
        "consistent direction, not a reliable estimate of the size of the saving."
    )

    a_succ = sum(r.success for r in records if r.condition == "assistant")
    m_succ = sum(r.success for r in records if r.condition == "manual")
    n_cond = len(a_time)
    always_fail = [t for t in tasks if not any(r.success for r in per_task[t]["assistant"] + per_task[t]["manual"])]
    R.p(
        f"**Task success.** {a_succ} of {n_cond} assistant sessions and {m_succ} of {n_cond} manual sessions passed "
        f"the automated checks (per-participant Wilcoxon p = {_p(success_cmp['p_value'])}, not significant). The "
        "per-task table shows why this comparison is weak. "
        + (
            f"Task {', '.join(f'`{t}`' for t in always_fail)} was never completed successfully in either condition, so it "
            "contributes no information about the assistant. "
            if always_fail
            else ""
        )
        + "With only two counterbalancing sequences, each participant used the assistant on a fixed pair of tasks, so a "
        "participant's success difference largely reflects which tasks they had the assistant for, not the "
        "assistant alone. The success comparison is therefore reported but not interpreted as an effect."
    )

    # ---- subjective measures -----------------------------------------------------------------------
    sus_rows, sus_all, trust_all = [], [], []
    by_exp_sus, by_exp_trust = defaultdict(list), defaultdict(list)
    for r in records:
        if r.sus_responses:
            s, t = score_sus(r.sus_responses), score_trust(r.trust_responses) if r.trust_responses else None
            sus_all.append(s)
            by_exp_sus[r.experience].append(s)
            if t is not None:
                trust_all.append(t)
                by_exp_trust[r.experience].append(t)
    for exp in EXPERIENCE_LEVELS:
        if by_exp_sus[exp]:
            sus_rows.append([
                EXP_NAME[exp],
                len(by_exp_sus[exp]),
                f"{mean(by_exp_sus[exp]):.1f} ({min(by_exp_sus[exp]):.1f}-{max(by_exp_sus[exp]):.1f})",
                f"{mean(by_exp_trust[exp]):.2f} ({min(by_exp_trust[exp]):.2f}-{max(by_exp_trust[exp]):.2f})" if by_exp_trust[exp] else "n/a",
            ])
    sus_rows.append([
        "All participants",
        len(sus_all),
        f"{mean(sus_all):.1f} ({min(sus_all):.1f}-{max(sus_all):.1f})",
        f"{mean(trust_all):.2f} ({min(trust_all):.2f}-{max(trust_all):.2f})" if trust_all else "n/a",
    ])
    R.table(
        ["Group", "n", "SUS, 0-100: mean (range)", "Trust, 1-7: mean (range)"],
        sus_rows,
        [4.4, 1.2, 5.2, 5.2],
        "Usability (SUS) and trust in the assistant, collected after the assistant condition.",
        align_right_from=1,
        font_size=9.5,
    )
    R.p(
        f"**Usability and trust.** The mean SUS score is {mean(sus_all):.1f}, below the commonly used benchmark "
        f"of 68 for an average system [16], with a wide spread ({min(sus_all):.1f} to {max(sus_all):.1f}). Mean "
        f"trust in the assistant is {mean(trust_all):.2f} on the 1-7 scale, above the neutral midpoint of 4, and "
        f"no participant scored it below {min(trust_all):.2f}. The two measures move together: the participants "
        "who rated usability highest also reported the most trust. With four participants per experience group, "
        "the difference between groups cannot be distinguished from individual variation. Trust was collected only "
        "after the assistant condition, so no comparison of trust between conditions is possible. The edit-count "
        "measure in the design (edits made to the assistant's output) was not recorded in any session and is not "
        "reported."
    )
    answered = sum(
        1
        for r in records
        if r.interview_notes
        and any(l.startswith("A:") and l[2:].strip() not in ("", "NA", "NO") for l in r.interview_notes.splitlines())
    )
    R.p(
        f"**Interviews.** The semi-structured interviews produced almost no usable data. Of the "
        f"{len(participants)} participants, {answered} gave any answer other than a blank or \"NA\", and those "
        "answers are single phrases (for example, that they would use the assistant \"as it is reliable\"). No "
        "thematic analysis is therefore possible, and the qualitative question of what makes developers trust or "
        "distrust generated infrastructure code remains open."
    )
    R.p(
        "**What the user evaluation does and does not show.** It shows that the assistant can be used by engineers "
        "at both experience levels without training, that they completed tasks faster with it than with their usual "
        "practice, and that they reported moderate usability and above-neutral trust. It does not show an "
        "improvement in task success. It cannot attribute the time saving to the assistant rather than to AI "
        "assistance in general, because the manual condition was not controlled for AI use. It also gives no insight "
        "into why participants trusted the output. A repeat with controlled tool use, recorded edits, trust measured "
        "in both conditions, a Latin-square task assignment and interviews conducted live rather than by form is "
        "listed under Future Scope."
    )


def _per_participant(records, metric):
    by = defaultdict(lambda: defaultdict(list))
    for r in records:
        by[r.participant_id][r.condition].append(float(getattr(r, metric)))
    xs, ys = [], []
    for v in by.values():
        if v["assistant"] and v["manual"]:
            xs.append(mean(v["assistant"]))
            ys.append(mean(v["manual"]))
    return xs, ys
