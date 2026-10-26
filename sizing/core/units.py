"""Stałe i przeliczniki jednostek. Wewnętrznie wszystko w SI."""

G0 = 9.80665                 # m/s^2
LBF = 4.4482216152605        # N
LB = 0.45359237              # kg
FT = 0.3048                  # m
NMI = 1852.0                 # m
KT = NMI / 3600.0            # m/s
HP = 745.69987158227         # W
HOUR = 3600.0                # s

# 1 lb/(hp·h) -> kg/(W·s)
LB_PER_HP_H = LB / (HP * HOUR)


def N_to_lbf(W: float) -> float:
    return W / LBF


def lbf_to_N(W: float) -> float:
    return W * LBF
