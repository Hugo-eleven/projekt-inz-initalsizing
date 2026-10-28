"""Przykład: misja zbliżona do Cessny 172S, porównanie metod na wspólnych danych.

Uruchomienie: python -m examples.c172
To przykład działania kodu, a nie punkt walidacji: przy 4 osobach prawdziwa C172S
zabiera przy MTOW ok. 60 kg paliwa, więc nie przeleci 500 NM. Punkty do walidacji
trzeba wziąć z POH.
U Roskama M_tfo = 0, bo paliwo niezużywalne pominięto też w pozostałych metodach.
Rezerwa jest wspólną stałą masą paliwa (rozdz. 3 pracy), dlatego u Raymera reserve_factor = 1.0
zamiast 1.06 z rów. 3.11.
"""
from sizing.core.mission import Cruise
from sizing.core.solver import bisection, brent, fixed_point
from sizing.core.units import G0, KT, LB_PER_HP_H, NMI
from sizing.methods.base import MissionInput
from sizing.methods.gudmundsson import Gudmundsson
from sizing.methods.raymer import LD_FACTORS, Raymer
from sizing.methods.roskam import Roskam

LD_max = 10.0                      # założenie
# Własne założenie, wspólne dla metod i dla obu faz (decyzja z rozdz. 2). Dla porównania Raymer,
# tab. 3.4, śmigło stałoskokowe: przelot c_bhp = 0,4 i eta_p = 0,8, krążenie 0,5 i 0,7.
c_p = 0.45 * LB_PER_HP_H
eta_p = 0.8

cruise = Cruise(range_m=500 * NMI, V=120 * KT, LD=LD_max * LD_FACTORS["prop"]["cruise"], c_p=c_p, eta_p=eta_p)
# Rezerwa wg rozdz. 3 pracy: stała masa W_res = t_res·c_P·0,45·P (45 min, C172S: 12,4 kg), w liczniku
inp = MissionInput(W_crew=77 * G0, W_payload=(3 * 77 + 20) * G0, cruise=cruise, W_reserve=12.4 * G0)

for m in (Raymer("ga_single_engine", reserve_factor=1.0), Gudmundsson("ga_single_engine"),
          Roskam("single_engine_prop", M_tfo=0.0)):
    print(f"--- {m.name}")
    f = lambda W: m.residual(W, inp)
    for r in (fixed_point(lambda W: m.g(W, inp), 1000 * G0), bisection(f, 300 * G0, 5000 * G0),
              brent(f, 300 * G0, 5000 * G0)):
        print(f"{r.method:12s} W0 = {r.W0 / G0:7.1f} kg  wywołania = {r.n_evals:3d}  zbieżny = {r.converged}")
    print(f"We/W0 = {m.empty_weight_fraction(r.W0, inp):.3f}, Wf/W0 = {m.fuel_fraction(r.W0, inp):.3f}")
