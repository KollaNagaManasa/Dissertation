import pytest

from ragiac.retry import call_with_backoff


class Transient(Exception):
    pass


def test_retries_then_succeeds():
    calls = {"n": 0}
    sleeps: list[float] = []

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise Transient()
        return "ok"

    assert call_with_backoff(flaky, (Transient,), sleep=sleeps.append) == "ok"
    assert calls["n"] == 3
    assert len(sleeps) == 2


def test_gives_up_after_max_retries():
    sleeps: list[float] = []

    def always_fails():
        raise Transient()

    with pytest.raises(Transient):
        call_with_backoff(always_fails, (Transient,), max_retries=2, sleep=sleeps.append)
    assert len(sleeps) == 2


def test_non_retryable_errors_propagate_immediately():
    sleeps: list[float] = []

    def bad():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        call_with_backoff(bad, (Transient,), sleep=sleeps.append)
    assert sleeps == []


def test_vertex_retryable_errors_cover_rest_and_grpc_429s():
    from google.api_core import exceptions

    from ragiac.retry import vertex_retryable_errors

    retryable = vertex_retryable_errors()
    for err in (exceptions.TooManyRequests("429"), exceptions.ResourceExhausted("429")):
        assert isinstance(err, retryable)
    assert isinstance(exceptions.ServiceUnavailable("503"), retryable)
    assert not isinstance(exceptions.NotFound("404"), retryable)
