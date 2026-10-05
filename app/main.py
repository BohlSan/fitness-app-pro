from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db

app = FastAPI(title="Fitness App")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # RNF-13: mensaje comprensible, sin exponer detalles internos
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return {"status": "ok", "database": "connected"}
