"""Weryfikacja metody Roskama na przykładzie 2.6.1 (Part I, 1985, s. 49–53 i 70–71)."""
from math import exp, log10

import pytest

from sizing.core.mission import Cruise, FixedFraction, mission_weight_fraction
from sizing.core.solver import bisection, brent, fixed_point
from sizing.core.units import G0, LB_PER_HP_H, KT, N_to_lbf, lbf_to_N
from sizing.methods.base import MissionInput
from sizing.methods.roskam import Roskam

SM = 1609.344   # mila lądowa, m


def example_2_6_1():
    """Tab. 2.17: 6 × 175 lb (z pilotem) + 200 lb bagażu, 1000 mil lądowych, rezerwa 25% paliwa zużytego.
    W tekście na s. 51 zasięg opisano jako 1000 nm, ale (2.9) daje zasięg w milach lądowych
    i wynik 0,863 odpowiada 1000 sm (errata z 1997 r.)."""
    cr = Cruise(range_m=1000 * SM, V=250 * KT, LD=11, c_p=0.5 * LB_PER_HP_H, eta_p=0.82)
    segs = [FixedFraction("start_warmup", 0.992), FixedFraction("taxi", 0.996),
            FixedFraction("takeoff", 0.996), FixedFraction("climb", 0.990), cr,
            FixedFraction("descent", 0.992), FixedFraction("landing_taxi_shutdown", 0.992)]
    m = Roskam("twin_engine_prop", reserve_fraction_of_used=0.25)
    # „The crew is counted here as part of the payload” (s. 53)
    return m, MissionInput(W_crew=0.0, W_payload=lbf_to_N(6 * 175 + 200), segments=segs)


def test_cruise_eq_2_9():
    """(2.9): R = 375·(η_p/c_p)·(L/D)·ln(W4/W5), R w sm, c_p w lb/hp/h → W5/W4 = 0,863 (s. 52)."""
    m, inp = example_2_6_1()
    cr = inp.segments[4]
    assert cr.weight_fraction() == pytest.approx(exp(-1000 / (375 * 0.82 / 0.5 * 11)), rel=1e-4)
    assert cr.weight_fraction() == pytest.approx(0.863, abs=5e-4)


def test_mission_fuel_fraction():
    """s. 52: M_ff = 0,827, W_F = 0,173·1,25·W_TO = 0,216·W_TO."""
    m, inp = example_2_6_1()
    assert mission_weight_fraction(inp.segments) == pytest.approx(0.827, abs=5e-4)
    assert m.fuel_fraction(1.0, inp) == pytest.approx(0.216, abs=1e-3)


def test_step_4_to_7_at_guess():
    """s. 53: przy W_TO = 7000 lb W_E,tent ≈ 4203 lb (z zaokrągleniem W_F = 0,216·W_TO)."""
    m, inp = example_2_6_1()
    W0 = lbf_to_N(7000)
    WE_tent = 7000 * (1 - m.fuel_fraction(W0, inp) - m.M_tfo) - 1250
    assert WE_tent == pytest.approx(4203, abs=5)
    # residuum to W_E,tent − W_E (krok 7)
    assert N_to_lbf(m.residual(W0, inp)) == pytest.approx(WE_tent - m.empty_weight_lbf(W0), abs=1e-6)


def test_takeoff_weight_example_2_6_1():
    """Wynik: W_TO = 7900 lb, W_E = 4900 lb (s. 53, odczyt z wykresu). Rozwiązanie analityczne
    z s. 70–71 (C = 0,779, D = 1250 lb) daje w książce 7935 lb (dokładnie 7931 lb). Bez zaokrągleń
    M_ff i W_F/W_TO kod daje 7943 lb, W_E = 4936 lb, W_F = 1718 lb."""
    m, inp = example_2_6_1()
    r = brent(lambda W: m.residual(W, inp), lbf_to_N(3000), lbf_to_N(20000), rtol=1e-10)
    W_lb = N_to_lbf(r.W0)
    # niezależnie: log10 W_TO = A + B·log10(C·W_TO − D)
    C, D = 1 - m.fuel_fraction(r.W0, inp) - 0.005, 1250.0
    assert log10(W_lb) == pytest.approx(0.0966 + 1.0298 * log10(C * W_lb - D), abs=1e-9)
    assert W_lb == pytest.approx(7935, rel=2e-3)
    assert W_lb == pytest.approx(7900, rel=1e-2)
    assert m.empty_weight_lbf(r.W0) == pytest.approx(4900, rel=1e-2)


