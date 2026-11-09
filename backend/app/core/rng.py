"""Controlled random number generator for deterministic gameplay."""

import random
from dataclasses import dataclass
from typing import Self


@dataclass
class SeededRNG:
    """Wrapper around random.Random with a fixed seed for reproducibility."""

    _rng: random.Random

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    @classmethod
    def from_seed(cls, seed: int) -> Self:
        """Create a new SeededRNG from a specific seed."""
        return cls(seed)

    def random(self) -> float:
        """Return random float in [0.0, 1.0)."""
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        """Return random integer in [a, b]."""
        return self._rng.randint(a, b)

    def randrange(self, start: int, stop: int | None = None, step: int = 1) -> int:
        """Return random integer from range(start, stop, step)."""
        return self._rng.randrange(start, stop, step)

    def choice(self, seq: list) -> any:
        """Return random element from sequence."""
        return self._rng.choice(seq)

    def choices(
        self, population: list, weights: list | None = None, k: int = 1
    ) -> list:
        """Return k random elements from population with optional weights."""
        return self._rng.choices(population, weights=weights, k=k)

    def shuffle(self, seq: list) -> None:
        """Shuffle sequence in place."""
        self._rng.shuffle(seq)

    def sample(self, population: list, k: int) -> list:
        """Return k unique elements from population."""
        return self._rng.sample(population, k)

    def uniform(self, a: float, b: float) -> float:
        """Return random float in [a, b]."""
        return self._rng.uniform(a, b)

    def gauss(self, mu: float, sigma: float) -> float:
        """Return random float from Gaussian distribution."""
        return self._rng.gauss(mu, sigma)

    def getstate(self) -> tuple:
        """Get internal state for serialization."""
        return self._rng.getstate()

    def setstate(self, state: tuple) -> None:
        """Set internal state from serialization."""
        self._rng.setstate(state)


def get_rng(session_seed: int) -> SeededRNG:
    """Get a SeededRNG instance for a game session."""
    return SeededRNG.from_seed(session_seed)
