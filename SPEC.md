# SPEC – narzędzie do wstępnego doboru masy i parametrów samolotu GA

Wersja robocza 0.1 (2026-10-26). Do uzgodnienia z Marcinem przed pisaniem kodu.

## 1. Cel

Narzędzie liczy dla zadanych wymagań misji: MTOW (W₀), masę własną, masę paliwa, powierzchnię skrzydła i moc silnika, trzema metodami (Gudmundsson, Raymer, Roskam), i porównuje wyniki z danymi rzeczywistych samolotów. Wyniki zasilają rozdziały 5 i 6 pracy, a opis narzędzia to rozdział 4.

Zakres: samoloty General Aviation, napęd tłokowo-śmigłowy, jednosilnikowe (wielosilnikowe jako ewentualne rozszerzenie).

## 2. Architektura

```
sizing/
  core/
    units.py          # konwersje; wewnętrznie wyłącznie SI
    atmosphere.py     # ISA (gęstość na wysokości przelotowej itd.)
    mission.py        # dane wejściowe: misja, ładunek, załoga, L/D, SFC, eta_p...
    solver.py         # iteracja prosta, bisekcja, Brent (scipy), Newton
    results.py        # wspólna struktura wyniku + historia iteracji
  methods/
    base.py           # klasa abstrakcyjna SizingMethod
    gudmundsson.py
    raymer.py
    roskam.py
  constraint/
    matching.py       # wykres dopasowania W/S – W/P (obwiednia osiągów)
  data/
    aircraft/*.yaml   # samoloty referencyjne (C172, SR22, DA40/P2008) + źródła
    regressions.yaml  # współczynniki regresji z książek, z numerem tabeli/strony
  ui/
    app.py            # Streamlit; tylko woła core, żadnej logiki obliczeń
tests/
  test_solver.py
  test_<metoda>_book_examples.py   # weryfikacja: przykłady z książek
  test_validation.py                # walidacja: błędy względem danych rzeczywistych
```

Zasada: rdzeń (`core`, `methods`, `constraint`) nie importuje niczego z `ui`. Wszystko da się uruchomić z poziomu pytest lub skryptu, co ułatwia generowanie tabel i wykresów do pracy.

### Wspólny interfejs metod

```python
class SizingMethod(ABC):
    name: str
    def empty_weight_fraction(self, W0, inp) -> float: ...
    def fuel_fraction(self, W0, inp) -> float: ...          # z frakcji faz misji
    def residual(self, W0, inp) -> float:                   # f(W0) = 0
        return W0 - (inp.W_crew + inp.W_payload) / (1 - self.fuel_fraction(W0, inp) - self.empty_weight_fraction(W0, inp))
    def required_inputs(self) -> list[str]: ...             # kryterium "liczba danych"
```

Solver dostaje `residual` i zwraca W₀, liczbę iteracji, historię zbieżności oraz status. Dzięki temu porównanie algorytmów (rozdz. 5.2) to po prostu podmiana solvera.

## 3. Metody (źródła w /mnt/project-files)

| | Gudmundsson (2014) | Raymer (1992, 2nd ed.) | Roskam (Part I, 1985) |
|---|---|---|---|
| Równanie wagowe | rozdz. 6.2.1 „Method 1”, rów. (6-6)–(6-9), przykład 6-2 | rozdz. 3.2, rów. (3.1)–(3.4) | rozdz. 2 (W_TO = W_E + W_F + W_PL + W_crew) |
| Masa własna | rozdz. 6.2.2 „Historical Empty Weight” | Tabela 3.1, W_e/W₀ = A·W₀^C·K_vs | regresja log₁₀W_E = (log₁₀W_TO − A)/B, współczynniki z tabeli w rozdz. 2 |
| Paliwo | analiza misji, rozdz. 6.1.4 | frakcje faz: Tabela 3.2 + Breguet (3.5)–(3.8) | frakcje faz misji (tabela fuel fractions), Breguet |
| Dobór W/S, W/P | rozdz. 3.2, rów. (3-1)–(3-7) | rozdz. 5 | rozdz. 3 (Part I) |

Numery z Roskama trzeba potwierdzić ręcznie na skanach (brak warstwy tekstowej). Każdy współczynnik w `regressions.yaml` ma pole `source` z numerem tabeli i strony, żeby dało się go zacytować w pracy.

## 4. Solver

- iteracja prosta W₀(k+1) = g(W₀(k)), z opcjonalnym tłumieniem,
- bisekcja na przedziale [W_crew+W_payload, ~10× ta wartość],
- Brent (`scipy.optimize.brentq`) jako metoda referencyjna,
- Newton z pochodną numeryczną (opcjonalnie).

Kryterium stopu: |ΔW₀|/W₀ < 1e-6 lub limit iteracji. Zapisywana historia służy do wykresów zbieżności.

## 5. Weryfikacja i walidacja

- **Weryfikacja:** testy pytest odtwarzające przykłady liczbowe z książek (Gudmundsson Example 6-2, Raymer przykład GA z rozdz. 21.2, przykład z Roskama Part I) z tolerancją ok. 1%.
- **Walidacja:** dane rzeczywiste z TCDS/POH dla C172, SR22 i trzeciego samolotu; liczony błąd względny MTOW, masy własnej, S i P.

## 6. Interfejs

Streamlit: formularz misji, wybór metod i solvera, tabela wyników obok siebie, wykres dopasowania, wykres zbieżności, eksport CSV. Analiza wrażliwości (tornado) jako osobny moduł `analysis/sensitivity.py` po zrobieniu rdzenia.

## 7. Kolejność prac

1. Szkielet, jednostki, ISA, solver + testy solvera.
2. Raymer (najlepiej udokumentowany, tekstowy PDF) + test na przykładzie z książki.
3. Gudmundsson, potem Roskam.
4. Wykres dopasowania.
5. Dane samolotów i walidacja.
6. Streamlit, wrażliwość.

## 8. Otwarte pytania

- Gdzie trzymamy kod (GitHub czy folder projektu)?
- Python 3.11+? Jakie środowisko ma Marcin lokalnie?
- Trzeci samolot: DA40 czy P2008?
- Czy W/S i W/P mają pochodzić z wykresu dopasowania (pełny sizing), czy na start przyjmujemy je jako dane wejściowe?
