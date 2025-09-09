from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..db.session import get_db
from ..core.security import get_current_user
from ..models import Dataset
from ..schemas import DatasetOut
from ..services.ingestion import save_csv_and_get_db_uri

router = APIRouter()

@router.post("/upload", response_model=DatasetOut)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Apenas CSV é suportado")

    # 1) Criar registro de dataset
    ds = Dataset(
        owner_user_id=user.id,
        nome=file.filename,
        tipo="csv",
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    # 2) Salvar CSV no volume compartilhado e construir db_uri padrão de SQLite
    # Nota: a conversão em si pode ser feita sob demanda no worker quando uma connection usar este dataset
    import tempfile
    import os
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.write(await file.read())
    tmp.flush()
    tmp.close()

    db_uri = save_csv_and_get_db_uri(tmp.name, ds.id)
    try:
        os.unlink(tmp.name)
    except Exception:
        pass

    ds.source_path = f"dataset_{ds.id}/{file.filename}"
    ds.db_uri = db_uri
    db.commit()
    db.refresh(ds)
    return ds

@router.get("/", response_model=List[DatasetOut])
def list_datasets(db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(Dataset).filter((Dataset.owner_user_id == user.id) | (Dataset.owner_empresa_id != None))
    return q.order_by(Dataset.created_at.desc()).all()

@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset não encontrado")
    return ds

