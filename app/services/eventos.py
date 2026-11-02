"""Patrón Observer (RF-12).

Sujeto: el historial de entrenamientos de una persona.
Observadores: quienes necesitan enterarse cuando ese historial cambia
(hoy, el trainer vinculado a la persona).
"""

from dataclasses import dataclass
from typing import Any, Protocol


class Observador(Protocol):
    def actualizar(self, evento: Any) -> None: ...


class Sujeto:
    def __init__(self) -> None:
        self._observadores: list[Observador] = []

    def suscribir(self, observador: Observador) -> None:
        if observador not in self._observadores:
            self._observadores.append(observador)

    def desuscribir(self, observador: Observador) -> None:
        if observador in self._observadores:
            self._observadores.remove(observador)

    def esta_suscripto(self, tipo: type) -> bool:
        return any(isinstance(observador, tipo) for observador in self._observadores)

    def notificar(self, evento: Any) -> None:
        for observador in list(self._observadores):
            observador.actualizar(evento)


@dataclass
class EntrenamientoFinalizado:
    db: Any
    entrenamiento: Any


class HistorialEntrenamientos(Sujeto):
    def finalizado(self, db: Any, entrenamiento: Any) -> None:
        self.notificar(EntrenamientoFinalizado(db=db, entrenamiento=entrenamiento))


# Instancia única que usa el servicio de entrenamientos
historial_entrenamientos = HistorialEntrenamientos()