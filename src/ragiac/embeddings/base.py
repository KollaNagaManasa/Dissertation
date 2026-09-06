from typing import Protocol


class Embedder(Protocol):
    """Turns text into a fixed-size dense vector."""

    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...
