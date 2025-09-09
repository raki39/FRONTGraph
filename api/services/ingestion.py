from pathlib import Path
import shutil
import pandas as pd
import logging
from sqlalchemy import create_engine
from ..core.settings import settings

logger = logging.getLogger(__name__)

DATASET_DIR = settings.DATA_DIR


def save_csv_and_get_db_uri(uploaded_path: str, dataset_id: int) -> str:
    """Move CSV para pasta compartilhada, converte para SQLite (tabela 'tabela') e retorna db_uri.
    Garante que o worker do agente encontrará o arquivo SQLite existente.
    """
    logger.info(f"📁 Processando upload: dataset_id={dataset_id}")
    logger.info(f"📂 DATA_DIR configurado: {DATASET_DIR}")

    src = Path(uploaded_path)
    dst_dir = DATASET_DIR / f"dataset_{dataset_id}"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_csv = dst_dir / src.name

    logger.info(f"📋 Copiando CSV: {src} → {dst_csv}")
    shutil.copy2(src, dst_csv)
    logger.info(f"✅ CSV copiado com sucesso")

    # Cria SQLite ao lado do CSV
    sqlite_path = dst_dir / "data.db"
    # Usar caminho absoluto para garantir que worker encontre o arquivo
    db_uri = f"sqlite:///{sqlite_path.absolute().as_posix()}"

    logger.info(f"🗄️ Criando SQLite: {sqlite_path.absolute()}")
    logger.info(f"🔗 DB URI: {db_uri}")

    try:
        # Leitura simples do CSV; heurísticas de separador podem ser adicionadas depois
        logger.info(f"📊 Lendo CSV: {dst_csv}")

        # Tentar diferentes separadores
        try:
            df = pd.read_csv(dst_csv)
        except:
            logger.info("📊 Tentando com separador ';'")
            df = pd.read_csv(dst_csv, sep=';')

        logger.info(f"📈 CSV carregado: {len(df)} linhas, {len(df.columns)} colunas")

        engine = create_engine(db_uri)
        with engine.begin() as conn:
            df.to_sql("tabela", conn, if_exists="replace", index=False)

        logger.info(f"✅ SQLite criado com sucesso: {sqlite_path}")

        # Verificar se arquivo foi criado
        if sqlite_path.exists():
            logger.info(f"✅ Arquivo SQLite confirmado: {sqlite_path.stat().st_size} bytes")
        else:
            logger.error(f"❌ Arquivo SQLite não foi criado: {sqlite_path}")

    except Exception as e:
        logger.error(f"❌ Erro ao criar SQLite: {e}")
        raise  # Re-raise para não mascarar o erro

    return db_uri

