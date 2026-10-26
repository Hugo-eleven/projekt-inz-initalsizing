"""Weryfikacja: przykład ASW z Raymera (2nd ed., Box 3.1, s. 27–28)."""
import pytest

from sizing.core.mission import Cruise, FixedFraction, Loiter, mission_weight_fraction
from sizing.core.solver import brent, fixed_point
from sizing.core.units import FT, NMI, lbf_to_N, N_to_lbf
from sizing.methods.base import MissionInput
from sizing.methods.raymer import CLIMB, LANDING, WARMUP_TAKEOFF, Raymer


@pytest.fixture
def asw():
    # W książce V = 569.9 ft/s, choć 0.6 · 994.8 = 596.9 ft/s (błąd przepisania w Box 3.1).
    # Żeby odtworzyć wynik książki, bierzemy wartość z książki.
    cruise = Cruise(range_m=1500 * NMI, V=569.9 * FT, LD=16 * 0.866, c_t=0.5 / 3600)
    loiter = Loiter(endurance_s=3 * 3600, LD=16, c_t=0.4 / 3600)
    segs = [
        FixedFraction("warmup_takeoff", WARMUP_TAKEOFF),
        FixedFraction("climb", CLIMB),
        cruise, loiter, cruise,
        Loiter(endurance_s=1200, LD=16, c_t=0.4 / 3600),
        FixedFraction("landing", LANDING),
    ]
    # Box 3.1: załoga + ładunek = 10 800 lb, regresja jak dla "military cargo/bomber"
    return Raymer("military_cargo_bomber"), MissionInput(W_crew=lbf_to_N(800), W_payload=lbf_to_N(10000), segments=segs)


def test_asw_mission_fraction(asw):
    _, inp = asw
    assert mission_weight_fraction(inp.segments) == pytest.approx(0.635, abs=0.001)


def test_asw_takeoff_weight(asw):
    m, inp = asw
    r = brent(lambda W: m.residual(W, inp), lbf_to_N(20_000), lbf_to_N(200_000))
    assert N_to_lbf(r.W0) == pytest.approx(59_310, rel=2e-3)
    assert m.empty_weight_fraction(r.W0, inp) == pytest.approx(0.4309, abs=5e-4)


def test_fixed_point_matches_brent(asw):
    m, inp = asw
    r_fp = fixed_point(lambda W: m.g(W, inp), lbf_to_N(50_000))
    r_br = brent(lambda W: m.residual(W, inp), lbf_to_N(20_000), lbf_to_N(200_000))
    assert r_fp.converged
    assert r_fp.W0 == pytest.approx(r_br.W0, rel=1e-5)
