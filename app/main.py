from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import auth, ejercicios, entrenamientos, perfil, rutinas, trainer

class StaticFilesSinCache(StaticFiles):
    """Obliga al navegador a revalidar los archivos del frontend en cada carga."""

    async def get_response(self, path, scope):
        respuesta = await super().get_response(path, scope)
        respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta


app = FastAPI(title="Fitness App")

app.include_router(auth.router)
app.include_router(perfil.router)
app.include_router(ejercicios.router)
app.include_router(rutinas.router)
app.include_router(entrenamientos.router)
app.include_router(trainer.router)



@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # RNF-13: mensaje comprensible, sin exponer detalles internos
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return {"status": "ok", "database": "connected"}


# Debe ir al final: sirve el frontend desde "/"
app.mount(
    "/",
    StaticFilesSinCache(directory=Path(__file__).parent / "static", html=True),
    name="static",
)