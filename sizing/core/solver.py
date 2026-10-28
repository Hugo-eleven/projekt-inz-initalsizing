"""Rozwiązywanie niejawnego równania wagowego.

Iteracja prosta działa na W0 = g(W0), bisekcja i Brent na residuum F(W0) = 0.
Do porównania algorytmów (rozdz. 5.2) służy `n_evals`, czyli liczba wywołań funkcji,
bo „iteracja” znaczy w każdym algorytmie co innego.
"""
from dataclasses import dataclass, field
from typing import Callable

from scipy.optimize import brentq


@dataclass
class SolverResult:
    W0: float
    iterations: int
    converged: bool
    method: str
    history: list[float] = field(default_factory=list)
    n_evals: int = 0
    message: str = ""


def fixed_point(g: Callable[[float], float], W0_guess: float, rtol=1e-6, max_iter=200, relax=1.0) -> SolverResult:
    """Iteracja prosta W0(k+1) = (1-relax)*W0(k) + relax*g(W0(k)).

    Gdy g zgłosi ValueError (W0 ≤ 0 albo mianownik równania wagowego ≤ 0),
    zwraca wynik z converged=False zamiast liczyć dalej.
    """
    W, hist = W0_guess, [W0_guess]
    for k in range(1, max_iter + 1):
        try:
            W_new = (1 - relax) * W + relax * g(W)
        except ValueError as e:
            return SolverResult(W, k, False, "fixed_point", hist, k, str(e))
        hist.append(W_new)
        if abs(W_new - W) / abs(W_new) < rtol:
            return SolverResult(W_new, k, True, "fixed_point", hist, k)
        W = W_new
    return SolverResult(W, max_iter, False, "fixed_point", hist, max_iter, "przekroczono max_iter")


def bisection(f: Callable[[float], float], a: float, b: float, rtol=1e-6, max_iter=200) -> SolverResult:
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError("f(a) i f(b) muszą mieć różne znaki")
    hist, n = [], 2
    for k in range(1, max_iter + 1):
        m = 0.5 * (a + b)
        fm = f(m)
        n += 1
        hist.append(m)
        if (b - a) / 2 / abs(m) < rtol or fm == 0:
            return SolverResult(m, k, True, "bisection", hist, n)
        if fa * fm < 0:
            b = m
        else:
            a, fa = m, fm
    return SolverResult(m, max_iter, False, "bisection", hist, n, "przekroczono max_iter")


def brent(f: Callable[[float], float], a: float, b: float, rtol=1e-6) -> SolverResult:
    hist = []

    def tracked(x):
        hist.append(x)
        return f(x)

    W, info = brentq(tracked, a, b, rtol=rtol, full_output=True)
    return SolverResult(W, info.iterations, info.converged, "brent", hist, info.function_calls)


def newton(f: Callable[[float], float], x0: float, rtol=1e-6, max_iter=100, h_rel=1e-6) -> SolverResult:
    """Metoda Newtona z pochodną centralną h = h_rel·W (3 wywołania f na iterację)."""
    W, hist, n = x0, [x0], 0
    for k in range(1, max_iter + 1):
        h = h_rel * W
        try:
            fW, fp, fm = f(W), f(W + h), f(W - h)
        except ValueError as e:
            return SolverResult(W, k, False, "newton", hist, n, str(e))
        n += 3
        d = (fp - fm) / (2 * h)
        if d == 0:
            return SolverResult(W, k, False, "newton", hist, n, "zerowa pochodna")
        W_new = W - fW / d
        hist.append(W_new)
        if abs(W_new - W) / abs(W_new) < rtol:
            return SolverResult(W_new, k, True, "newton", hist, n)
        W = W_new
    return SolverResult(W, max_iter, False, "newton", hist, n, "przekroczono max_iter")


ALGORITHMS = ("fixed_point", "bisection", "brent", "newton")


def solve(method, inp, algorithm: str = "brent", rtol=1e-6) -> SolverResult:
    """Wspólne ustawienia dla porównania algorytmów (kryterium P4, rozdz. 3 i 4 pracy).

    Przedział [a, b] = [W_fixed, 10·W_fixed], W_fixed = Wc + Wp + W_res; gdy F(a)·F(b) > 0,
    przedział wyznacza method.bracket(). Iteracja prosta i Newton startują z W0 = b.
    """
    F = lambda W: method.residual(W, inp)
    a, b = inp.W_fixed, 10 * inp.W_fixed
    if F(a) * F(b) > 0:
        a, b = method.bracket(inp)
    if algorithm == "fixed_point":
        return fixed_point(lambda W: method.g(W, inp), b, rtol=rtol)
    if algorithm == "bisection":
        return bisection(F, a, b, rtol=rtol)
    if algorithm == "brent":
        return brent(F, a, b, rtol=rtol)
    if algorithm == "newton":
        return newton(F, b, rtol=rtol)
    raise ValueError(f"nieznany algorytm {algorithm!r}, dostępne: {ALGORITHMS}")
