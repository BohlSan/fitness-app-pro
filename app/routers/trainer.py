from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.trainer import EstadoVinculo
from app.models.usuario import RolUsuario, Usuario
from app.schemas.entrenamiento import EntrenamientoOut
from app.schemas.estadisticas import (
    EjercicioEntrenadoOut,
    EvolucionEjercicioOut,
    EvolucionPesoOut,
    ResumenOut,
)
from app.schemas.habitos import RachaOut
from app.schemas.trainer import (
    ActividadOut,
    AsignacionIn,
    AsignacionOut,
    ClienteDetalleOut,
    ClienteResumenOut,
    CodigoOut,
    CuotaIn,
    PagoIn,
    PagoOut,
    PanelOut,
)
from app.services import (
    asignacion_service,
    entrenamiento_service,
    estadisticas_service,
    historial_service,
    peso_service,
    racha_service,
    rutina_service,
    trainer_service,
    vinculo_service,
)

router = APIRouter(prefix="/trainer", tags=["Personal Trainer"])

solo_trainer = require_role(RolUsuario.PERSONAL_TRAINER)

_PERIODO_INVALIDO = 'La fecha "desde" no puede ser posterior a "hasta"'


def cliente_autorizado(
    cliente_id: int,
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
) -> int:
    """Puerta única hacia los datos de un cliente (RF-13 y RF-30).

    Si la persona no es cliente ACTIVO de este trainer, responde 404 como si no existiera.
    """
    try:
        vinculo_service.exigir_cliente_activo(db, trainer.id, cliente_id)
    except vinculo_service.ClienteNoAutorizado:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente_id


# ---------- Panel, código y novedades ----------
@router.get("/panel", response_model=PanelOut)
def panel(trainer: Usuario = Depends(solo_trainer), db: Session = Depends(get_db)):
    return trainer_service.panel(db, trainer)


@router.get("/codigo", response_model=CodigoOut)
def codigo(trainer: Usuario = Depends(solo_trainer), db: Session = Depends(get_db)):
    return {"codigo_enlace": vinculo_service.obtener_codigo(db, trainer)}


@router.post("/codigo/regenerar", response_model=CodigoOut)
def regenerar_codigo(trainer: Usuario = Depends(solo_trainer), db: Session = Depends(get_db)):
    return {"codigo_enlace": vinculo_service.regenerar_codigo(db, trainer)}


