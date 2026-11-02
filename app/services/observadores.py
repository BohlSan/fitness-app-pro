from sqlalchemy import select

from app.models.trainer import ActividadCliente, EstadoVinculo, VinculoTrainer
from app.services.calculos import volumen_series
from app.services.eventos import EntrenamientoFinalizado, historial_entrenamientos


class ObservadorActividadTrainer:
    """Cuando una persona termina un entrenamiento, avisa a su trainer (si tiene uno activo).

    Corre dentro de la misma transacción que la finalización (RNF-14): la novedad
    se guarda junto con el entrenamiento o no se guarda ninguno de los dos.
    """

    def actualizar(self, evento: EntrenamientoFinalizado) -> None:
        db = evento.db
        entrenamiento = evento.entrenamiento

        trainers = list(
            db.scalars(
                select(VinculoTrainer.trainer_id).where(
                    VinculoTrainer.cliente_id == entrenamiento.usuario_id,
                    VinculoTrainer.estado == EstadoVinculo.ACTIVA,
                )
            )
        )
        volumen = round(
            volumen_series([serie for e in entrenamiento.ejercicios for serie in e.series]), 2
        )
        for trainer_id in trainers:
            db.add(
                ActividadCliente(
                    trainer_id=trainer_id,
                    cliente_id=entrenamiento.usuario_id,
                    tipo="ENTRENAMIENTO_FINALIZADO",
                    entrenamiento_id=entrenamiento.id,
                    titulo=entrenamiento.titulo,
                    fecha=entrenamiento.fecha,
                    duracion_segundos=entrenamiento.duracion_segundos,
                    volumen_kg=volumen,
                )
            )


def registrar_observadores() -> None:
    """Se llama una vez al iniciar la aplicación (es seguro repetirla)."""
    if not historial_entrenamientos.esta_suscripto(ObservadorActividadTrainer):
        historial_entrenamientos.suscribir(ObservadorActividadTrainer())