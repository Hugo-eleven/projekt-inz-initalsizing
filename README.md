# Narzędzie do wstępnego doboru masy samolotu GA

Porównanie metod initial sizingu (Gudmundsson, Raymer, Roskam) – praca inżynierska. Specyfikacja: [SPEC.md](SPEC.md).

## Uruchomienie

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
```

Wymagany Python 3.10 lub nowszy (składnia `float | None`).

```
python -m examples.c172
python -m examples.walidacja
```
