def volumen_serie(peso_kg: float | None, repeticiones: int) -> float:
    return float(peso_kg or 0) * repeticiones


def volumen_series(series) -> float:
    """Volumen = Σ (peso × repeticiones) de las series completadas (RF-23).

    Funciona con cualquier objeto que tenga peso_kg, repeticiones y completada.
    Las series sin peso (peso corporal) aportan 0.
    """
    return sum(volumen_serie(s.peso_kg, s.repeticiones) for s in series if s.completada)