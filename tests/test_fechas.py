from datetime import date

import pytest

from app.services.fechas import calcular_edad


@pytest.mark.parametrize(
    "nacimiento, referencia, esperada",
    [
        (date(2000, 6, 15), date(2026, 6, 14), 25),  # cumple mañana
        (date(2000, 6, 15), date(2026, 6, 15), 26),  # cumple hoy
        (date(2000, 6, 15), date(2026, 12, 31), 26),  # ya cumplió este año
        (date(2000, 2, 29), date(2026, 2, 28), 25),  # nacido en año bisiesto
        (date(2000, 2, 29), date(2026, 3, 1), 26),
    ],
)
def test_calcular_edad(nacimiento, referencia, esperada):
    assert calcular_edad(nacimiento, referencia) == esperada