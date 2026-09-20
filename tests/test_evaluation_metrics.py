import pytest

from ragiac.evaluation.metrics import (
    group_counts,
    mean_pass_at_k,
    pass_at_k,
    retrieval_hit,
    wilson_interval,
)


def test_pass_at_1_equals_fraction_correct():
    assert pass_at_k(5, 1, 1) == pytest.approx(0.2)
    assert pass_at_k(10, 7, 1) == pytest.approx(0.7)


def test_pass_at_k_edge_cases():
    assert pass_at_k(5, 0, 3) == 0.0
    assert pass_at_k(5, 5, 3) == 1.0
    assert pass_at_k(5, 3, 3) == 1.0  # n - c = 2 < k
    assert pass_at_k(5, 1, 5) == 1.0


def test_pass_at_k_known_value():
    # 1 - C(3,2)/C(5,2) = 1 - 3/10
    assert pass_at_k(5, 2, 2) == pytest.approx(0.7)


def test_pass_at_k_rejects_k_above_n():
    with pytest.raises(ValueError):
        pass_at_k(2, 1, 3)


def test_mean_pass_at_k_skips_tasks_with_too_few_samples():
    assert mean_pass_at_k([(5, 5), (1, 0)], k=3) == 1.0
    assert mean_pass_at_k([(1, 1)], k=3) is None


def test_wilson_interval_bounds():
    lo, hi = wilson_interval(0, 10)
    assert lo == 0.0 and 0 < hi < 0.4
    lo, hi = wilson_interval(10, 10)
    assert hi == 1.0 and lo > 0.6
    assert wilson_interval(0, 0) == (0.0, 0.0)


def test_retrieval_hit_matches_on_resource_types_mentioned_in_chunks():
    mentioned = ["google_storage_bucket", "google_storage_bucket_iam_member", "google_project_service"]
    assert retrieval_hit(["google_storage_bucket"], mentioned) == 1.0
    assert retrieval_hit(["google_storage_bucket", "google_sql_user"], mentioned) == 0.5
    assert retrieval_hit([], mentioned) is None


def test_retrieval_hit_accepts_alternatives_and_is_not_a_prefix_match():
    # google_storage_bucket must not be satisfied merely by *_iam_member chunks
    assert retrieval_hit(["google_storage_bucket"], ["google_storage_bucket_iam_member"]) == 0.0
    alternatives = [["google_storage_bucket_iam_member", "google_storage_bucket_iam_binding"]]
    assert retrieval_hit(alternatives, ["google_storage_bucket_iam_binding"]) == 1.0
    assert retrieval_hit(alternatives, ["google_storage_bucket"]) == 0.0


def test_group_counts():
    records = [
        {"task_id": "a", "ok": True},
        {"task_id": "a", "ok": False},
        {"task_id": "b", "ok": True},
    ]
    assert group_counts(records, lambda r: r["ok"]) == {"a": (2, 1), "b": (1, 1)}
