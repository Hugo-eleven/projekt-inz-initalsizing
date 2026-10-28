"""Weryfikacja metody Gudmundssona na przykładach z książki (wyd. 1, 2014)."""
from math import exp, log

import pytest

from sizing.core.mission import Cruise, FixedFraction, Loiter, mission_weight_fraction
from sizing.core.solver import brent
from sizing.core.units import G0, KT, LB_PER_HP_H, NMI, N_to_lbf, lbf_to_N
from sizing.methods.base import MissionInput
from sizing.methods.gudmundsson import Gudmundsson


def test_example_6_2_method_1():
    """Example 6-2, s. 140: W0 = 6069 lbf, We = 4172 lbf, Wf = 797 lbf."""
    m = Gudmundsson(We_W0=0.6875, Wf_W0=0.13125)
    inp = MissionInput(W_crew=lbf_to_N(200), W_payload=lbf_to_N(3 * 200 + 300))
    W0 = m.g(lbf_to_N(1000), inp)   # przy stałych stosunkach (6-9) jest jawne
    assert N_to_lbf(W0) == pytest.approx(6069, abs=1)
    assert N_to_lbf(m.empty_weight_fraction(W0, inp) * W0) == pytest.approx(4172, abs=1)
    assert N_to_lbf(m.fuel_fraction(W0, inp) * W0) == pytest.approx(797, abs=1)


def test_eq_6_14_kg_and_lbf_forms_agree():
    """(6-14) podaje dwie postacie: 0.8841 - 0.0333 ln W0[lbf] i 0.8578 - 0.0333 ln W0[kg]."""
    m = Gudmundsson()
    for kg in (600, 1157, 1633):
        W0 = kg * G0
        assert m.empty_weight_fraction(W0, None) == pytest.approx(0.8578 - 0.0333 * log(kg), abs=2e-4)


def test_example_20_12_mission_fractions():
    """Test wzoru Wf/W0 = 1 − Π(W_i/W_(i-1)) na liczbach z Example 20-12, s. 918
    (W5/W2 = 0.8608). Nie jest to niezależna weryfikacja wariantu podstawowego."""
    known = [FixedFraction("0-1", 0.9971), FixedFraction("1-2", 0.9933),
             FixedFraction("5-6", 0.998), FixedFraction("6-7", 0.999)]
    W5_W2 = (1 - 0.15) / mission_weight_fraction(known)
    assert W5_W2 == pytest.approx(0.8608, abs=1e-4)
    segs = known + [FixedFraction("2-5", W5_W2)]
    m = Gudmundsson()
    assert m.fuel_fraction(0, MissionInput(0, 0, segments=segs)) == pytest.approx(0.15, abs=1e-12)


def test_cruise_eq_20_12_with_20_9():
    """Przelot (20-12) z c_t = c_bhp·V / (1 980 000·η_p) w jednostkach brytyjskich ma dawać
    to samo co postać SI w mission.Cruise."""
    c_bhp, eta, V_fts, LD, R_ft = 0.45, 0.8, 120 * 1.68781, 10.0, 500 * 6076.12
    c_t = c_bhp * V_fts / (1_980_000 * eta)            # (20-9), 1/s
    ratio_uk = exp(-R_ft * c_t / (V_fts * LD))         # (20-12) rozwiązane względem W_fin/W_ini
    cr = Cruise(range_m=500 * NMI, V=120 * KT, LD=LD, c_p=c_bhp * LB_PER_HP_H, eta_p=eta)
    assert cr.weight_fraction() == pytest.approx(ratio_uk, rel=1e-4)


def test_default_profile_uses_table_20_6():
    cr = Cruise(range_m=0.0, V=60.0, LD=10, c_p=1e-7, eta_p=0.8)
    m = Gudmundsson()
    ff = m.fuel_fraction(1e4, MissionInput(0, 0, cruise=cr))
    assert ff == pytest.approx(1 - 0.995 * 0.988 * 0.997 * 0.995, abs=1e-12)


def test_regression_variant_converges():
    cr = Cruise(range_m=500 * NMI, V=120 * KT, LD=10, c_p=0.45 * LB_PER_HP_H, eta_p=0.8)
    inp = MissionInput(W_crew=77 * G0, W_payload=251 * G0, cruise=cr)
    m = Gudmundsson()
    r = brent(lambda W: m.residual(W, inp), 300 * G0, 5000 * G0)
    assert r.converged
    assert abs(m.residual(r.W0, inp)) < 1e-6 * r.W0


@pytest.mark.parametrize("W0_lbf, expected", [(1320, 0.6448), (2550, 0.6229), (3600, 0.6114)])
def test_eq_6_14_values(W0_lbf, expected):
    """We/W0 z (6-14) policzone ręcznie: 0.8841 − 0.0333·ln W0[lbf]."""
    assert Gudmundsson().empty_weight_fraction(lbf_to_N(W0_lbf), None) == pytest.approx(expected, abs=1e-4)


def test_full_case_independent_imperial_calculation():
    """Pełny wariant podstawowy policzony niezależnie od klasy, w jednostkach brytyjskich,
    wprost ze wzorów: tab. 20-6, (20-9), (20-12), (20-22), (6-14), (6-9)."""
    # dane: 500 NM przy 120 KTAS, rezerwa 45 min przy 90 KTAS, c_bhp = 0.45 lbf/h/BHP, eta_p = 0.8
    c_bhp, eta, LD_cr, LD_res = 0.45, 0.8, 10.0, 8.66
    V_cr, V_res = 120 * 1.687810, 90 * 1.687810          # ft/s
    R, E = 500 * 6076.115, 45 * 60.0                      # ft, s
    Wc, Wp = 77 * 2.2046226, 251 * 2.2046226              # lbf
    ct_cr = c_bhp * V_cr / (1_980_000 * eta)              # (20-9), 1/s
    ct_res = c_bhp * V_res / (1_980_000 * eta)
    f_cr = exp(-R * ct_cr / (V_cr * LD_cr))               # (20-12)
    f_res = exp(-E * ct_res / LD_res)                     # (20-22)
    Wf_W0 = 1 - 0.995 * 0.988 * f_cr * 0.997 * f_res * 0.995
    W0 = 2000.0
    for _ in range(200):                                  # (6-9) z (6-14)
        W0 = (Wc + Wp) / (1 - (0.8841 - 0.0333 * log(W0)) - Wf_W0)

    cr = Cruise(range_m=500 * NMI, V=120 * KT, LD=LD_cr, c_p=c_bhp * LB_PER_HP_H, eta_p=eta)
    rs = Loiter(endurance_s=E, V=90 * KT, LD=LD_res, c_p=c_bhp * LB_PER_HP_H, eta_p=eta)
    inp = MissionInput(W_crew=77 * G0, W_payload=251 * G0, cruise=cr, reserve=rs)
    m = Gudmundsson()
    r = brent(lambda W: m.residual(W, inp), 300 * G0, 5000 * G0, rtol=1e-10)
    assert m.fuel_fraction(r.W0, inp) == pytest.approx(Wf_W0, rel=1e-5)
    assert N_to_lbf(r.W0) == pytest.approx(W0, rel=1e-5)
