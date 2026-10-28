"""Metoda Roskama, Airplane Design, Part I (1985), rozdz. 2.

W_TO = W_OE + W_F + W_PL (2.1), W_OE = W_E + W_tfo + W_crew (2.2).
Krok 7 procedury (s. 7): W_E,tent = W_TO − W_F − W_PL − W_tfo − W_crew (2.4)–(2.5)
ma się zgadzać z W_E dopuszczalnym z regresji (2.16):
    log10 W_TO = A + B · log10 W_E   →   W_E = 10^((log10 W_TO − A) / B),  masy w lb.
Residuum F(W0) z klasy bazowej to dokładnie W_E,tent − W_E.

Paliwo: metoda frakcji paliwa (s. 9–16): M_ff = iloczyn frakcji faz (2.13),
W_F = (1 − M_ff)·W_TO + W_F,res (2.14)–(2.15). Frakcje faz stałych z tab. 2.1 (s. 12),
przelot z (2.9), krążenie z (2.11) – w SI liczone tymi samymi klasami co u innych metod.
"""
from math import log10

from ..core.mission import FixedFraction, mission_weight_fraction
from ..core.units import N_to_lbf
from .base import MissionInput, SizingMethod

# Tab. 2.15 (s. 47): stałe A, B równania (2.16)
REGRESSION_TABLE_2_15 = {
    "homebuilt": (0.3411, 0.9519),
    "homebuilt_scaled_fighter": (0.5542, 0.8654),
    "homebuilt_composite": (0.8222, 0.8050),
    "single_engine_prop": (-0.1440, 1.1162),
    "twin_engine_prop": (0.0966, 1.0298),
    "twin_engine_prop_composite": (0.1130, 1.0403),
    "agricultural": (-0.4398, 1.1946),
}

# Tab. 2.1 (s. 12): frakcje faz W_i/W_(i-1)
FIXED_FRACTIONS_2_1 = {
    "homebuilt": dict(start_warmup=0.998, taxi=0.998, takeoff=0.998, climb=0.995, descent=0.995, landing_taxi_shutdown=0.995),
    "single_engine": dict(start_warmup=0.995, taxi=0.997, takeoff=0.998, climb=0.992, descent=0.993, landing_taxi_shutdown=0.993),
    "twin_engine": dict(start_warmup=0.992, taxi=0.996, takeoff=0.996, climb=0.990, descent=0.992, landing_taxi_shutdown=0.992),
    "agricultural": dict(start_warmup=0.996, taxi=0.995, takeoff=0.996, climb=0.998, descent=0.999, landing_taxi_shutdown=0.998),
}

# s. 7, krok 5: W_tfo „może sięgać 0,5% W_TO lub więcej”; w przykładzie 2.6.1 przyjęto 0,005·W_TO
M_TFO = 0.005


class Roskam(SizingMethod):
    name = "Roskam"

    def __init__(self, category: str = "single_engine_prop", phases: str = "single_engine",
                 M_tfo: float = M_TFO, reserve_fraction_of_used: float = 0.0):
        """reserve_fraction_of_used: rezerwa jako ułamek paliwa zużytego (typ 1 z s. 9),
        np. 0,25 w przykładzie 2.6.1. Przy wspólnej rezerwie liczonej jako faza misji
        (inp.reserve) zostaje 0. M_tfo = 0 wyłącza paliwo i olej niezużywalne."""
        self.A, self.B = REGRESSION_TABLE_2_15[category]
        self.fixed = FIXED_FRACTIONS_2_1[phases]
        self.M_tfo = M_tfo
        self.reserve_fraction_of_used = reserve_fraction_of_used

    def empty_weight_lbf(self, W0: float) -> float:
        """W_E dopuszczalne z (2.16), w lb."""
        return 10 ** ((log10(N_to_lbf(W0)) - self.A) / self.B)

    def empty_weight_fraction(self, W0: float, inp: MissionInput) -> float:
        return self.empty_weight_lbf(W0) / N_to_lbf(W0)

    def fixed_weight_fraction(self, W0: float, inp: MissionInput) -> float:
        return self.M_tfo

    def standard_segments(self, inp: MissionInput) -> list:
        """Profil z rys. 2.1: rozruch, kołowanie, start, wznoszenie, przelot, (krążenie), zniżanie, lądowanie."""
        f = self.fixed
        segs = [FixedFraction(k, f[k]) for k in ("start_warmup", "taxi", "takeoff", "climb")]
        segs.append(inp.cruise)
        if inp.reserve is not None:
            segs.append(inp.reserve)
        segs += [FixedFraction(k, f[k]) for k in ("descent", "landing_taxi_shutdown")]
        return segs

    def fuel_fraction(self, W0: float, inp: MissionInput) -> float:
        if self.reserve_fraction_of_used > 0 and inp.reserve is not None and inp.segments is None:
            raise ValueError("rezerwa podana dwa razy: reserve_fraction_of_used > 0 i faza inp.reserve")
        M_ff = mission_weight_fraction(self.segments(inp))      # (2.13)
        return (1 + self.reserve_fraction_of_used) * (1 - M_ff)  # (2.14)–(2.15)

    def required_inputs(self) -> list[str]:
        return ["W_crew", "W_payload", "category", "range", "V_cruise", "L/D", "SFC", "eta_p"]
