from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.usuario import RolUsuario, Usuario
from app.schemas.habitos import DiaHidratacionOut, HidratacionDiaOut, HidratacionIn
from app.services import hidratacion_service

router = APIRouter(prefix="/hidratacion", tags=["Hidratación"])

solo_usuario = require_role(RolUsuario.USUARIO)

_SIN_PERFIL = "Completá tu perfil para registrar tu hidratación"


@router.get("", response_model=HidratacionDiaOut)
def dia(
    fecha: date | None = None,
    usuario: Usuario = Depends(solo_usuario),
    db: Session = Depends(get_db),
):
    try:
        return hidratacion_service.obtener_dia(db, usuario.id, fecha)
    except hidratacion_service.PerfilIncompleto:
        raise HTTPException(status_code=409, detail=_SIN_PERFIL)


# Debe declararse antes de rutas con parámetro de ruta
@router.get("/historial", response_model=list[DiaHidratacionOut])
def historial(
    dias: int = Query(default=14, ge=1, le=120),
    usuario: Usuario = Depends(solo_usuario),
    db: Session = Depends(get_db),
):
    try:
        return hidratacion_service.historial(db, usuario.id, dias)
    except hidratacion_service.PerfilIncompleto:
        raise HTTPException(status_code=409, detail=_SIN_PERFIL)


@router.post("", response_model=HidratacionDiaOut, status_code=status.HTTP_201_CREATED)
def registrar(
    datos: HidratacionIn,
    usuario: Usuario = Depends(solo_usuario),
    db: Session = Depends(get_db),
):
    try:
        hidratacion_service.registrar(db, usuario.id, datos.cantidad_ml, datos.fecha)
    except hidratacion_service.PerfilIncompleto:
        raise HTTPException(status_code=409, detail=_SIN_PERFIL)
    except hidratacion_service.FechaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error))
    return hidratacion_service.obtener_dia(db, usuario.id, datos.fecha)


@router.delete("/{registro_id}", response_model=HidratacionDiaOut)
def eliminar(
    registro_id: int,
    usuario: Usuario = Depends(solo_usuario),
    db: Session = Depends(get_db),
):
    try:
        fecha = hidratacion_service.eliminar(db, usuario.id, registro_id)
    except hidratacion_service.RegistroNoEncontrado:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return hidratacion_service.obtener_dia(db, usuario.id, fecha)