"""Dane samolotów mają się zgadzać z tab. 3.2 rozdz. 3 (skrypt rozdzial3/obliczenia_rozdzial3.py)."""
import pytest

from sizing.core.solver import brent
from sizing.data.aircraft import AIRCRAFT
from sizing.methods.gudmundsson import Gudmundsson


@pytest.mark.parametrize("key, fuel, payload, reserve, LD", [
    ("C172S", 144.2, 173.4, 12.4, 8.98),
    ("SR22", 250.4, 275.0, 21.4, 10.87),
    ("DA40", 136.1, 194.9, 12.4, 10.30),
])
def test_values_match_chapter_3(key, fuel, payload, reserve, LD):
    a = AIRCRAFT[key]
    assert a.fuel_kg == pytest.approx(fuel, abs=0.05)
    assert a.payload_kg == pytest.approx(payload, abs=0.05)
    assert a.reserve_kg == pytest.approx(reserve, abs=0.05)
    assert a.LD_cruise == pytest.approx(LD, abs=0.005)


@pytest.mark.parametrize("key", list(AIRCRAFT))
def test_missions_solve(key):
    a, m = AIRCRAFT[key], Gudmundsson()
    inp = a.mission()
    r = brent(lambda W: m.residual(W, inp), *m.bracket(inp))
    assert r.converged
