from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA_HORARIA = ZoneInfo("America/Argentina/Buenos_Aires")


def hoy() -> date:
    """Fecha actual en Argentina (el servidor puede estar en UTC)."""
    return datetime.now(ZONA_HORARIA).date()


def calcular_edad(fecha_nacimiento: date, referencia: date | None = None) -> int:
    referencia = referencia or hoy()
    cumplio = (referencia.month, referencia.day) >= (
        fecha_nacimiento.month,
        fecha_nacimiento.day,
    )
    return referencia.year - fecha_nacimiento.year - (0 if cumplio else 1)