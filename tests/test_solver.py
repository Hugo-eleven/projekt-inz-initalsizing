import pytest

from sizing.core.solver import bisection, brent, fixed_point
from sizing.methods.base import MissionInput, SizingMethod


class Toy(SizingMethod):
    """We/W0 = A*W0^C (postać z Tabeli 3.1 Raymera), stała frakcja paliwa."""
    name = "toy"

    def empty_weight_fraction(self, W0, inp):
        return 2.36 * W0 ** -0.18

    def fuel_fraction(self, W0, inp):
        return 0.15

    def required_inputs(self):
        return []


@pytest.fixture
def case():
    return Toy(), MissionInput(W_crew=180.0, W_payload=400.0)


def test_solvers_agree(case):
    m, inp = case
    f = lambda W: m.residual(W, inp)
    r_fp = fixed_point(lambda W: m.g(W, inp), 2000.0)
    r_bi = bisection(f, 1000.0, 10000.0)
    r_br = brent(f, 1000.0, 10000.0)
    assert all(r.converged for r in (r_fp, r_bi, r_br))
    assert r_fp.W0 == pytest.approx(r_br.W0, rel=1e-5)
    assert r_bi.W0 == pytest.approx(r_br.W0, rel=1e-5)
    assert abs(f(r_br.W0)) < 1e-3
    assert r_br.n_evals < r_bi.n_evals


# --- Regresja: biegun g(W0) (recenzja kodu, runda 1, P1) -----------------------------

from sizing.core.mission import Cruise, Loiter
from sizing.core.units import G0, KT, LB_PER_HP_H, NMI
from sizing.methods.raymer import Raymer


@pytest.fixture
def c172():
    cr = Cruise(range_m=500 * NMI, V=120 * KT, LD=10, c_p=0.45 * LB_PER_HP_H, eta_p=0.8)
    rs = Loiter(endurance_s=2700, V=90 * KT, LD=8.66, c_p=0.45 * LB_PER_HP_H, eta_p=0.8)
    return Raymer(reserve_factor=1.0), MissionInput(W_crew=77 * G0, W_payload=251 * G0, cruise=cr, reserve=rs)


def test_fixed_point_from_wrong_side_of_pole_does_not_report_convergence(c172):
    m, inp = c172
    r = fixed_point(lambda W: m.g(W, inp), 100 * G0)
    assert not r.converged
    assert isinstance(r.W0, float)


def test_bisection_does_not_converge_to_pole(c172):
    m, inp = c172
    # Na 100–400 kg residuum bez bieguna nie zmienia znaku, więc bisekcja ma odmówić.
    with pytest.raises(ValueError):
        bisection(lambda W: m.residual(W, inp), 100 * G0, 400 * G0)
    r = bisection(lambda W: m.residual(W, inp), 100 * G0, 5000 * G0)
    assert r.converged and r.W0 / G0 == pytest.approx(1151.5, abs=0.5)


def test_g_rejects_nonpositive_weight_and_denominator(c172):
    m, inp = c172
    with pytest.raises(ValueError):
        m.g(-10.0, inp)
    with pytest.raises(ValueError):
        m.g(100 * G0, inp)


def test_n_evals_counts_all_function_calls(case):
    m, inp = case
    calls = []

    def f(W):
        calls.append(W)
        return m.residual(W, inp)

    assert bisection(f, 1000.0, 10000.0).n_evals == len(calls)
    calls.clear()
    assert brent(f, 1000.0, 10000.0).n_evals == len(calls)


def test_fixed_reserve_mass_goes_to_numerator(c172):
    """Rezerwa jako stała masa paliwa (rozdz. 3 pracy): W0 = (Wc + Wp + W_res) / (1 − Wf,m/W0 − We/W0)."""
    import dataclasses
    m, inp = c172
    inp = dataclasses.replace(inp, reserve=None, W_reserve=12.4 * G0)
    r = brent(lambda W: m.residual(W, inp), *m.bracket(inp))
    d = 1 - m.fuel_fraction(r.W0, inp) - m.empty_weight_fraction(r.W0, inp)
    assert r.W0 == pytest.approx((77 + 251 + 12.4) * G0 / d, rel=1e-6)


@pytest.mark.parametrize("key", ["C172S", "SR22", "DA40"])
def test_solve_all_algorithms_agree_on_aircraft(key):
    from sizing.core.solver import ALGORITHMS, solve
    from sizing.data.aircraft import AIRCRAFT
    from sizing.methods.gudmundsson import Gudmundsson
    from sizing.methods.roskam import Roskam
    inp = AIRCRAFT[key].mission()
    for m in (Raymer(reserve_factor=1.0), Gudmundsson(), Roskam(M_tfo=0.0)):
        rs = {alg: solve(m, inp, alg) for alg in ALGORITHMS}
        assert all(r.converged for r in rs.values())
        for r in rs.values():
            assert r.W0 == pytest.approx(rs["brent"].W0, rel=1e-5)
        assert rs["newton"].n_evals == 3 * rs["newton"].iterations
