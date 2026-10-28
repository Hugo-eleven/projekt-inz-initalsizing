"""Pierwsza walidacja: trzy metody na misjach samolotów badawczych z rozdz. 3.

Uruchomienie: python -m examples.walidacja
Błąd względny = (wynik − wartość rzeczywista) / wartość rzeczywista.
"""
from sizing.core.solver import brent
from sizing.core.units import G0
from sizing.data.aircraft import AIRCRAFT
from sizing.methods.gudmundsson import Gudmundsson
from sizing.methods.raymer import Raymer
from sizing.methods.roskam import Roskam


def methods(ac):
    c = ac.category
    return [Raymer(c["raymer"], reserve_factor=1.0), Gudmundsson(c["gudmundsson"]),
            Roskam(c["roskam"], M_tfo=0.0)]


print(f"{'samolot':18s} {'metoda':12s} {'W0 [kg]':>8s} {'błąd':>7s} {'We [kg]':>8s} {'błąd':>7s} {'Wf [kg]':>8s}")
for key, ac in AIRCRAFT.items():
    inp = ac.mission()
    for m in methods(ac):
        r = brent(lambda W: m.residual(W, inp), *m.bracket(inp))
        W0 = r.W0 / G0
        We = m.empty_weight_fraction(r.W0, inp) * W0
        Wf = m.fuel_fraction(r.W0, inp) * W0 + ac.reserve_kg
        flag = " *" if ac.range_provisional else ""
        print(f"{ac.name + flag:18s} {m.name:12s} {W0:8.1f} {W0 / ac.mtow_kg - 1:+7.1%} "
              f"{We:8.1f} {We / ac.we_kg - 1:+7.1%} {Wf:8.1f}")
    print(f"{'':18s} {'rzeczywiste':12s} {ac.mtow_kg:8.1f} {'':7s} {ac.we_kg:8.1f} {'':7s} {ac.fuel_kg:8.1f}")
print("* zasięg tymczasowy (model z rozdz. 3)")