@router.get("/actividad", response_model=list[ActividadOut])
def actividad(
    solo_no_leidas: bool = False,
    limite: int = Query(default=30, ge=1, le=100),
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    return trainer_service.actividad(db, trainer.id, solo_no_leidas, limite)


@router.post("/actividad/leidas", status_code=status.HTTP_204_NO_CONTENT)
def marcar_leidas(trainer: Usuario = Depends(solo_trainer), db: Session = Depends(get_db)):
    trainer_service.marcar_actividad_leida(db, trainer.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Clientes y solicitudes ----------
@router.get("/clientes", response_model=list[ClienteResumenOut])
def clientes(
    estado: EstadoVinculo | None = None,
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    return trainer_service.listar_clientes(db, trainer.id, estado)


@router.post("/vinculos/{vinculo_id}/aceptar", response_model=ClienteResumenOut)
def aceptar(
    vinculo_id: int,
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    try:
        vinculo_service.aceptar(db, trainer, vinculo_id)
    except vinculo_service.VinculoNoEncontrado:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except vinculo_service.EstadoInvalido:
        raise HTTPException(status_code=409, detail="Esa solicitud ya no está pendiente")
    return trainer_service.resumen_vinculo(db, trainer.id, vinculo_id)


@router.post("/vinculos/{vinculo_id}/finalizar", response_model=ClienteResumenOut)
def finalizar(
    vinculo_id: int,
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    try:
        vinculo_service.finalizar_como_trainer(db, trainer, vinculo_id)
    except vinculo_service.VinculoNoEncontrado:
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    except vinculo_service.EstadoInvalido:
        raise HTTPException(status_code=409, detail="Esa relación ya está finalizada")
    return trainer_service.resumen_vinculo(db, trainer.id, vinculo_id)


# ---------- Información de un cliente ----------
@router.get("/clientes/{cliente_id}", response_model=ClienteDetalleOut)
def detalle_cliente(
    cliente_id: int = Depends(cliente_autorizado),
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    return trainer_service.detalle_cliente(db, trainer.id, cliente_id)


@router.put("/clientes/{cliente_id}/cuota", response_model=ClienteDetalleOut)
def cambiar_cuota(
    datos: CuotaIn,
    cliente_id: int = Depends(cliente_autorizado),
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    vinculo_service.cambiar_cuota(db, trainer, cliente_id, datos.estado_cuota)
    return trainer_service.detalle_cliente(db, trainer.id, cliente_id)


@router.get("/clientes/{cliente_id}/pagos", response_model=list[PagoOut])
def pagos(
    cliente_id: int = Depends(cliente_autorizado),
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    vinculo = vinculo_service.exigir_cliente_activo(db, trainer.id, cliente_id)
    return vinculo_service.listar_pagos(db, vinculo.id)


@router.post("/clientes/{cliente_id}/pagos", response_model=PagoOut, status_code=status.HTTP_201_CREATED)
def registrar_pago(
    datos: PagoIn,
    cliente_id: int = Depends(cliente_autorizado),
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    try:
        return vinculo_service.registrar_pago(db, trainer, cliente_id, datos)
    except vinculo_service.DatosPagoInvalidos as error:
        raise HTTPException(status_code=422, detail=str(error))


# ---------- Rutinas asignadas (RF-11) ----------
@router.get("/clientes/{cliente_id}/asignaciones", response_model=list[AsignacionOut])
def asignaciones(
    cliente_id: int = Depends(cliente_autorizado),
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    return asignacion_service.listar_asignaciones(db, trainer.id, cliente_id)


@router.post(
    "/clientes/{cliente_id}/asignaciones",
    response_model=AsignacionOut,
    status_code=status.HTTP_201_CREATED,
)
def asignar_rutina(
    datos: AsignacionIn,
    cliente_id: int = Depends(cliente_autorizado),
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    try:
        return asignacion_service.asignar_rutina(db, trainer, cliente_id, datos.rutina_id)
    except rutina_service.RutinaNoEncontrada:
        raise HTTPException(status_code=404, detail="Rutina no encontrada")
    except asignacion_service.RutinaNoAsignable:
        raise HTTPException(status_code=422, detail="Solo podés asignar rutinas propias")


@router.post(
    "/clientes/{cliente_id}/asignaciones/{asignacion_id}/finalizar",
    response_model=AsignacionOut,
)
def finalizar_asignacion(
    asignacion_id: int,
    cliente_id: int = Depends(cliente_autorizado),
    trainer: Usuario = Depends(solo_trainer),
    db: Session = Depends(get_db),
):
    try:
        return asignacion_service.finalizar_asignacion(db, trainer, cliente_id, asignacion_id)
    except asignacion_service.AsignacionNoEncontrada:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")


# ---------- Historial de entrenamientos del cliente (RF-12) ----------
@router.get("/clientes/{cliente_id}/entrenamientos", response_model=list[EntrenamientoOut])
def historial_del_cliente(
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cliente_id: int = Depends(cliente_autorizado),
    db: Session = Depends(get_db),
):
    try:
        entrenamientos = historial_service.listar_historial(
            db, cliente_id, desde, hasta, limite, offset
        )
    except historial_service.PeriodoInvalido:
        raise HTTPException(status_code=422, detail=_PERIODO_INVALIDO)
    return [EntrenamientoOut.model_validate(e) for e in entrenamientos]


@router.get(
    "/clientes/{cliente_id}/entrenamientos/{entrenamiento_id}",
    response_model=EntrenamientoOut,
)
def entrenamiento_del_cliente(
    entrenamiento_id: int,
    cliente_id: int = Depends(cliente_autorizado),
    db: Session = Depends(get_db),
):
    try:
        entrenamiento = entrenamiento_service.obtener_finalizado_de(db, cliente_id, entrenamiento_id)
    except entrenamiento_service.EntrenamientoNoEncontrado:
        raise HTTPException(status_code=404, detail="Entrenamiento no encontrado")
    return EntrenamientoOut.model_validate(entrenamiento)


# ---------- Progreso del cliente (RF-29): los mismos servicios de las etapas 6 y 7 ----------
@router.get("/clientes/{cliente_id}/estadisticas/resumen", response_model=ResumenOut)
def resumen_del_cliente(
    desde: date | None = None,
    hasta: date | None = None,
    cliente_id: int = Depends(cliente_autorizado),
    db: Session = Depends(get_db),
):
    try:
        return estadisticas_service.resumen(db, cliente_id, desde, hasta)
    except estadisticas_service.PeriodoInvalido:
        raise HTTPException(status_code=422, detail=_PERIODO_INVALIDO)


@router.get(
    "/clientes/{cliente_id}/estadisticas/ejercicios",
    response_model=list[EjercicioEntrenadoOut],
)
def ejercicios_del_cliente(
    cliente_id: int = Depends(cliente_autorizado), db: Session = Depends(get_db)
):
    return estadisticas_service.ejercicios_entrenados(db, cliente_id)


@router.get(
    "/clientes/{cliente_id}/estadisticas/ejercicios/{ejercicio_id}",
    response_model=EvolucionEjercicioOut,
)
def evolucion_del_cliente(
    ejercicio_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    cliente_id: int = Depends(cliente_autorizado),
    db: Session = Depends(get_db),
):
    try:
        return estadisticas_service.evolucion_ejercicio(db, cliente_id, ejercicio_id, desde, hasta)
    except estadisticas_service.PeriodoInvalido:
        raise HTTPException(status_code=422, detail=_PERIODO_INVALIDO)
    except estadisticas_service.SinRegistros:
        raise HTTPException(status_code=404, detail="No hay registros para consultar")


@router.get("/clientes/{cliente_id}/peso", response_model=EvolucionPesoOut)
def peso_del_cliente(
    desde: date | None = None,
    hasta: date | None = None,
    cliente_id: int = Depends(cliente_autorizado),
    db: Session = Depends(get_db),
):
    return peso_service.obtener_evolucion(db, cliente_id, desde, hasta)


@router.get("/clientes/{cliente_id}/racha", response_model=RachaOut)
def racha_del_cliente(
    cliente_id: int = Depends(cliente_autorizado), db: Session = Depends(get_db)
):
    try:
        return racha_service.obtener_racha(db, cliente_id)
    except racha_service.PerfilIncompleto:
        raise HTTPException(status_code=409, detail="El cliente todavía no completó su perfil")