"""Profil misji i frakcje masy faz lotu (wspólne dla metod)."""
from dataclasses import dataclass
from math import exp

from .units import G0


def _check_sfc(seg, needs_V: bool):
    if seg.c_t is None and (seg.c_p is None or seg.eta_p is None):
        raise ValueError(f"{seg.name}: podaj c_t (odrzut) albo c_p i eta_p (śmigło)")
    if needs_V and seg.V is None:
        raise ValueError(f"{seg.name}: dla śmigła potrzebna jest prędkość V")


@dataclass
class FixedFraction:
    """Faza o frakcji przyjętej statystycznie (rozruch i start, wznoszenie, lądowanie)."""
    name: str
    fraction: float

    def weight_fraction(self) -> float:
        return self.fraction


@dataclass
class Cruise:
    """Przelot, równanie Bregueta.

    Śmigło: c_p [kg/(W·s)], eta_p; frakcja = exp(-R·c_p·g / (eta_p·L/D)).
    Odrzut: c_t [1/s]; frakcja = exp(-R·c_t / (V·L/D)) (Raymer, rów. 3.6).
    """
    range_m: float
    V: float              # m/s
    LD: float
    c_p: float | None = None
    eta_p: float | None = None
    c_t: float | None = None
    name: str = "cruise"

    def __post_init__(self):
        _check_sfc(self, needs_V=False)

    def weight_fraction(self) -> float:
        if self.c_t is not None:
            return exp(-self.range_m * self.c_t / (self.V * self.LD))
        return exp(-self.range_m * self.c_p * G0 / (self.eta_p * self.LD))


@dataclass
class Loiter:
    """Krążenie, równanie długotrwałości (Raymer, rów. 3.8)."""
    endurance_s: float
    LD: float
    V: float | None = None    # potrzebna tylko dla śmigła
    c_p: float | None = None
    eta_p: float | None = None
    c_t: float | None = None
    name: str = "loiter"

    def __post_init__(self):
        _check_sfc(self, needs_V=self.c_t is None)

    def weight_fraction(self) -> float:
        c = self.c_t if self.c_t is not None else self.c_p * G0 * self.V / self.eta_p
        return exp(-self.endurance_s * c / self.LD)


def mission_weight_fraction(segments) -> float:
    """W_x / W_0 jako iloczyn frakcji wszystkich faz."""
    r = 1.0
    for s in segments:
        r *= s.weight_fraction()
    return r
