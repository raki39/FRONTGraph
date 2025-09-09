"""
Nó para processamento de arquivos CSV
"""
import os
import shutil
import logging
import time
import pandas as pd
import numpy as np
from typing import Dict, Any, TypedDict, List, Optional
from sqlalchemy.types import DateTime, Integer, Float, String, Boolean
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

from agentgraph.utils.config import UPLOADED_CSV_PATH
from agentgraph.utils.object_manager import get_object_manager
import numpy as np

def analyze_numeric_column(sample_values: pd.Series) -> Dict[str, Any]:
    """
    Análise otimizada para detectar se coluna é numérica

    Args:
        sample_values: Amostra dos valores da coluna

    Returns:
        Dicionário com análise numérica
    """
    analysis = {
        "is_numeric": False,
        "is_integer": False,
        "numeric_ratio": 0.0,
        "has_decimals": False
    }

    if len(sample_values) == 0:
        return analysis

    # Converte para string e limpa valores
    str_values = sample_values.astype(str).str.strip()

    # Remove valores vazios e nulos
    clean_values = str_values[
        ~str_values.isin(['', 'nan', 'null', 'none', '-', 'NaN', 'NULL'])
    ]

    if len(clean_values) == 0:
        return analysis

    # Tenta conversão numérica vetorizada
    try:
        # Substitui vírgulas por pontos para formato brasileiro
        numeric_values = clean_values.str.replace(',', '.', regex=False)

        # Tenta conversão para float
        converted = pd.to_numeric(numeric_values, errors='coerce')

        # Conta valores válidos
        valid_count = converted.notna().sum()
        total_count = len(clean_values)

        analysis["numeric_ratio"] = valid_count / total_count if total_count > 0 else 0

        # Se mais de 80% são números válidos, considera numérico
        if analysis["numeric_ratio"] > 0.8:
            analysis["is_numeric"] = True

            # Verifica se são inteiros
            valid_numbers = converted.dropna()
            if len(valid_numbers) > 0:
                # Verifica se todos os números válidos são inteiros
                analysis["is_integer"] = all(
                    float(x).is_integer() for x in valid_numbers
                    if not pd.isna(x) and abs(x) < 1e15  # Evita overflow
                )
                analysis["has_decimals"] = not analysis["is_integer"]

    except Exception as e:
        logging.debug(f"Erro na análise numérica: {e}")
        analysis["is_numeric"] = False

    return analysis

def detect_date_format(date_string: str) -> str:
    """
    Detecta o formato mais provável de uma string de data

    Args:
        date_string: String para analisar

    Returns:
        'iso', 'american', 'brazilian' ou 'auto'
    """
    date_str = str(date_string).strip()

    # Formato ISO (YYYY-MM-DD ou YYYY/MM/DD)
    if len(date_str) >= 10 and date_str[4] in ['-', '/', '.'] and date_str[7] in ['-', '/', '.']:
        if date_str[:4].isdigit() and int(date_str[:4]) > 1900:
            return 'iso'

    # Verifica se pode ser formato americano (MM/DD/YYYY)
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            try:
                month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                # Se o primeiro número é > 12, provavelmente é DD/MM/YYYY
                if month > 12:
                    return 'brazilian'
                # Se o segundo número é > 12, provavelmente é MM/DD/YYYY
                elif day > 12:
                    return 'american'
                # Se ambos <= 12, é ambíguo, assume brasileiro por padrão
                else:
                    return 'brazilian'
            except:
                pass

    # Formato brasileiro por padrão (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY)
    return 'brazilian'

def smart_date_conversion(date_string: str):
    """
    Converte string para data usando detecção inteligente de formato

    Args:
        date_string: String da data

    Returns:
        Timestamp do pandas ou levanta exceção
    """
    format_type = detect_date_format(date_string)

    if format_type == 'iso':
        return pd.to_datetime(date_string, errors='raise')
    elif format_type == 'american':
        return pd.to_datetime(date_string, format='%m/%d/%Y', errors='raise')
    elif format_type == 'brazilian':
        return pd.to_datetime(date_string, dayfirst=True, errors='raise')
    else:
        # Fallback para detecção automática
        return pd.to_datetime(date_string, errors='raise')

