from types import SimpleNamespace

from app.services.calculos import volumen_series


def serie(peso, repeticiones, completada=True):
    return SimpleNamespace(peso_kg=peso, repeticiones=repeticiones, completada=completada)


def test_el_volumen_suma_peso_por_repeticiones_de_las_series_completadas():
    series = [serie(60, 10), serie(62.5, 8), serie(100, 10, completada=False)]

    assert volumen_series(series) == 1100


def test_las_series_sin_peso_no_suman_volumen():
    assert volumen_series([serie(None, 15)]) == 0