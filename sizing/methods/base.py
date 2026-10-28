"""Wspólny interfejs metod wstępnego doboru masy."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MissionInput:
    """Wspólne dane wejściowe misji.

    Fazy o frakcjach statystycznych (rozruch, start, wznoszenie, lądowanie) dobiera
    każda metoda ze swoich tabel, a fazy liczone (przelot, rezerwa) są wspólne.
    Jawna lista `segments` zastępuje profil metody (np. przy odtwarzaniu przykładów z książek).
    """
    W_crew: float                 # N
    W_payload: float              # N
    cruise: object = None         # mission.Cruise
    reserve: object = None        # mission.Loiter lub Cruise, opcjonalnie
    segments: list | None = None
    W_reserve: float = 0.0        # N, stała masa paliwa rezerwowego (rozdz. 3 pracy, wz. 3.7)

    def __post_init__(self):
        if self.W_crew < 0 or self.W_payload < 0 or self.W_reserve < 0:
            raise ValueError("masa załogi, ładunku i rezerwy nie może być ujemna")

    @property
    def W_fixed(self) -> float:
        """Licznik równania wagowego: Wc + Wp + W_res."""
        return self.W_crew + self.W_payload + self.W_reserve


class SizingMethod(ABC):
    name: str

    @abstractmethod
    def empty_weight_fraction(self, W0: float, inp: MissionInput) -> float: ...

    @abstractmethod
    def fuel_fraction(self, W0: float, inp: MissionInput) -> float: ...

    @abstractmethod
    def required_inputs(self) -> list[str]:
        """Dane wejściowe wymagane przez metodę (kryterium porównania z rozdz. 3)."""

    def fixed_weight_fraction(self, W0: float, inp: MissionInput) -> float:
        """Inne składniki proporcjonalne do W0 poza masą własną i paliwem misji
        (np. paliwo i olej niezużywalne W_tfo u Roskama). Domyślnie 0."""
        return 0.0

    def standard_segments(self, inp: MissionInput) -> list:
        raise NotImplementedError(f"{self.name}: brak domyślnego profilu misji, podaj inp.segments")

    def segments(self, inp: MissionInput) -> list:
        if inp.segments is not None:
            return inp.segments
        if inp.cruise is None:
            raise ValueError(f"{self.name}: brak fazy przelotu (inp.cruise) i jawnej listy faz")
        return self.standard_segments(inp)

    def _denominator(self, W0: float, inp: MissionInput) -> float:
        if W0 <= 0:
            raise ValueError(f"W0 = {W0:.6g} N ≤ 0")
        return (1 - self.fuel_fraction(W0, inp) - self.empty_weight_fraction(W0, inp)
                - self.fixed_weight_fraction(W0, inp))

    def g(self, W0: float, inp: MissionInput) -> float:
        """Prawa strona równania wagowego (Raymer, rów. 3.4; Gudmundsson, rów. 6-9)."""
        d = self._denominator(W0, inp)
        if d <= 0:
            raise ValueError(f"mianownik równania wagowego ≤ 0 przy W0 = {W0:.6g} N (We/W0 + Wf/W0 ≥ 1)")
        return inp.W_fixed / d

    def residual(self, W0: float, inp: MissionInput) -> float:
        """Residuum bez bieguna: F(W0) = W0·(1 − Wf/W0 − We/W0 − W_inne/W0) − (Wc + Wp + W_res).

        Ma ten sam pierwiastek co W0 − g(W0), ale jest ciągłe dla W0 > 0, więc
        zmiana znaku na przedziale oznacza pierwiastek, a nie biegun g.
        """
        return W0 * self._denominator(W0, inp) - inp.W_fixed

    def bracket(self, inp: MissionInput, W_max_factor: float = 50.0, n: int = 400) -> tuple[float, float]:
        """Przedział [a, b] z pierwiastkiem F, na którym F rośnie (F' > 0).

        Skanuje logarytmicznie od Wc + Wp do W_max_factor·(Wc + Wp). Dla regresji, w których
        We/W0 rośnie z W0 (Roskam B < 1, Gudmundsson b > 0), F bywa wklęsłe i ma dwa pierwiastki
        albo żadnego. Wybierany jest najmniejszy pierwiastek z F' > 0, przy którym iteracja prosta
        jest stabilna. Brak takiego pierwiastka kończy się czytelnym ValueError.
        """
        W_fixed = inp.W_fixed
        if W_fixed <= 0:
            raise ValueError("Wc + Wp musi być dodatnie, żeby wyznaczyć przedział")
        lo, hi = W_fixed * 1.0001, W_fixed * W_max_factor
        pts = [lo * (hi / lo) ** (i / n) for i in range(n + 1)]
        vals = [self.residual(W, inp) for W in pts]
        for a, b, fa, fb in zip(pts, pts[1:], vals, vals[1:]):
            if fa < 0 <= fb:
                return a, b
        raise ValueError(
            f"{self.name}: równanie wagowe nie ma rozwiązania z F' > 0 dla W0 w "
            f"[{lo:.4g}, {hi:.4g}] N (masa własna i paliwo zawsze przekraczają W0 − Wc − Wp)")

