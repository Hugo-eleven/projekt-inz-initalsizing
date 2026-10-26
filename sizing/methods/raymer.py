"""Metoda Raymera, Aircraft Design: A Conceptual Approach, 2nd ed. (1992), rozdz. 3."""
from ..core.mission import FixedFraction, mission_weight_fraction
from ..core.units import N_to_lbf
from .base import MissionInput, SizingMethod

# Tabela 3.1: W_e/W_0 = A · W_0^C · K_vs, W_0 w lb
EMPTY_WEIGHT_TABLE_3_1 = {
    "sailplane_unpowered": (0.86, -0.05),
    "sailplane_powered": (0.91, -0.05),
    "homebuilt_metal_wood": (1.19, -0.09),
    "homebuilt_composite": (0.99, -0.09),
    "ga_single_engine": (2.36, -0.18),
    "ga_twin_engine": (1.51, -0.10),
    "agricultural": (0.74, -0.03),
    "twin_turboprop": (0.96, -0.05),
    "flying_boat": (1.09, -0.05),
    "jet_trainer": (1.59, -0.10),
    "jet_fighter": (2.34, -0.13),
    "military_cargo_bomber": (0.93, -0.07),
    "jet_transport": (1.02, -0.06),
}

# Tabela 3.2: historyczne frakcje faz
WARMUP_TAKEOFF = 0.970
CLIMB = 0.985
LANDING = 0.995

# Rów. 3.11: 6% zapasu na paliwo rezerwowe i niezużywalne
RESERVE_FACTOR = 1.06

# Rozdz. 3.4 (L/D Estimation): śmigło przelot przy L/D_max, krążenie 0.866 L/D_max; odrzut odwrotnie
LD_FACTORS = {"prop": {"cruise": 1.0, "loiter": 0.866}, "jet": {"cruise": 0.866, "loiter": 1.0}}


def standard_segments(cruise, loiter=None):
    """Prosta misja z rozdz. 3: rozruch i start, wznoszenie, przelot, (krążenie), lądowanie."""
    segs = [FixedFraction("warmup_takeoff", WARMUP_TAKEOFF), FixedFraction("climb", CLIMB), cruise]
    if loiter is not None:
        segs.append(loiter)
    segs.append(FixedFraction("landing", LANDING))
    return segs


class Raymer(SizingMethod):
    name = "Raymer"

    def __init__(self, category: str = "ga_single_engine", K_vs: float = 1.0):
        self.A, self.C = EMPTY_WEIGHT_TABLE_3_1[category]
        self.K_vs = K_vs

    def empty_weight_fraction(self, W0: float, inp: MissionInput) -> float:
        return self.A * N_to_lbf(W0) ** self.C * self.K_vs

    def fuel_fraction(self, W0: float, inp: MissionInput) -> float:
        return RESERVE_FACTOR * (1 - mission_weight_fraction(inp.segments))

    def required_inputs(self) -> list[str]:
        return ["W_crew", "W_payload", "category", "range", "V_cruise", "L/D", "SFC", "eta_p"]