async def process_dates_advanced(series: pd.Series) -> pd.Series:
    """
    Processa datas com múltiplos formatos de forma robusta

    Args:
        series: Série pandas com datas em formato texto

    Returns:
        Série com datas convertidas para datetime
    """
    # Formatos de data para tentar em ordem de prioridade
    date_formats = [
        '%d/%m/%Y',     # 01/12/2024
        '%d-%m-%Y',     # 01-12-2024
        '%Y-%m-%d',     # 2024-12-01
        '%d/%m/%y',     # 01/12/24
        '%d-%m-%y',     # 01-12-24
        '%Y/%m/%d',     # 2024/12/01
        '%d.%m.%Y',     # 01.12.2024
        '%Y.%m.%d',     # 2024.12.01
        '%d/%m/%Y %H:%M:%S',  # 01/12/2024 14:30:00
        '%Y-%m-%d %H:%M:%S',  # 2024-12-01 14:30:00
    ]

    result_series = pd.Series(index=series.index, dtype='datetime64[ns]')

    for idx, value in series.items():
        if pd.isna(value) or str(value).strip() in ['', 'nan', 'null', 'none', '-']:
            result_series[idx] = pd.NaT
            continue

        value_str = str(value).strip()
        converted = False

        # Tenta conversão automática com detecção inteligente de formato
        try:
            result_series[idx] = smart_date_conversion(value_str)
            converted = True
        except:
            pass

        # Se não funcionou, tenta formatos específicos
        if not converted:
            for fmt in date_formats:
                try:
                    result_series[idx] = pd.to_datetime(value_str, format=fmt, errors='raise')
                    converted = True
                    break
                except:
                    continue

        # Se ainda não converteu, marca como NaT
        if not converted:
            result_series[idx] = pd.NaT
            logging.warning(f"Não foi possível converter '{value_str}' para data")

    return result_series

class CSVProcessingState(TypedDict):
    """Estado para processamento de CSV"""
    file_path: str
    success: bool
    message: str
    csv_data_sample: dict
    column_info: dict
    processing_stats: dict

