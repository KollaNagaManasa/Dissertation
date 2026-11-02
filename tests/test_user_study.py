import pytest

from ragiac.evaluation.user_study import (
    CONDITIONS,
    Participant,
    SessionRecord,
    assign_conditions,
    build_schedule,
    compare_success,
    demographics_summary,
    score_sus,
    score_trust,
    wilcoxon_signed_rank,
)


def test_score_sus_known_value():
    # odd items (positive) rated 4, even items (negative) rated 2: each contributes 3 -> 30*2.5
    assert score_sus([4, 2, 4, 2, 4, 2, 4, 2, 4, 2]) == pytest.approx(75.0)


def test_score_sus_bounds():
    assert score_sus([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == pytest.approx(100.0)
    assert score_sus([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == pytest.approx(0.0)


def test_score_sus_rejects_wrong_length_or_range():
    with pytest.raises(ValueError):
        score_sus([3] * 9)
    with pytest.raises(ValueError):
        score_sus([6] + [3] * 9)


def test_score_trust_reverse_codes_distrust_items():
    # fully trusting: reverse items (1-5) rated 1 ("not at all"), direct items (6-12) rated 7
    assert score_trust([1, 1, 1, 1, 1, 7, 7, 7, 7, 7, 7, 7]) == pytest.approx(7.0)
    # fully distrusting: the opposite
    assert score_trust([7, 7, 7, 7, 7, 1, 1, 1, 1, 1, 1, 1]) == pytest.approx(1.0)


def test_score_trust_rejects_wrong_length_or_range():
    with pytest.raises(ValueError):
        score_trust([3] * 11)
    with pytest.raises(ValueError):
        score_trust([8] + [3] * 11)


def test_assign_conditions_alternates_and_flips_by_participant():
    assert assign_conditions(0, 4) == ["assistant", "manual", "assistant", "manual"]
    assert assign_conditions(1, 4) == ["manual", "assistant", "manual", "assistant"]


def test_assign_conditions_balances_exposure_across_participants():
    for n_tasks in (2, 4):
        counts = {c: 0 for c in CONDITIONS}
        for participant_index in range(8):
            for cond in assign_conditions(participant_index, n_tasks):
                counts[cond] += 1
        assert counts["assistant"] == counts["manual"]


def test_build_schedule_pairs_each_participant_with_every_task():
    participants = [Participant("p1", "under_1y"), Participant("p2", "2y_plus")]
    schedule = build_schedule(participants, ["t1", "t2"])
    assert len(schedule) == 4
    assert {(p.id, task) for p, task, _ in schedule} == {("p1", "t1"), ("p1", "t2"), ("p2", "t1"), ("p2", "t2")}


def test_demographics_summary_counts_by_experience():
    participants = [Participant("p1", "under_1y"), Participant("p2", "under_1y"), Participant("p3", "2y_plus")]
    assert demographics_summary(participants) == {"under_1y": 2, "2y_plus": 1}


def test_wilcoxon_signed_rank_symmetric_case_is_not_significant():
    result = wilcoxon_signed_rank([5, 6], [6, 5])
    assert result["n"] == 2
    assert result["p_value"] == pytest.approx(1.0)
    assert result["rank_biserial"] == pytest.approx(0.0)


def test_wilcoxon_signed_rank_matches_known_exact_p_for_n4_all_same_direction():
    # every pair favours x by a distinct margin -> the smallest exact two-sided p at n=4 (0.125)
    result = wilcoxon_signed_rank([5, 5, 5, 5], [1, 2, 3, 4])
    assert result["n"] == 4
    assert result["p_value"] == pytest.approx(0.125)
    assert result["rank_biserial"] == pytest.approx(1.0)


def test_wilcoxon_signed_rank_drops_tied_pairs():
    result = wilcoxon_signed_rank([1, 2, 3], [1, 5, 1])
    assert result["n"] == 2  # the (1, 1) pair is dropped


def test_compare_success_mcnemar_known_value():
    # 1 pair where assistant succeeds and manual fails, 4 the other way round -> p = 2*(C(5,0)+C(5,1))/32
    records = [SessionRecord("p1", "under_1y", "t1", "assistant", True, 1.0, 0)] + [
        SessionRecord("p1", "under_1y", "t1", "manual", False, 1.0, 0)
    ]
    records += [
        r
        for i in range(4)
        for r in (
            SessionRecord(f"p{i+2}", "under_1y", "t1", "assistant", False, 1.0, 0),
            SessionRecord(f"p{i+2}", "under_1y", "t1", "manual", True, 1.0, 0),
        )
    ]
    result = compare_success(records)
    assert result == {"n": 5, "assistant_only": 1, "manual_only": 4, "p_value": pytest.approx(0.375)}
