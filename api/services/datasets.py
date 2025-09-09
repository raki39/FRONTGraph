import os
from typing import Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from api.config import settings
from api import models


def save_csv_and_create_sqlite(db: Session, owner_user_id: Optional[int], owner_empresa_id: Optional[int], nome: str, file_path: str) -> Tuple[models.Dataset, str]:
    """
    Converte CSV em SQLite (no diretório DATA_DIR compartilhado) e retorna db_uri.
    Grava Dataset no Postgres.
    """
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    # Normaliza nome do arquivo destino
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    sqlite_path = os.path.join(settings.DATA_DIR, f"{base_name}.db")

    # Carrega CSV e persiste em SQLite
    df = pd.read_csv(file_path)
    engine = create_engine(f"sqlite:///{sqlite_path}")
    df.to_sql("tabela", engine, if_exists="replace", index=False)

    db_uri = f"sqlite:///{sqlite_path}"

    ds = models.Dataset(
        owner_user_id=owner_user_id,
        owner_empresa_id=owner_empresa_id,
        nome=nome,
        tipo="csv",
        source_path=file_path,
        db_uri=db_uri,
        schema_snapshot=None,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    return ds, db_uri