async def detect_column_types(df: pd.DataFrame, sample_size: int = 1000) -> Dict[str, Any]:
    """
    Detecta automaticamente os tipos de colunas de forma genérica e otimizada

    Args:
        df: DataFrame do pandas
        sample_size: Número de linhas para amostragem (otimização)

    Returns:
        Dicionário com informações dos tipos detectados
    """
    column_info = {
        "detected_types": {},
        "sql_types": {},
        "date_columns": [],
        "numeric_columns": [],
        "text_columns": [],
        "processing_rules": {}
    }

    # Usa amostra para otimizar performance em datasets grandes
    sample_df = df.sample(n=min(sample_size, len(df)), random_state=42) if len(df) > sample_size else df
    logging.info(f"[OPTIMIZATION] Usando amostra de {len(sample_df)} linhas para detecção de tipos")

    for col in df.columns:
        # Detecta tipo original
        original_type = str(df[col].dtype)
        column_info["detected_types"][col] = original_type

        # Usa amostra para análise
        sample_col = sample_df[col] if col in sample_df.columns else df[col]
        
        # Detecta números já convertidos pelo pandas
        if sample_col.dtype in ['int64', 'Int64', 'float64', 'Float64']:
            if 'int' in str(sample_col.dtype).lower():
                column_info["numeric_columns"].append(col)
                column_info["sql_types"][col] = Integer()
                column_info["processing_rules"][col] = "keep_as_int"
            else:
                column_info["numeric_columns"].append(col)
                column_info["sql_types"][col] = Float()
                column_info["processing_rules"][col] = "keep_as_float"
            continue

        # Para colunas de texto (object), detecta datas e números
        if sample_col.dtype == 'object':
            # Primeiro, tenta detectar datas
            sample_values = sample_col.dropna().head(20)
            date_success_count = 0

            # Formatos de data comuns para testar
            date_formats = [
                '%d/%m/%Y',     # 01/12/2024
                '%d-%m-%Y',     # 01-12-2024
                '%Y-%m-%d',     # 2024-12-01
                '%d/%m/%y',     # 01/12/24
                '%d-%m-%y',     # 01-12-24
                '%Y/%m/%d',     # 2024/12/01
                '%d.%m.%Y',     # 01.12.2024
                '%Y.%m.%d',     # 2024.12.01
            ]

            for val in sample_values:
                val_str = str(val).strip()
                if not val_str or val_str.lower() in ['nan', 'null', 'none', '-']:
                    continue

                # Tenta conversão automática com detecção inteligente
                try:
                    smart_date_conversion(val_str)
                    date_success_count += 1
                    continue
                except:
                    pass

                # Tenta formatos específicos
                for fmt in date_formats:
                    try:
                        pd.to_datetime(val_str, format=fmt, errors='raise')
                        date_success_count += 1
                        break
                    except:
                        continue

            # Se mais de 70% dos valores são datas válidas, considera como coluna de data
            if len(sample_values) > 0 and date_success_count / len(sample_values) > 0.7:
                column_info["date_columns"].append(col)
                column_info["sql_types"][col] = DateTime()
                column_info["processing_rules"][col] = "parse_dates_advanced"
                continue

            # Se não é data, tenta detectar números em colunas de texto (otimizado)
            # Análise otimizada de números em texto
            sample_values = sample_col.dropna().head(50)  # Aumenta amostra para melhor precisão

            if len(sample_values) == 0:
                column_info["text_columns"].append(col)
                column_info["sql_types"][col] = String()
                column_info["processing_rules"][col] = "keep_as_text"
                continue

            # Análise vetorizada para performance
            numeric_analysis = analyze_numeric_column(sample_values)

            if numeric_analysis["is_numeric"]:
                if numeric_analysis["is_integer"]:
                    column_info["numeric_columns"].append(col)
                    column_info["sql_types"][col] = Integer()
                    column_info["processing_rules"][col] = "convert_text_to_int_safe"
                    logging.debug(f"[TYPE_DETECTION] {col}: Detectado como INTEGER (ratio: {numeric_analysis['numeric_ratio']:.2f})")
                else:
                    column_info["numeric_columns"].append(col)
                    column_info["sql_types"][col] = Float()
                    column_info["processing_rules"][col] = "convert_text_to_float_safe"
                    logging.debug(f"[TYPE_DETECTION] {col}: Detectado como FLOAT (ratio: {numeric_analysis['numeric_ratio']:.2f})")
            else:
                # Mantém como texto
                column_info["text_columns"].append(col)
                column_info["sql_types"][col] = String()
                column_info["processing_rules"][col] = "keep_as_text"
                logging.debug(f"[TYPE_DETECTION] {col}: Mantido como TEXT (ratio: {numeric_analysis['numeric_ratio']:.2f})")
        else:
            # Outros tipos mantém como texto
            column_info["text_columns"].append(col)
            column_info["sql_types"][col] = String()
            column_info["processing_rules"][col] = "keep_as_text"

    # Log resumo dos tipos detectados
    logging.info(f"[TYPE_DETECTION] Resumo: {len(column_info['numeric_columns'])} numericas, {len(column_info['date_columns'])} datas, {len(column_info['text_columns'])} texto")
    if column_info['numeric_columns']:
        logging.info(f"[TYPE_DETECTION] Colunas numericas: {column_info['numeric_columns']}")

    return column_info

async def process_dataframe_generic(df: pd.DataFrame, column_info: Dict[str, Any]) -> pd.DataFrame:
    """
    Processa DataFrame com OTIMIZAÇÕES EXTREMAS para performance máxima

    Args:
        df: DataFrame original
        column_info: Informações dos tipos detectados

    Returns:
        DataFrame processado
    """
    logging.info(f"[ULTRA_OPTIMIZATION] Iniciando processamento ULTRA-OTIMIZADO de {len(df)} linhas")
    start_time = time.time()

    # OTIMIZAÇÃO 1: Evita cópia desnecessária - modifica in-place quando possível
    processed_df = df

    # OTIMIZAÇÃO 2: Agrupa colunas por tipo de processamento
    processing_groups = {
        'dates': [],
        'keep_numeric': [],
        'convert_numeric': [],
        'text': []
    }

    for col, rule in column_info["processing_rules"].items():
        if col not in processed_df.columns:
            continue

        if 'date' in rule:
            processing_groups['dates'].append((col, rule))
        elif 'keep_as' in rule:
            processing_groups['keep_numeric'].append((col, rule))
        elif 'convert' in rule:
            processing_groups['convert_numeric'].append((col, rule))
        else:
            processing_groups['text'].append((col, rule))

    # OTIMIZAÇÃO 3: Processamento paralelo por grupos
    await process_groups_parallel(processed_df, processing_groups)

    total_time = time.time() - start_time
    logging.info(f"[ULTRA_OPTIMIZATION] Processamento ULTRA-OTIMIZADO concluído em {total_time:.2f}s")

    return processed_df

