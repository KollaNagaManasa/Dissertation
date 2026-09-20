"""Exponential-backoff retry for transient Vertex AI errors (429 quota, 503).

A fresh GCP project starts with low Vertex AI quota, so benchmark runs that issue many
generation calls back to back hit `429 Resource exhausted` — transient, and resolved by waiting.
"""

import logging
import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")
log = logging.getLogger(__name__)


def call_with_backoff(
    fn: Callable[[], T],
    retryable: tuple[type[BaseException], ...],
    max_retries: int = 6,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    attempt = 0
    while True:
        try:
            return fn()
        except retryable as e:
            if attempt >= max_retries:
                raise
            delay = min(max_delay, base_delay * (2**attempt)) * (0.5 + random.random() / 2)
            log.warning("retry %d/%d after %s; sleeping %.1fs", attempt + 1, max_retries, type(e).__name__, delay)
            sleep(delay)
            attempt += 1


def vertex_retryable_errors() -> tuple[type[BaseException], ...]:
    from google.api_core import exceptions

    # The REST transport raises TooManyRequests for HTTP 429; ResourceExhausted (gRPC) is only a
    # *subclass* of it, so catching ResourceExhausted alone misses the 429s we actually see.
    return (exceptions.TooManyRequests, exceptions.ServiceUnavailable, exceptions.DeadlineExceeded)
