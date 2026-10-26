from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ZONA_HORARIA = ZoneInfo("America/Argentina/Buenos_Aires")


def hoy() -> date:
    """Fecha actual en Argentina (el servidor puede estar en UTC)."""
    return datetime.now(ZONA_HORARIA).date()


def ahora_utc() -> datetime:
    """Instante actual con zona horaria, para registrar inicio y fin."""
    return datetime.now(timezone.utc)


def calcular_edad(fecha_nacimiento: date, referencia: date | None = None) -> int:
    referencia = referencia or hoy()
    cumplio = (referencia.month, referencia.day) >= (
        fecha_nacimiento.month,
        fecha_nacimiento.day,
    )
    return referencia.year - fecha_nacimiento.year - (0 if cumplio else 1)