async def process_groups_parallel(df: pd.DataFrame, groups: Dict[str, List]):
    """
    Processa grupos de colunas em paralelo para máxima performance
    """
    tasks = []

    # Processa cada grupo
    for group_name, columns in groups.items():
        if not columns:
            continue

        if group_name == 'dates':
            tasks.append(process_date_columns_batch(df, columns))
        elif group_name == 'keep_numeric':
            tasks.append(process_keep_numeric_batch(df, columns))
        elif group_name == 'convert_numeric':
            tasks.append(process_convert_numeric_batch(df, columns))
        # text não precisa processamento

    # Executa todos os grupos em paralelo
    if tasks:
        import asyncio
        await asyncio.gather(*tasks)

async def process_date_columns_batch(df: pd.DataFrame, date_columns: List[tuple]):
    """Processa colunas de data em lote"""
    for col, rule in date_columns:
        try:
            if rule == "parse_dates_advanced":
                # OTIMIZAÇÃO: Processamento vetorizado de datas
                df[col] = process_dates_vectorized(df[col])
            else:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
        except Exception as e:
            logging.warning(f"Erro ao processar data {col}: {e}")

async def process_keep_numeric_batch(df: pd.DataFrame, numeric_columns: List[tuple]):
    """Processa colunas numéricas que já estão no tipo correto"""
    for col, rule in numeric_columns:
        try:
            if rule == "keep_as_int" and df[col].dtype != 'Int64':
                df[col] = df[col].astype("Int64")
            elif rule == "keep_as_float" and df[col].dtype != 'float64':
                df[col] = df[col].astype("float64")
        except Exception as e:
            logging.warning(f"Erro ao manter tipo {col}: {e}")

async def process_convert_numeric_batch(df: pd.DataFrame, convert_columns: List[tuple]):
    """Processa conversões numéricas em lote com máxima otimização"""
    for col, rule in convert_columns:
        try:
            if rule == "convert_text_to_int_safe":
                df[col] = convert_to_int_ultra_optimized(df[col])
            elif rule == "convert_text_to_float_safe":
                df[col] = convert_to_float_ultra_optimized(df[col])
        except Exception as e:
            logging.warning(f"Erro ao converter {col}: {e}")

def convert_to_int_optimized(series: pd.Series) -> pd.Series:
    """
    Conversão otimizada para inteiros

    Args:
        series: Série para converter

    Returns:
        Série convertida para Int64
    """
    try:
        # Operações vetorizadas para performance
        cleaned = series.astype(str).str.strip()

        # Remove valores inválidos
        cleaned = cleaned.replace(['', 'nan', 'null', 'none', '-', 'NaN', 'NULL'], np.nan)

        # Substitui vírgulas por pontos
        cleaned = cleaned.str.replace(',', '.', regex=False)

        # Converte para numérico
        numeric = pd.to_numeric(cleaned, errors='coerce')

        # Verifica se pode ser convertido para inteiro sem perda
        # Só converte se todos os valores válidos são inteiros
        valid_mask = numeric.notna()
        if valid_mask.any():
            valid_numbers = numeric[valid_mask]
            # Verifica se são inteiros (sem parte decimal significativa)
            is_integer_mask = np.abs(valid_numbers - np.round(valid_numbers)) < 1e-10

            if is_integer_mask.all():
                # Todos são inteiros, pode converter
                result = numeric.round().astype("Int64")
            else:
                # Tem decimais, mantém como float mas avisa
                logging.warning(f"Coluna contém decimais, mantendo como float")
                result = numeric.astype("Float64")
        else:
            # Nenhum valor válido
            result = pd.Series([pd.NA] * len(series), dtype="Int64")

        return result

    except Exception as e:
        logging.error(f"Erro na conversão otimizada para int: {e}")
        return series

def convert_to_float_optimized(series: pd.Series) -> pd.Series:
    """
    Conversão otimizada para floats

    Args:
        series: Série para converter

    Returns:
        Série convertida para float64
    """
    try:
        # Operações vetorizadas para performance
        cleaned = series.astype(str).str.strip()

        # Remove valores inválidos
        cleaned = cleaned.replace(['', 'nan', 'null', 'none', '-', 'NaN', 'NULL'], np.nan)

        # Substitui vírgulas por pontos (formato brasileiro)
        cleaned = cleaned.str.replace(',', '.', regex=False)

        # Converte para numérico
        result = pd.to_numeric(cleaned, errors='coerce')

        return result

    except Exception as e:
        logging.error(f"Erro na conversão otimizada para float: {e}")
        return series