def test_eq_2_16_values():
    m = Roskam("single_engine_prop")
    W0 = lbf_to_N(2550)
    assert m.empty_weight_lbf(W0) == pytest.approx(10 ** ((log10(2550) + 0.1440) / 1.1162), rel=1e-12)
    assert m.empty_weight_fraction(W0, None) == pytest.approx(0.5948, abs=2e-4)  # ręcznie: 10^(3.5505/1.1162) = 1516.8 lb


def test_default_profile_uses_table_2_1():
    cr = Cruise(range_m=0.0, V=60.0, LD=10, c_p=1e-7, eta_p=0.8)
    ff = Roskam().fuel_fraction(1e4, MissionInput(0, 0, cruise=cr))
    assert ff == pytest.approx(1 - 0.995 * 0.997 * 0.998 * 0.992 * 0.993 * 0.993, abs=1e-12)


def test_solvers_agree_on_example():
    m, inp = example_2_6_1()
    f = lambda W: m.residual(W, inp)
    a, b = lbf_to_N(3000), lbf_to_N(20000)
    rs = [fixed_point(lambda W: m.g(W, inp), lbf_to_N(7000)), bisection(f, a, b), brent(f, a, b)]
    assert all(r.converged for r in rs)
    assert rs[0].W0 == pytest.approx(rs[2].W0, rel=1e-5)
    assert rs[1].W0 == pytest.approx(rs[2].W0, rel=1e-5)


# --- Recenzja 2 (R1, R2) --------------------------------------------------------------

from sizing.core.mission import Loiter
from sizing.core.units import NMI
from sizing.methods.gudmundsson import Gudmundsson
from sizing.methods.raymer import Raymer


def c172_input():
    cr = Cruise(range_m=500 * NMI, V=120 * KT, LD=10, c_p=0.45 * LB_PER_HP_H, eta_p=0.8)
    rs = Loiter(endurance_s=2700, V=90 * KT, LD=8.66, c_p=0.45 * LB_PER_HP_H, eta_p=0.8)
    return MissionInput(W_crew=77 * G0, W_payload=251 * G0, cruise=cr, reserve=rs)


def test_bracket_picks_lower_rising_root_when_two_roots():
    """homebuilt_composite (B < 1): F wklęsłe. Przy 150 kg ładunku są dwa pierwiastki,
    a szeroki przedział 300–5000 kg nie zmienia znaku, więc Brent na nim zawodzi."""
    import dataclasses
    m = Roskam("homebuilt_composite", phases="homebuilt", M_tfo=0.0)
    inp = dataclasses.replace(c172_input(), W_crew=0.0, W_payload=150 * G0)
    assert m.residual(300 * G0, inp) * m.residual(5000 * G0, inp) > 0
    a, b = m.bracket(inp)
    r = brent(lambda W: m.residual(W, inp), a, b)
    assert r.W0 / G0 == pytest.approx(372.8, abs=0.5)
    h = 1e-6 * r.W0
    assert m.residual(r.W0 + h, inp) - m.residual(r.W0 - h, inp) > 0


def test_bracket_raises_when_no_solution():
    with pytest.raises(ValueError, match="nie ma rozwiązania"):
        Roskam("homebuilt_scaled_fighter", phases="homebuilt").bracket(c172_input())


@pytest.mark.parametrize("m", [Raymer(reserve_factor=1.0), Gudmundsson(), Roskam(M_tfo=0.0)])
def test_bracket_matches_wide_interval_for_ga_single(m):
    inp = c172_input()
    r1 = brent(lambda W: m.residual(W, inp), *m.bracket(inp))
    r2 = brent(lambda W: m.residual(W, inp), 300 * G0, 5000 * G0)
    assert r1.W0 == pytest.approx(r2.W0, rel=1e-5)


def test_double_reserve_rejected():
    m = Roskam(reserve_fraction_of_used=0.25)
    with pytest.raises(ValueError, match="dwa razy"):
        m.fuel_fraction(1e4, c172_input())
