"""Rozwiązywanie niejawnego równania wagowego f(W0) = 0."""
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


def fixed_point(g: Callable[[float], float], W0_guess: float, rtol=1e-6, max_iter=200, relax=1.0) -> SolverResult:
    """Iteracja prosta W0(k+1) = (1-relax)*W0(k) + relax*g(W0(k))."""
    W, hist = W0_guess, [W0_guess]
    for k in range(1, max_iter + 1):
        W_new = (1 - relax) * W + relax * g(W)
        hist.append(W_new)
        if abs(W_new - W) / abs(W_new) < rtol:
            return SolverResult(W_new, k, True, "fixed_point", hist)
        W = W_new
    return SolverResult(W, max_iter, False, "fixed_point", hist)


def bisection(f: Callable[[float], float], a: float, b: float, rtol=1e-6, max_iter=200) -> SolverResult:
    fa = f(a)
    if fa * f(b) > 0:
        raise ValueError("f(a) i f(b) muszą mieć różne znaki")
    hist = []
    for k in range(1, max_iter + 1):
        m = 0.5 * (a + b)
        fm = f(m)
        hist.append(m)
        if (b - a) / 2 / abs(m) < rtol or fm == 0:
            return SolverResult(m, k, True, "bisection", hist)
        if fa * fm < 0:
            b = m
        else:
            a, fa = m, fm
    return SolverResult(m, max_iter, False, "bisection", hist)


def brent(f: Callable[[float], float], a: float, b: float, rtol=1e-6) -> SolverResult:
    hist = []

    def tracked(x):
        hist.append(x)
        return f(x)

    W, info = brentq(tracked, a, b, rtol=rtol, full_output=True)
    return SolverResult(W, info.iterations, info.converged, "brent", hist)