def convert_to_int_ultra_optimized(series: pd.Series) -> pd.Series:
    """
    Conversão ULTRA-OTIMIZADA para inteiros usando NumPy puro
    """
    try:
        # OTIMIZAÇÃO EXTREMA: Usa NumPy diretamente
        values = series.values

        # Se já é numérico, converte diretamente
        if pd.api.types.is_numeric_dtype(series):
            return pd.Series(values, dtype="Int64")

        # Para strings, usa operações vetorizadas do NumPy
        str_values = np.asarray(series.astype(str))

        # Máscara para valores válidos
        valid_mask = ~np.isin(str_values, ['', 'nan', 'null', 'none', '-', 'NaN', 'NULL'])

        # Inicializa resultado
        result = np.full(len(series), pd.NA, dtype=object)

        if valid_mask.any():
            valid_values = str_values[valid_mask]

            # Garante que são strings antes de usar np.char
            if valid_values.dtype.kind in ['U', 'S', 'O']:  # Unicode, bytes ou object
                # Remove vírgulas e converte
                cleaned = np.char.replace(valid_values.astype(str), ',', '.')
            else:
                # Se não são strings, converte primeiro
                cleaned = np.char.replace(np.asarray(valid_values, dtype=str), ',', '.')

            # Conversão vetorizada
            try:
                numeric_values = pd.to_numeric(cleaned, errors='coerce')
                # Só converte se são realmente inteiros
                valid_numeric = ~np.isnan(numeric_values)
                if valid_numeric.any():
                    int_mask = np.abs(numeric_values[valid_numeric] - np.round(numeric_values[valid_numeric])) < 1e-10
                    int_values = np.round(numeric_values[valid_numeric][int_mask]).astype('Int64')

                    # Atribui valores convertidos
                    valid_indices = np.where(valid_mask)[0]
                    numeric_indices = valid_indices[valid_numeric]
                    int_indices = numeric_indices[int_mask]
                    result[int_indices] = int_values

            except Exception as e:
                logging.debug(f"Erro na conversão vetorizada: {e}")

        return pd.Series(result, dtype="Int64")

    except Exception as e:
        logging.error(f"Erro na conversão ultra-otimizada para int: {e}")
        logging.debug(f"Tipo da serie: {series.dtype}, Primeiros valores: {series.head()}")
        return series

def convert_to_float_ultra_optimized(series: pd.Series) -> pd.Series:
    """
    Conversão ULTRA-OTIMIZADA para floats usando NumPy puro
    """
    try:
        # OTIMIZAÇÃO EXTREMA: Usa NumPy diretamente
        values = series.values

        # Se já é numérico, retorna diretamente
        if pd.api.types.is_numeric_dtype(series):
            return series.astype('float64')

        # Para strings, usa operações vetorizadas do NumPy
        str_values = np.asarray(series.astype(str))

        # Máscara para valores válidos
        valid_mask = ~np.isin(str_values, ['', 'nan', 'null', 'none', '-', 'NaN', 'NULL'])

        # Inicializa resultado
        result = np.full(len(series), np.nan, dtype='float64')

        if valid_mask.any():
            valid_values = str_values[valid_mask]

            # Garante que são strings antes de usar np.char
            if valid_values.dtype.kind in ['U', 'S', 'O']:  # Unicode, bytes ou object
                # Remove vírgulas (formato brasileiro)
                cleaned = np.char.replace(valid_values.astype(str), ',', '.')
            else:
                # Se não são strings, converte primeiro
                cleaned = np.char.replace(np.asarray(valid_values, dtype=str), ',', '.')

            # Conversão vetorizada ultra-rápida
            numeric_values = pd.to_numeric(cleaned, errors='coerce')
            result[valid_mask] = numeric_values

        return pd.Series(result, dtype='float64')

    except Exception as e:
        logging.error(f"Erro na conversão ultra-otimizada para float: {e}")
        logging.debug(f"Tipo da serie: {series.dtype}, Primeiros valores: {series.head()}")
        return series

