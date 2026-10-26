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
    assert r_br.iterations < r_bi.iterations
