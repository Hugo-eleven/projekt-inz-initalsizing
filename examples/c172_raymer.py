"""Przykład: misja zbliżona do Cessny 172S, metoda Raymera (rozdz. 3)."""
from sizing.core.mission import Cruise, Loiter
from sizing.core.solver import bisection, brent, fixed_point
from sizing.core.units import G0, KT, LB_PER_HP_H, NMI
from sizing.methods.base import MissionInput
from sizing.methods.raymer import LD_FACTORS, Raymer, standard_segments

LD_max = 10.0                      # założenie
c_p = 0.45 * LB_PER_HP_H           # Tabela 3.4: tłok, śmigło stałoskokowe, przelot ~0.4–0.5
eta_p = 0.8

cruise = Cruise(range_m=500 * NMI, V=120 * KT, LD=LD_max * LD_FACTORS["prop"]["cruise"], c_p=c_p, eta_p=eta_p)
reserve = Loiter(endurance_s=45 * 60, V=90 * KT, LD=LD_max * LD_FACTORS["prop"]["loiter"], c_p=c_p, eta_p=eta_p)
inp = MissionInput(W_crew=77 * G0, W_payload=(3 * 77 + 20) * G0, segments=standard_segments(cruise, reserve))

m = Raymer("ga_single_engine")
f = lambda W: m.residual(W, inp)
for r in (fixed_point(lambda W: m.g(W, inp), 1000 * G0), bisection(f, 300 * G0, 5000 * G0), brent(f, 300 * G0, 5000 * G0)):
    print(f"{r.method:12s} W0 = {r.W0 / G0:7.1f} kg  iteracje = {r.iterations:3d}  zbieżny = {r.converged}")
print(f"We/W0 = {m.empty_weight_fraction(r.W0, inp):.3f}, Wf/W0 = {m.fuel_fraction(r.W0, inp):.3f}")