def process_dates_vectorized(series: pd.Series) -> pd.Series:
    """
    Processamento vetorizado ULTRA-OTIMIZADO de datas
    """
    try:
        # OTIMIZAÇÃO: Tenta conversão direta primeiro
        try:
            return pd.to_datetime(series, dayfirst=True, errors='coerce')
        except:
            pass

        # Se falhou, usa abordagem mais robusta mas ainda otimizada
        str_values = series.astype(str)

        # Detecta formato mais comum na amostra
        sample = str_values.dropna().head(100)
        if len(sample) > 0:
            first_val = sample.iloc[0]

            # Detecta formato baseado no primeiro valor
            if len(first_val) >= 10 and first_val[4] in ['-', '/']:
                # Formato ISO
                return pd.to_datetime(series, errors='coerce')
            else:
                # Formato brasileiro
                return pd.to_datetime(series, dayfirst=True, errors='coerce')

        return pd.to_datetime(series, errors='coerce')

    except Exception as e:
        logging.error(f"Erro no processamento vetorizado de datas: {e}")
        return series

async def csv_processing_node(state: CSVProcessingState) -> CSVProcessingState:
    """
    Nó principal para processamento de CSV
    
    Args:
        state: Estado do processamento CSV
        
    Returns:
        Estado atualizado
    """
    try:
        file_path = state["file_path"]
        
        # Copia arquivo para diretório de upload
        shutil.copy(file_path, UPLOADED_CSV_PATH)
        logging.info(f"[CSV_PROCESSING] Arquivo copiado para: {UPLOADED_CSV_PATH}")
        
        # OTIMIZAÇÃO EXTREMA: Leitura de CSV ultra-otimizada
        separators = [';', ',', '\t', '|']
        df = None
        used_separator = None

        # Detecta separador com amostra mínima
        for sep in separators:
            try:
                test_df = pd.read_csv(file_path, sep=sep, nrows=3, engine='c')  # Engine C é mais rápido
                if len(test_df.columns) > 1:
                    # OTIMIZAÇÃO: Lê com configurações de performance máxima
                    df = pd.read_csv(
                        file_path,
                        sep=sep,
                        encoding='utf-8',
                        on_bad_lines="skip",
                        engine='c',  # Engine C para máxima performance
                        low_memory=False,  # Evita warnings de tipos mistos
                        dtype=str  # Lê tudo como string primeiro (mais rápido)
                    )
                    used_separator = sep
                    break
            except:
                continue
        
        if df is None:
            raise ValueError("Não foi possível detectar o formato do CSV")
        
        logging.info(f"[CSV_PROCESSING] CSV lido com separador '{used_separator}', {len(df)} linhas, {len(df.columns)} colunas")
        
        # Detecta tipos de colunas automaticamente
        column_info = await detect_column_types(df)
        
        # Processa DataFrame
        processed_df = await process_dataframe_generic(df, column_info)
        
        # Estatísticas do processamento
        processing_stats = {
            "original_rows": len(df),
            "processed_rows": len(processed_df),
            "original_columns": len(df.columns),
            "processed_columns": len(processed_df.columns),
            "separator_used": used_separator,
            "date_columns_detected": len(column_info["date_columns"]),
            "numeric_columns_detected": len(column_info["numeric_columns"]),
            "text_columns_detected": len(column_info["text_columns"])
        }
        
        # Amostra dos dados para o estado
        csv_data_sample = {
            "head": processed_df.head(5).to_dict(),
            "dtypes": processed_df.dtypes.astype(str).to_dict(),
            "columns": list(processed_df.columns)
        }
        
        # Armazena DataFrame processado no gerenciador de objetos
        obj_manager = get_object_manager()
        df_id = obj_manager.store_object(processed_df, "processed_dataframe")
        
        # Atualiza estado
        state.update({
            "success": True,
            "message": f"✅ CSV processado com sucesso! {processing_stats['processed_rows']} linhas, {processing_stats['processed_columns']} colunas",
            "csv_data_sample": csv_data_sample,
            "column_info": column_info,
            "processing_stats": processing_stats,
            "dataframe_id": df_id
        })
        
        logging.info(f"[CSV_PROCESSING] Processamento concluído: {processing_stats}")
        
    except Exception as e:
        error_msg = f"❌ Erro ao processar CSV: {e}"
        logging.error(f"[CSV_PROCESSING] {error_msg}")
        state.update({
            "success": False,
            "message": error_msg,
            "csv_data_sample": {},
            "column_info": {},
            "processing_stats": {}
        })
    
    return state
