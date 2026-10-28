"""Metoda Gudmundssona, General Aviation Aircraft Design, 1st ed. (2014).

Wariant podstawowy (decyzja z rozdz. 2 pracy):
  - równanie wagowe (6-9), s. 138,
  - masa własna z regresji dla jednosilnikowych GA, rów. (6-14), s. 141,
  - paliwo z analizy profilu misji wg §20.5: frakcje faz stałych z tab. 20-6 (s. 916),
    przelot z rów. (20-12) z c_t wg (20-9), rezerwa (krążenie) z rów. (20-22).
Wariant kontrolny: „Method 1” (§6.2.1), stałe historyczne We/W0 i Wf/W0 w (6-9).
"""
from math import log

from ..core.mission import FixedFraction, mission_weight_fraction
from ..core.units import N_to_lbf
from .base import MissionInput, SizingMethod

# Rów. (6-10)–(6-17): We/W0 = a + b·ln(W0), W0 w lbf
EMPTY_WEIGHT_LN = {
    "sailplane": (0.2950, 0.0386),             # (6-10)
    "powered_sailplane": (0.3068, 0.0510),     # (6-11)
    "lsa_land": (1.5451, -0.1402),             # (6-12)
    "lsa_amphib": (1.6351, -0.1402),           # (6-13)
    "ga_single_engine": (0.8841, -0.0333),     # (6-14)
    "ga_twin_piston": (0.4074, 0.0253),        # (6-15)
    "ga_twin_turboprop": (0.5319, 0.0066),     # (6-16)
    "agricultural": (1.4029, -0.0995),         # (6-17)
}

# Tab. 20-6: frakcje W_i/W_(i-1) dla samolotów GA
FIXED_FRACTIONS_20_6 = {
    "single_piston": {"warmup_takeoff": 0.995, "climb": 0.988, "descent": 0.997, "landing": 0.995},
    "twin_piston": {"warmup_takeoff": 0.994, "climb": 0.985, "descent": 0.996, "landing": 0.995},
}


class Gudmundsson(SizingMethod):
    name = "Gudmundsson"

    def __init__(self, category: str = "ga_single_engine", engine: str = "single_piston",
                 We_W0: float | None = None, Wf_W0: float | None = None):
        """We_W0 i Wf_W0 podane razem włączają wariant kontrolny „Method 1”."""
        if (We_W0 is None) != (Wf_W0 is None):
            raise ValueError("Method 1 wymaga obu stosunków: We_W0 i Wf_W0")
        self.a, self.b = EMPTY_WEIGHT_LN[category]
        self.fixed = FIXED_FRACTIONS_20_6[engine]
        self.We_W0, self.Wf_W0 = We_W0, Wf_W0
        if We_W0 is not None:
            self.name = "Gudmundsson (Method 1)"

    def empty_weight_fraction(self, W0: float, inp: MissionInput) -> float:
        if self.We_W0 is not None:
            return self.We_W0
        return self.a + self.b * log(N_to_lbf(W0))

    def standard_segments(self, inp: MissionInput) -> list:
        """Profil jak na rys. 20-14: rozruch i start, wznoszenie, przelot, zniżanie, (rezerwa), lądowanie."""
        f = self.fixed
        segs = [FixedFraction("warmup_takeoff", f["warmup_takeoff"]), FixedFraction("climb", f["climb"]),
                inp.cruise, FixedFraction("descent", f["descent"])]
        if inp.reserve is not None:
            segs.append(inp.reserve)
        segs.append(FixedFraction("landing", f["landing"]))
        return segs

    def fuel_fraction(self, W0: float, inp: MissionInput) -> float:
        if self.Wf_W0 is not None:
            return self.Wf_W0
        # §20.5.2: całe paliwo misji zużyte na końcu profilu, W_x = W0 - W_fm
        return 1 - mission_weight_fraction(self.segments(inp))

    def required_inputs(self) -> list[str]:
        if self.We_W0 is not None:
            return ["W_crew", "W_payload", "We/W0", "Wf/W0"]
        return ["W_crew", "W_payload", "category", "range", "V_cruise", "L/D", "SFC", "eta_p"]
