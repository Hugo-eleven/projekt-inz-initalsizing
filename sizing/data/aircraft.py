"""Samoloty badawcze i ich misje projektowe (rozdz. 3 pracy, tab. 3.1–3.2).

Wartości wyjściowe i konwencje pochodzą z rozdz. 3 (skrypt rozdzial3/obliczenia_rozdzial3.py):
misja przy MTOW z 1 pilotem 77 kg (CS 23.25), ładunek = MTOW − masa własna − paliwo użytkowe − pilot,
wspólne c_P = 0,45 lb/(hp·h) i η_p = 0,80, L/D w przelocie = W0·g·V / (η_p·P_c),
rezerwa jako stała masa W_res = t_res·c_P·0,45·P (45 min).
Zasięgi SR22 i DA40 są tymczasowe (model z rozdz. 3, brak wartości z POH dla 75% mocy).
"""
from dataclasses import dataclass

from ..core.mission import Cruise
from ..core.units import FT, G0, HP, KT, LB, LB_PER_HP_H, NMI
from ..methods.base import MissionInput

GAL = 3.785411784e-3          # m^3
RHO_FUEL = 6 * LB / (GAL * 1000) * 1000   # kg/m^3, avgas 6 lb/US gal jak w POH
M_PILOT = 77.0                # kg, CS 23.25
C_P = 0.45 * LB_PER_HP_H      # kg/(W·s)
ETA_P = 0.80
T_RES = 0.75 * 3600           # s
P_RES = 0.45                  # ułamek mocy znamionowej podczas rezerwy


@dataclass(frozen=True)
class Aircraft:
    name: str
    mtow_kg: float
    we_kg: float              # masa własna (z paliwem niezużywalnym i olejem)
    fuel_gal: float           # paliwo użytkowe
    S_m2: float
    b_m: float
    P_W: float                # moc znamionowa
    power_cruise: float       # ułamek mocy w przelocie
    h_cruise_m: float
    V_cruise: float           # m/s, TAS
    range_nm: float           # zasięg misji projektowej
    range_provisional: bool
    category: dict            # klasa regresji dla każdej metody
    source: str

    @property
    def fuel_kg(self) -> float:
        return self.fuel_gal * GAL * RHO_FUEL

    @property
    def payload_kg(self) -> float:
        return self.mtow_kg - self.we_kg - self.fuel_kg - M_PILOT

    @property
    def reserve_kg(self) -> float:
        return T_RES * C_P * P_RES * self.P_W

    @property
    def LD_cruise(self) -> float:
        return self.mtow_kg * G0 * self.V_cruise / (ETA_P * self.power_cruise * self.P_W)

    def mission(self) -> MissionInput:
        cr = Cruise(range_m=self.range_nm * NMI, V=self.V_cruise, LD=self.LD_cruise, c_p=C_P, eta_p=ETA_P)
        return MissionInput(W_crew=M_PILOT * G0, W_payload=self.payload_kg * G0, cruise=cr,
                            W_reserve=self.reserve_kg * G0)


_SINGLE = {"raymer": "ga_single_engine", "gudmundsson": "ga_single_engine", "roskam": "single_engine_prop"}

AIRCRAFT = {
    "C172S": Aircraft("Cessna 172S", 2550 * LB, 1680 * LB, 53, 174 * FT ** 2, 11.00, 180 * HP, 0.75,
                      8500 * FT, 124 * KT, 518, False, _SINGLE,
                      "POH 172S rev. 5 (2004), karta Textron 2024; zasięg 518 NM przy 75% mocy, 8500 ft"),
    "SR22": Aircraft("Cirrus SR22", 3600 * LB, 2272 * LB, 92, 144.9 * FT ** 2, 38.3 * FT, 310 * HP, 0.75,
                     8000 * FT, 183 * KT, 767, True, _SINGLE,
                     "dane producenta (rozdz. 3, tab. 3.1); zasięg z modelu rozdz. 3"),
    "DA40": Aircraft("Diamond DA40 XLT", 1200.0, 792.0, 50, 13.54, 11.63, 180 * HP, 0.75,
                     6000 * FT, 137 * KT, 534, True, _SINGLE,
                     "Diamond tech specs DA40 XLT, S z karty DA40 NG (2010); zasięg z modelu rozdz. 3"),
}
