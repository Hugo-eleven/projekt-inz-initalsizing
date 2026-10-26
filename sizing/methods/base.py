"""Wspólny interfejs metod wstępnego doboru masy."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MissionInput:
    W_crew: float          # N
    W_payload: float       # N
    segments: list = field(default_factory=list)


class SizingMethod(ABC):
    name: str

    @abstractmethod
    def empty_weight_fraction(self, W0: float, inp: MissionInput) -> float: ...

    @abstractmethod
    def fuel_fraction(self, W0: float, inp: MissionInput) -> float: ...

    def g(self, W0: float, inp: MissionInput) -> float:
        """Prawa strona równania wagowego (Raymer, rów. 3.4)."""
        return (inp.W_crew + inp.W_payload) / (
            1 - self.fuel_fraction(W0, inp) - self.empty_weight_fraction(W0, inp))

    def residual(self, W0: float, inp: MissionInput) -> float:
        return W0 - self.g(W0, inp)
