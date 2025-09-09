from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..core.security import get_current_user
from ..models import Empresa
from ..schemas import EmpresaOut
from typing import List

router = APIRouter()

@router.get("/", response_model=List[EmpresaOut])
def list_empresas(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Empresa).order_by(Empresa.created_at.desc()).all()

