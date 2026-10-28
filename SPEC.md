# SPEC – narzędzie do wstępnego doboru masy i parametrów samolotu GA

Wersja robocza 0.2 (2026-10-27; 0.1 z 2026-10-26). Do uzgodnienia z Marcinem przed pisaniem kodu.

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
| Równanie wagowe | rów. (6-9); „Method 1” (§6.2.1, stałe We/W0 i Wf/W0) jako wariant kontrolny, Example 6-2 | rozdz. 3.2, rów. (3.1)–(3.4) | (2.1)–(2.5), krok 7: W_E,tent = W_E z regresji; W_tfo = 0,005·W_TO |
| Masa własna | §6.2.2, rów. (6-14): We/W0 = 0,8841 − 0,0333·ln W0 [lbf] | Tabela 3.1, W_e/W₀ = A·W₀^C·K_vs | (2.16): log₁₀W_E = (log₁₀W_TO − A)/B, tab. 2.15 (s. 47) |
| Paliwo | §20.5: tab. 20-6, przelot (20-12) z (20-9), rezerwa (20-22), bez współczynnika 1,06 | frakcje faz: Tabela 3.2 + Breguet (3.5)–(3.8) | (2.13)–(2.15), tab. 2.1 (s. 12), przelot (2.9), krążenie (2.11) |
| Dobór W/S, W/P | rozdz. 3.2, rów. (3-1)–(3-7) | rozdz. 5 | rozdz. 3 (Part I) |

Numery z Roskama sprawdzone na skanach (PDF = strona druku + 12). Każdy współczynnik w `regressions.yaml` ma pole `source` z numerem tabeli i strony, żeby dało się go zacytować w pracy.

Rezerwa paliwa jest wspólna dla metod (jawna faza `reserve` w `MissionInput`). U Raymera przy porównaniu ustawiamy wtedy `reserve_factor = 1.0`, żeby nie liczyć rezerwy podwójnie.

## 4. Solver

- iteracja prosta W₀(k+1) = g(W₀(k)), z opcjonalnym tłumieniem,
- bisekcja na przedziale [W_crew+W_payload, ~10× ta wartość],
- Brent (`scipy.optimize.brentq`) jako metoda referencyjna,
- Newton z pochodną numeryczną (opcjonalnie).

Kryterium stopu: |ΔW₀|/W₀ < 1e-6 lub limit iteracji. Zapisywana historia służy do wykresów zbieżności.

## 5. Weryfikacja i walidacja

- **Weryfikacja:** testy pytest odtwarzające przykłady liczbowe z książek (Gudmundsson Example 6-2 i 20-12, Raymer Box 3.1, Roskam przykład 2.6.1) z tolerancją ok. 1%.
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
