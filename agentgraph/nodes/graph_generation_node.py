"""
Nó para geração de gráficos
"""
import io
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from PIL import Image
from typing import Dict, Any, Optional

from agentgraph.utils.object_manager import get_object_manager

async def graph_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para geração de gráficos baseado no tipo selecionado
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado com gráfico gerado
    """
    try:
        logging.info("[GRAPH_GENERATION] Iniciando geração de gráfico")
        
        # Verifica se há tipo de gráfico selecionado
        graph_type = state.get("graph_type")
        if not graph_type:
            logging.info("[GRAPH_GENERATION] Nenhum tipo de gráfico selecionado, pulando geração")
            return state
        
        # Verifica se há erro anterior
        if state.get("graph_error"):
            logging.info("[GRAPH_GENERATION] Erro anterior detectado, pulando geração")
            return state
        
        # Recupera dados do gráfico
        graph_data = state.get("graph_data", {})
        data_id = graph_data.get("data_id")
        
        if not data_id:
            error_msg = "ID dos dados do gráfico não encontrado"
            logging.error(f"[GRAPH_GENERATION] {error_msg}")
            state.update({
                "graph_error": error_msg,
                "graph_generated": False
            })
            return state
        
        # Recupera DataFrame dos dados
        obj_manager = get_object_manager()
        df = obj_manager.get_object(data_id)
        
        if df is None or df.empty:
            error_msg = "Dados do gráfico não encontrados ou vazios"
            logging.error(f"[GRAPH_GENERATION] {error_msg}")
            state.update({
                "graph_error": error_msg,
                "graph_generated": False
            })
            return state
        
        # Gera título do gráfico baseado na pergunta do usuário
        user_query = state.get("user_input", "")
        title = f"Visualização: {user_query[:50]}..." if len(user_query) > 50 else f"Visualização: {user_query}"
        
        # Gera o gráfico
        graph_image = await generate_graph(df, graph_type, title, user_query)
        
        if graph_image is None:
            error_msg = f"Falha ao gerar gráfico do tipo {graph_type}"
            logging.error(f"[GRAPH_GENERATION] {error_msg}")
            state.update({
                "graph_error": error_msg,
                "graph_generated": False
            })
            return state
        
        # Armazena imagem do gráfico no ObjectManager
        graph_image_id = obj_manager.store_object(graph_image, "graph_image")
        
        # Atualiza estado
        state.update({
            "graph_image_id": graph_image_id,
            "graph_generated": True,
            "graph_error": None
        })
        
        logging.info(f"[GRAPH_GENERATION] Gráfico gerado com sucesso: {graph_type}")
        
    except Exception as e:
        error_msg = f"Erro na geração de gráfico: {e}"
        logging.error(f"[GRAPH_GENERATION] {error_msg}")
        state.update({
            "graph_error": error_msg,
            "graph_generated": False
        })
    
    return state

async def generate_graph(df: pd.DataFrame, graph_type: str, title: str = None, user_query: str = None) -> Optional[Image.Image]:
    """
    Gera um gráfico com base no DataFrame e tipo especificado
    
    Args:
        df: DataFrame com os dados
        graph_type: Tipo de gráfico a ser gerado
        title: Título do gráfico
        user_query: Pergunta original do usuário
        
    Returns:
        Imagem PIL do gráfico ou None se falhar
    """
    logging.info(f"[GRAPH_GENERATION] Gerando gráfico tipo {graph_type}. DataFrame: {len(df)} linhas")
    
    if df.empty:
        logging.warning("[GRAPH_GENERATION] DataFrame vazio")
        return None
    
    try:
        # Preparar dados usando lógica UNIFICADA
        prepared_df = prepare_data_for_graph_unified(df, graph_type, user_query)
        if prepared_df.empty:
            logging.warning("[GRAPH_GENERATION] DataFrame preparado está vazio")
            return None
        
        # Configurações gerais
        plt.style.use('default')
        colors = plt.cm.tab10.colors
        
        # Gerar gráfico baseado no tipo
        if graph_type == 'line_simple':
            return await generate_line_simple(prepared_df, title, colors)
        elif graph_type == 'multiline':
            return await generate_multiline(prepared_df, title, colors)
        elif graph_type == 'area':
            return await generate_area(prepared_df, title, colors)
        elif graph_type == 'bar_vertical':
            return await generate_bar_vertical(prepared_df, title, colors)
        elif graph_type == 'bar_horizontal':
            return await generate_bar_horizontal(prepared_df, title, colors)
        elif graph_type == 'bar_grouped':
            return await generate_bar_grouped(prepared_df, title, colors)
        elif graph_type == 'bar_stacked':
            return await generate_bar_stacked(prepared_df, title, colors)
        elif graph_type == 'pie':
            return await generate_pie(prepared_df, title, colors)
        elif graph_type == 'donut':
            return await generate_donut(prepared_df, title, colors)
        elif graph_type == 'pie_multiple':
            return await generate_pie_multiple(prepared_df, title, colors)
        else:
            logging.warning(f"[GRAPH_GENERATION] Tipo '{graph_type}' não reconhecido, usando bar_vertical")
            return await generate_bar_vertical(prepared_df, title, colors)
            
    except Exception as e:
        logging.error(f"[GRAPH_GENERATION] Erro ao gerar gráfico: {e}")
        return None

def analyze_dataframe_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analisa a estrutura do DataFrame e retorna informações detalhadas

    Args:
        df: DataFrame a ser analisado

    Returns:
        Dicionário com informações sobre tipos de colunas e estrutura
    """
    if df.empty:
        return {
            'numeric_cols': [],
            'date_cols': [],
            'categorical_cols': [],
            'total_cols': 0,
            'has_multiple_numerics': False,
            'has_multiple_categoricals': False,
            'is_suitable_for_grouping': False
        }

    # Analisar tipos de colunas de forma mais robusta
    numeric_cols = []
    date_cols = []
    categorical_cols = []

    for col in df.columns:
        col_data = df[col]

        # Verificar se é numérico (incluindo strings que representam números)
        if pd.api.types.is_numeric_dtype(col_data):
            numeric_cols.append(col)
        elif col_data.dtype == 'object':
            # Tentar converter para numérico
            try:
                test_numeric = pd.to_numeric(col_data.astype(str).str.replace(',', '.'), errors='coerce')
                if test_numeric.notna().sum() > len(col_data) * 0.8:  # 80% são números válidos
                    numeric_cols.append(col)
                else:
                    # Verificar se é data
                    if any(date_indicator in col.lower() for date_indicator in ['data', 'date', 'time', 'dia', 'mes', 'ano']):
                        try:
                            pd.to_datetime(col_data.head(3), errors='raise')
                            date_cols.append(col)
                        except:
                            categorical_cols.append(col)
                    else:
                        categorical_cols.append(col)
            except:
                categorical_cols.append(col)
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            date_cols.append(col)
        else:
            categorical_cols.append(col)

    return {
        'numeric_cols': numeric_cols,
        'date_cols': date_cols,
        'categorical_cols': categorical_cols,
        'total_cols': len(df.columns),
        'has_multiple_numerics': len(numeric_cols) >= 2,
        'has_multiple_categoricals': len(categorical_cols) >= 2,
        'is_suitable_for_grouping': len(categorical_cols) >= 2 or (len(categorical_cols) >= 1 and len(numeric_cols) >= 2)
    }

def prepare_data_for_graph_unified(df: pd.DataFrame, graph_type: str, user_query: str = None) -> pd.DataFrame:
    """
    FUNÇÃO UNIFICADA para preparação de dados - substitui lógica duplicada

    Args:
        df: DataFrame original
        graph_type: Tipo de gráfico
        user_query: Pergunta do usuário

    Returns:
        DataFrame preparado com colunas adequadas para o tipo de gráfico
    """
    logging.info(f"[GRAPH_GENERATION] 🔧 Preparação UNIFICADA para {graph_type}")

    if df.empty:
        logging.warning("[GRAPH_GENERATION] DataFrame vazio")
        return df

    # Fazer cópia para não modificar original
    prepared_df = df.copy()

    # Analisar estrutura do DataFrame
    structure = analyze_dataframe_structure(prepared_df)
    numeric_cols = structure['numeric_cols']
    date_cols = structure['date_cols']
    categorical_cols = structure['categorical_cols']

    logging.info(f"[GRAPH_GENERATION] 📊 Estrutura: {len(numeric_cols)} numéricas, {len(date_cols)} datas, {len(categorical_cols)} categóricas")

    # Preparação específica por tipo de gráfico
    if graph_type in ['line_simple', 'area']:
        return _prepare_for_temporal_graphs(prepared_df, date_cols, numeric_cols, categorical_cols)

    elif graph_type in ['bar_vertical', 'bar_horizontal']:
        return _prepare_for_simple_bar_graphs(prepared_df, categorical_cols, numeric_cols, graph_type)

    elif graph_type in ['bar_grouped', 'bar_stacked']:
        return _prepare_for_grouped_graphs(prepared_df, structure, graph_type)

    elif graph_type in ['pie', 'donut', 'pie_multiple']:
        return _prepare_for_pie_graphs(prepared_df, categorical_cols, numeric_cols, graph_type)

    elif graph_type == 'multiline':
        return _prepare_for_multiline_graphs(prepared_df, structure)

    else:
        logging.warning(f"[GRAPH_GENERATION] Tipo {graph_type} não reconhecido, usando preparação básica")
        return _prepare_basic_fallback(prepared_df, categorical_cols, numeric_cols)

def _prepare_for_temporal_graphs(df: pd.DataFrame, date_cols: list, numeric_cols: list, categorical_cols: list) -> pd.DataFrame:
    """Prepara dados para gráficos temporais (linha, área)"""
    if date_cols and numeric_cols:
        # Usar primeira coluna de data e primeira numérica
        x_col, y_col = date_cols[0], numeric_cols[0]
        result_df = df[[x_col, y_col]].sort_values(by=x_col)
        logging.info(f"[GRAPH_GENERATION] 📅 Temporal: {x_col} (data) + {y_col} (numérica)")
        return result_df
    elif categorical_cols and numeric_cols:
        # Usar primeira categórica e primeira numérica
        x_col, y_col = categorical_cols[0], numeric_cols[0]
        result_df = df[[x_col, y_col]].sort_values(by=y_col)
        logging.info(f"[GRAPH_GENERATION] 📊 Categórico: {x_col} + {y_col}")
        return result_df
    else:
        logging.warning("[GRAPH_GENERATION] Dados insuficientes para gráfico temporal")
        return df

def _prepare_for_simple_bar_graphs(df: pd.DataFrame, categorical_cols: list, numeric_cols: list, graph_type: str) -> pd.DataFrame:
    """Prepara dados para gráficos de barras simples"""
    if categorical_cols and numeric_cols:
        x_col, y_col = categorical_cols[0], numeric_cols[0]
        result_df = df[[x_col, y_col]].sort_values(by=y_col, ascending=False)

        # Limitar categorias para barras verticais
        if graph_type == 'bar_vertical' and len(result_df) > 15:
            result_df = result_df.head(15)
            logging.info(f"[GRAPH_GENERATION] 📊 Limitado a 15 categorias para {graph_type}")

        logging.info(f"[GRAPH_GENERATION] 📊 Barras simples: {x_col} + {y_col}")
        return result_df
    else:
        logging.warning("[GRAPH_GENERATION] Dados insuficientes para gráfico de barras")
        return df

def _prepare_for_grouped_graphs(df: pd.DataFrame, structure: dict, graph_type: str) -> pd.DataFrame:
    """
    FUNÇÃO CRÍTICA: Prepara dados para gráficos agrupados com lógica inteligente
    """
    numeric_cols = structure['numeric_cols']
    categorical_cols = structure['categorical_cols']
    has_multiple_numerics = structure['has_multiple_numerics']
    has_multiple_categoricals = structure['has_multiple_categoricals']

    logging.info(f"[GRAPH_GENERATION] 🎯 Preparando agrupado: {len(numeric_cols)} num, {len(categorical_cols)} cat")

    if has_multiple_numerics:
        # CENÁRIO 1: Múltiplas numéricas - usar primeira categórica + todas numéricas
        cols_to_keep = [categorical_cols[0]] + numeric_cols
        result_df = df[cols_to_keep]
        logging.info(f"[GRAPH_GENERATION] ✅ Múltiplas numéricas: {cols_to_keep}")
        return result_df

    elif len(numeric_cols) == 1 and has_multiple_categoricals:
        # CENÁRIO 2: 1 numérica + múltiplas categóricas - AGRUPAMENTO POR COR
        # Usar TODAS as categóricas + a numérica
        cols_to_keep = categorical_cols + numeric_cols
        result_df = df[cols_to_keep]
        logging.info(f"[GRAPH_GENERATION] ✅ Agrupamento por cor: {cols_to_keep}")
        return result_df

    elif len(numeric_cols) == 1 and len(categorical_cols) == 1:
        # CENÁRIO 3: 1 numérica + 1 categórica - gráfico simples
        cols_to_keep = categorical_cols + numeric_cols
        result_df = df[cols_to_keep]
        logging.info(f"[GRAPH_GENERATION] ⚠️ Dados simples para agrupado: {cols_to_keep}")
        return result_df

    else:
        # CENÁRIO 4: Dados inadequados
        logging.warning("[GRAPH_GENERATION] ❌ Dados inadequados para gráfico agrupado")
        return df

def _prepare_for_pie_graphs(df: pd.DataFrame, categorical_cols: list, numeric_cols: list, graph_type: str) -> pd.DataFrame:
    """Prepara dados para gráficos de pizza"""
    if categorical_cols and numeric_cols:
        cat_col, val_col = categorical_cols[0], numeric_cols[0]

        if graph_type == 'pie_multiple' and len(categorical_cols) >= 2:
            # Para pizzas múltiplas, manter 2 categóricas + 1 numérica
            result_df = df[[categorical_cols[0], categorical_cols[1], val_col]]
            logging.info(f"[GRAPH_GENERATION] 🥧 Pizzas múltiplas: {result_df.columns.tolist()}")
        else:
            # Agrupar e somar valores para pizza simples/donut
            result_df = df.groupby(cat_col)[val_col].sum().reset_index()
            result_df = result_df.sort_values(by=val_col, ascending=False)

            # Limitar a 10 categorias
            if len(result_df) > 10:
                top_9 = result_df.head(9)
                others_sum = result_df.iloc[9:][val_col].sum()
                if others_sum > 0:
                    others_row = pd.DataFrame({cat_col: ['Outros'], val_col: [others_sum]})
                    result_df = pd.concat([top_9, others_row], ignore_index=True)
                else:
                    result_df = top_9

            logging.info(f"[GRAPH_GENERATION] 🥧 Pizza: {cat_col} + {val_col} ({len(result_df)} categorias)")

        return result_df
    else:
        logging.warning("[GRAPH_GENERATION] Dados insuficientes para gráfico de pizza")
        return df

def _prepare_for_multiline_graphs(df: pd.DataFrame, structure: dict) -> pd.DataFrame:
    """Prepara dados para gráficos de múltiplas linhas"""
    date_cols = structure['date_cols']
    numeric_cols = structure['numeric_cols']
    categorical_cols = structure['categorical_cols']

    if date_cols and len(numeric_cols) >= 2:
        # Data + múltiplas numéricas
        cols_to_keep = [date_cols[0]] + numeric_cols
        result_df = df[cols_to_keep].sort_values(by=date_cols[0])
        logging.info(f"[GRAPH_GENERATION] 📈 Multilinhas temporais: {cols_to_keep}")
        return result_df
    elif categorical_cols and len(numeric_cols) >= 2:
        # Categórica + múltiplas numéricas
        cols_to_keep = [categorical_cols[0]] + numeric_cols
        result_df = df[cols_to_keep]
        logging.info(f"[GRAPH_GENERATION] 📈 Multilinhas categóricas: {cols_to_keep}")
        return result_df
    else:
        logging.warning("[GRAPH_GENERATION] Dados insuficientes para multilinhas")
        return df

def _prepare_basic_fallback(df: pd.DataFrame, categorical_cols: list, numeric_cols: list) -> pd.DataFrame:
    """Preparação básica de fallback"""
    if categorical_cols and numeric_cols:
        result_df = df[[categorical_cols[0], numeric_cols[0]]]
        logging.info(f"[GRAPH_GENERATION] 🔄 Fallback básico: {result_df.columns.tolist()}")
        return result_df
    else:
        logging.warning("[GRAPH_GENERATION] Dados inadequados para qualquer gráfico")
        return df

def save_plot_to_image() -> Image.Image:
    """
    Salva o plot atual do matplotlib como imagem PIL

    Returns:
        Imagem PIL
    """
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    img = Image.open(buf)
    plt.close()  # Importante: fechar o plot para liberar memória
    return img

# ==================== FUNÇÕES DE GERAÇÃO ESPECÍFICAS ====================

async def generate_line_simple(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """Gera gráfico de linha simples"""
    if len(df.columns) < 2:
        return None

    x_col, y_col = df.columns[0], df.columns[1]
    is_date = pd.api.types.is_datetime64_any_dtype(df[x_col])

    plt.figure(figsize=(12, 6))

    if is_date:
        plt.plot(df[x_col], df[y_col], marker='o', linewidth=2, color=colors[0])
        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
    else:
        plt.plot(range(len(df)), df[y_col], marker='o', linewidth=2, color=colors[0])
        plt.xticks(range(len(df)), df[x_col], rotation=45, ha='right')

    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.title(title or f"{y_col} por {x_col}")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    return save_plot_to_image()

async def generate_multiline(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """Gera gráfico de múltiplas linhas"""
    if len(df.columns) < 2:
        return None

    x_col = df.columns[0]
    y_cols = [col for col in df.columns[1:] if pd.api.types.is_numeric_dtype(df[col])]

    if not y_cols:
        return await generate_line_simple(df, title, colors)

    is_date = pd.api.types.is_datetime64_any_dtype(df[x_col])

    plt.figure(figsize=(12, 6))

    for i, y_col in enumerate(y_cols):
        if is_date:
            plt.plot(df[x_col], df[y_col], marker='o', linewidth=2,
                    label=y_col, color=colors[i % len(colors)])
        else:
            plt.plot(range(len(df)), df[y_col], marker='o', linewidth=2,
                    label=y_col, color=colors[i % len(colors)])

    if is_date:
        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
    else:
        plt.xticks(range(len(df)), df[x_col], rotation=45, ha='right')

    plt.xlabel(x_col)
    plt.ylabel("Valores")
    plt.title(title or f"Comparação por {x_col}")
    plt.legend(title="Séries", loc='best')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    return save_plot_to_image()

async def generate_area(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """Gera gráfico de área"""
    if len(df.columns) < 2:
        return None

    x_col, y_col = df.columns[0], df.columns[1]
    is_date = pd.api.types.is_datetime64_any_dtype(df[x_col])

    plt.figure(figsize=(12, 6))

    if is_date:
        plt.fill_between(df[x_col], df[y_col], alpha=0.5, color=colors[0])
        plt.plot(df[x_col], df[y_col], color=colors[0], linewidth=2)
        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
    else:
        plt.fill_between(range(len(df)), df[y_col], alpha=0.5, color=colors[0])
        plt.plot(range(len(df)), df[y_col], color=colors[0], linewidth=2)
        plt.xticks(range(len(df)), df[x_col], rotation=45, ha='right')

    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.title(title or f"{y_col} por {x_col}")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    return save_plot_to_image()

async def generate_bar_vertical(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """Gera gráfico de barras verticais"""
    if len(df.columns) < 2:
        return None

    x_col, y_col = df.columns[0], df.columns[1]

    # Preparar dados numéricos - converter strings com vírgula para float
    df_plot = df.copy()
    try:
        if df_plot[y_col].dtype == 'object':
            # Converte strings para números, tratando vírgulas como separador decimal
            df_plot[y_col] = pd.to_numeric(df_plot[y_col].astype(str).str.replace(',', '.'), errors='coerce')

        # Remove linhas com valores não numéricos
        df_plot = df_plot.dropna(subset=[y_col])

        if df_plot.empty:
            logging.error(f"[GRAPH_GENERATION] Nenhum valor numérico válido encontrado na coluna {y_col}")
            return None

    except Exception as e:
        logging.error(f"[GRAPH_GENERATION] Erro ao converter dados para numérico: {e}")
        return None

    plt.figure(figsize=(12, 8))
    bars = plt.bar(range(len(df_plot)), df_plot[y_col], color=colors[0])

    # Adicionar valores nas barras
    try:
        max_value = df_plot[y_col].max()
        for i, bar in enumerate(bars):
            height = bar.get_height()
            if isinstance(height, (int, float)) and not pd.isna(height):
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.02 * max_value,
                        f'{height:,.0f}', ha='center', fontsize=9)
    except Exception as e:
        logging.warning(f"[GRAPH_GENERATION] Erro ao adicionar valores nas barras: {e}")

    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.title(title or f"{y_col} por {x_col}")
    plt.xticks(range(len(df_plot)), df_plot[x_col], rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.7, axis='y')
    plt.tight_layout()

    return save_plot_to_image()

async def generate_bar_horizontal(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """Gera gráfico de barras horizontais"""
    if len(df.columns) < 2:
        return None

    x_col, y_col = df.columns[0], df.columns[1]

    # Preparar dados numéricos - converter strings com vírgula para float
    df_plot = df.copy()
    try:
        if df_plot[y_col].dtype == 'object':
            # Converte strings para números, tratando vírgulas como separador decimal
            df_plot[y_col] = pd.to_numeric(df_plot[y_col].astype(str).str.replace(',', '.'), errors='coerce')

        # Remove linhas com valores não numéricos
        df_plot = df_plot.dropna(subset=[y_col])

        if df_plot.empty:
            logging.error(f"[GRAPH_GENERATION] Nenhum valor numérico válido encontrado na coluna {y_col}")
            return None

    except Exception as e:
        logging.error(f"[GRAPH_GENERATION] Erro ao converter dados para numérico: {e}")
        return None

    plt.figure(figsize=(12, max(6, len(df_plot) * 0.4)))
    bars = plt.barh(range(len(df_plot)), df_plot[y_col], color=colors[0])

    # Adicionar valores nas barras
    try:
        max_value = df_plot[y_col].max()
        for i, bar in enumerate(bars):
            width = bar.get_width()
            if isinstance(width, (int, float)) and not pd.isna(width):
                plt.text(width + 0.02 * max_value, bar.get_y() + bar.get_height()/2.,
                        f'{width:,.0f}', va='center', fontsize=9)
    except Exception as e:
        logging.warning(f"[GRAPH_GENERATION] Erro ao adicionar valores nas barras: {e}")

    plt.xlabel(y_col)
    plt.ylabel(x_col)
    plt.title(title or f"{y_col} por {x_col}")
    plt.yticks(range(len(df_plot)), df_plot[x_col])
    plt.grid(True, linestyle='--', alpha=0.7, axis='x')
    plt.tight_layout()

    return save_plot_to_image()

async def generate_bar_grouped(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """
    FUNÇÃO REFATORADA: Gera gráfico de barras agrupadas com fallbacks inteligentes
    """
    logging.info(f"[GRAPH_GENERATION] 🎯 Gerando barras agrupadas REFATORADO. Colunas: {df.columns.tolist()}")

    if len(df.columns) < 2:
        logging.warning("[GRAPH_GENERATION] ❌ Dados insuficientes para gráfico agrupado")
        return None

    # Analisar estrutura dos dados
    structure = analyze_dataframe_structure(df)
    numeric_cols = structure['numeric_cols']
    categorical_cols = structure['categorical_cols']

    logging.info(f"[GRAPH_GENERATION] 📊 Estrutura: {len(numeric_cols)} numéricas, {len(categorical_cols)} categóricas")

    if not numeric_cols:
        logging.warning("[GRAPH_GENERATION] ❌ Nenhuma coluna numérica encontrada")
        return await generate_bar_vertical(df, title, colors)

    # DECISÃO INTELIGENTE baseada na estrutura dos dados
    if len(numeric_cols) >= 2:
        # CENÁRIO 1: Múltiplas numéricas - gráfico agrupado tradicional
        return await _generate_multi_numeric_grouped(df, title, colors, categorical_cols[0], numeric_cols)

    elif len(numeric_cols) == 1 and len(categorical_cols) >= 2:
        # CENÁRIO 2: 1 numérica + múltiplas categóricas - agrupamento por cor
        return await _generate_color_grouped_bars(df, title, colors, categorical_cols, numeric_cols[0])

    elif len(numeric_cols) == 1 and len(categorical_cols) == 1:
        # CENÁRIO 3: Dados simples - fallback inteligente para barras verticais
        logging.info("[GRAPH_GENERATION] ⚠️ Dados simples, usando barras verticais")
        return await generate_bar_vertical(df, title, colors)

    else:
        # CENÁRIO 4: Estrutura inadequada
        logging.warning("[GRAPH_GENERATION] ❌ Estrutura de dados inadequada para agrupamento")
        return await generate_bar_vertical(df, title, colors)

async def _generate_multi_numeric_grouped(df: pd.DataFrame, title: str, colors, x_col: str, y_cols: list) -> Optional[Image.Image]:
    """
    Gera gráfico agrupado com múltiplas colunas numéricas (cenário tradicional)
    """
    logging.info(f"[GRAPH_GENERATION] 📊 Múltiplas numéricas: {x_col} + {y_cols}")

    # Converter colunas numéricas se necessário
    for col in y_cols:
        if df[col].dtype == 'object':
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

    # Remover linhas com valores NaN
    df_clean = df.dropna(subset=y_cols)

    if df_clean.empty:
        logging.error("[GRAPH_GENERATION] ❌ Todos os valores são NaN após conversão")
        return None

    # Verificar diferença de escala entre colunas
    col_ranges = {col: df_clean[col].max() - df_clean[col].min() for col in y_cols}
    max_range = max(col_ranges.values())
    min_range = min(col_ranges.values())

    if max_range > 0 and min_range > 0 and (max_range / min_range) > 100:
        # Escalas muito diferentes - usar eixos duplos
        logging.info("[GRAPH_GENERATION] 📊 Escalas diferentes, usando eixos duplos")
        return await _generate_dual_axis_chart(df_clean, title, colors, x_col, y_cols[0], y_cols[1])

    # Gráfico agrupado normal
    x_pos = np.arange(len(df_clean))
    width = 0.8 / len(y_cols)

    fig, ax = plt.subplots(figsize=(14, 8))

    for i, col in enumerate(y_cols):
        offset = width * i - width * (len(y_cols) - 1) / 2
        bars = ax.bar(x_pos + offset, df_clean[col], width, label=col,
                     color=colors[i % len(colors)], alpha=0.8)

        # Adicionar valores nas barras
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + height * 0.02,
                       f'{height:.0f}', ha='center', fontsize=8)

    ax.set_xlabel(x_col)
    ax.set_ylabel('Valores')
    ax.set_title(title or f"Comparação de {', '.join(y_cols)} por {x_col}")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(df_clean[x_col], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.7, axis='y')
    plt.tight_layout()

    logging.info(f"[GRAPH_GENERATION] ✅ Gráfico agrupado tradicional criado: {len(y_cols)} métricas")
    return save_plot_to_image()

async def _generate_color_grouped_bars(df: pd.DataFrame, title: str, colors, categorical_cols: list, y_col: str) -> Optional[Image.Image]:
    """
    Gera gráfico agrupado por cor usando múltiplas categóricas (CENÁRIO CRÍTICO)
    """
    x_col = categorical_cols[0]
    group_col = categorical_cols[1] if len(categorical_cols) > 1 else None

    logging.info(f"[GRAPH_GENERATION] 🎨 Agrupamento por cor: {x_col} (X) + {y_col} (Y) + {group_col} (cor)")

    if not group_col:
        logging.warning("[GRAPH_GENERATION] ⚠️ Sem coluna para agrupamento, usando gráfico simples")
        return await generate_bar_vertical(df[[x_col, y_col]], title, colors)

    # Converter coluna numérica se necessário
    if df[y_col].dtype == 'object':
        df[y_col] = pd.to_numeric(df[y_col].astype(str).str.replace(',', '.'), errors='coerce')

    # Remover linhas com valores NaN
    df_clean = df.dropna(subset=[y_col])

    if df_clean.empty:
        logging.error("[GRAPH_GENERATION] ❌ Todos os valores são NaN após conversão")
        return None

    # Obter categorias únicas
    unique_groups = df_clean[group_col].unique()
    unique_x = df_clean[x_col].unique()

    logging.info(f"[GRAPH_GENERATION] 🎯 Grupos: {unique_groups} | X: {len(unique_x)} categorias")

    # Configurar gráfico
    x_pos = np.arange(len(unique_x))
    width = 0.8 / len(unique_groups)

    fig, ax = plt.subplots(figsize=(14, 8))

    # Criar barras para cada grupo
    for i, group in enumerate(unique_groups):
        group_data = df_clean[df_clean[group_col] == group]

        # Criar array de valores para cada posição X
        values = []
        for x_val in unique_x:
            matching_rows = group_data[group_data[x_col] == x_val]
            if not matching_rows.empty:
                values.append(matching_rows[y_col].iloc[0])
            else:
                values.append(0)

        # Calcular posição das barras
        offset = width * i - width * (len(unique_groups) - 1) / 2
        bars = ax.bar(x_pos + offset, values, width, label=f"{group_col}: {group}",
                     color=colors[i % len(colors)], alpha=0.8)

        # Adicionar valores nas barras
        for bar, value in zip(bars, values):
            if value > 0:
                ax.text(bar.get_x() + bar.get_width()/2., value + value * 0.02,
                       f'{value:.0f}', ha='center', fontsize=8)

    # Configurações do gráfico
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title or f"{y_col} por {x_col} (agrupado por {group_col})")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(unique_x, rotation=45, ha='right')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, linestyle='--', alpha=0.7, axis='y')
    plt.tight_layout()

    logging.info(f"[GRAPH_GENERATION] ✅ Gráfico agrupado por cor criado: {len(unique_groups)} grupos")
    return save_plot_to_image()

async def _generate_dual_axis_chart(df: pd.DataFrame, title: str, colors, x_col: str, y1_col: str, y2_col: str) -> Optional[Image.Image]:
    """
    Gera gráfico com eixos duplos para métricas com escalas diferentes
    """
    logging.info(f"[GRAPH_GENERATION] 📊 Eixos duplos: {y1_col} (esq) + {y2_col} (dir)")

    fig, ax1 = plt.subplots(figsize=(14, 8))

    # Primeiro eixo Y (esquerda)
    x_pos = np.arange(len(df))
    width = 0.35

    bars1 = ax1.bar(x_pos - width/2, df[y1_col], width, label=y1_col,
                    color=colors[0], alpha=0.8)
    ax1.set_xlabel(x_col)
    ax1.set_ylabel(y1_col, color=colors[0])
    ax1.tick_params(axis='y', labelcolor=colors[0])

    # Segundo eixo Y (direita)
    ax2 = ax1.twinx()
    bars2 = ax2.bar(x_pos + width/2, df[y2_col], width, label=y2_col,
                    color=colors[1], alpha=0.8)
    ax2.set_ylabel(y2_col, color=colors[1])
    ax2.tick_params(axis='y', labelcolor=colors[1])

    # Configurações comuns
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(df[x_col], rotation=45, ha='right')
    ax1.grid(True, linestyle='--', alpha=0.7, axis='y')

    # Adicionar valores nas barras
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., height + height * 0.02,
                    f'{height:.0f}', ha='center', fontsize=8)

    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., height + height * 0.02,
                    f'{height:.0f}', ha='center', fontsize=8)

    plt.title(title or f"{y1_col} e {y2_col} por {x_col}")
    plt.tight_layout()

    logging.info(f"[GRAPH_GENERATION] ✅ Gráfico com eixos duplos criado: {y1_col} + {y2_col}")
    return save_plot_to_image()

# Função removida - substituída pela nova lógica unificada

# Função removida - substituída pela nova lógica unificada em _generate_color_grouped_bars()

async def generate_bar_stacked(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """Gera gráfico de barras empilhadas"""
    if len(df.columns) < 3:
        return await generate_bar_vertical(df, title, colors)

    x_col = df.columns[0]
    y_cols = [col for col in df.columns[1:] if pd.api.types.is_numeric_dtype(df[col])]

    if not y_cols:
        return await generate_bar_vertical(df, title, colors)

    fig, ax = plt.subplots(figsize=(12, 8))
    bottom = np.zeros(len(df))

    for i, col in enumerate(y_cols):
        bars = ax.bar(range(len(df)), df[col], bottom=bottom, label=col, color=colors[i % len(colors)])

        # Adicionar valores nas barras
        for j, bar in enumerate(bars):
            height = bar.get_height()
            if isinstance(height, (int, float)) and height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., bottom[j] + height/2,
                        f'{height:.2f}', ha='center', va='center', fontsize=8, color='white')

        bottom += df[col].fillna(0)

    ax.set_xlabel(x_col)
    ax.set_ylabel('Valores')
    ax.set_title(title or f"Distribuição por {x_col}")
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df[x_col], rotation=45, ha='right')
    ax.legend()
    plt.tight_layout()

    return save_plot_to_image()

async def generate_pie(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """Gera gráfico de pizza"""
    if len(df.columns) < 2:
        return None

    label_col, value_col = df.columns[0], df.columns[1]

    # Preparar dados numéricos - converter strings com vírgula para float
    df_plot = df.copy()
    try:
        if df_plot[value_col].dtype == 'object':
            # Converte strings para números, tratando vírgulas como separador decimal
            df_plot[value_col] = pd.to_numeric(df_plot[value_col].astype(str).str.replace(',', '.'), errors='coerce')

        # Remove linhas com valores não numéricos, negativos ou zero
        df_plot = df_plot.dropna(subset=[value_col])
        df_plot = df_plot[df_plot[value_col] > 0]

        if df_plot.empty:
            logging.error(f"[GRAPH_GENERATION] Nenhum valor numérico positivo encontrado na coluna {value_col}")
            return await generate_bar_vertical(df, title, colors)

    except Exception as e:
        logging.error(f"[GRAPH_GENERATION] Erro ao converter dados para numérico: {e}")
        return await generate_bar_vertical(df, title, colors)

    plt.figure(figsize=(10, 10))

    # Calcular percentuais para os rótulos
    total = df_plot[value_col].sum()
    labels = [f'{label} ({val:,.0f}, {val/total:.1%})' for label, val in zip(df_plot[label_col], df_plot[value_col])]

    plt.pie(df_plot[value_col], labels=labels, autopct='%1.1f%%',
            startangle=90, shadow=False, colors=colors[:len(df_plot)])

    plt.axis('equal')
    plt.title(title or f"Distribuição de {value_col} por {label_col}")
    plt.tight_layout()

    return save_plot_to_image()

async def generate_donut(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """Gera gráfico de donut"""
    if len(df.columns) < 2:
        return None

    label_col, value_col = df.columns[0], df.columns[1]

    # Preparar dados numéricos - converter strings com vírgula para float
    df_plot = df.copy()
    try:
        if df_plot[value_col].dtype == 'object':
            # Converte strings para números, tratando vírgulas como separador decimal
            df_plot[value_col] = pd.to_numeric(df_plot[value_col].astype(str).str.replace(',', '.'), errors='coerce')

        # Remove linhas com valores não numéricos, negativos ou zero
        df_plot = df_plot.dropna(subset=[value_col])
        df_plot = df_plot[df_plot[value_col] > 0]

        if df_plot.empty:
            logging.error(f"[GRAPH_GENERATION] Nenhum valor numérico positivo encontrado na coluna {value_col}")
            return await generate_bar_vertical(df, title, colors)

    except Exception as e:
        logging.error(f"[GRAPH_GENERATION] Erro ao converter dados para numérico: {e}")
        return await generate_bar_vertical(df, title, colors)

    plt.figure(figsize=(10, 10))

    # Calcular percentuais para os rótulos
    total = df_plot[value_col].sum()
    labels = [f'{label} ({val:,.0f}, {val/total:.1%})' for label, val in zip(df_plot[label_col], df_plot[value_col])]

    # Criar gráfico de donut (pizza com círculo central)
    plt.pie(df_plot[value_col], labels=labels, autopct='%1.1f%%',
            startangle=90, shadow=False, colors=colors[:len(df_plot)],
            wedgeprops=dict(width=0.5))  # Largura do anel

    plt.axis('equal')
    plt.title(title or f"Distribuição de {value_col} por {label_col}")
    plt.tight_layout()

    return save_plot_to_image()

async def generate_pie_multiple(df: pd.DataFrame, title: str, colors) -> Optional[Image.Image]:
    """Gera múltiplos gráficos de pizza"""
    if len(df.columns) < 3:
        return await generate_pie(df, title, colors)

    cat1, cat2, val_col = df.columns[0], df.columns[1], df.columns[2]

    # Verificar se o valor é numérico
    if not pd.api.types.is_numeric_dtype(df[val_col]):
        return await generate_bar_grouped(df, title, colors)

    # Agrupar dados
    grouped = df.groupby([cat1, cat2])[val_col].sum().unstack().fillna(0)

    # Determinar layout da grade
    n_groups = len(grouped)
    if n_groups == 0:
        return None

    cols = min(3, n_groups)  # Máximo 3 colunas
    rows = (n_groups + cols - 1) // cols  # Arredondar para cima

    # Criar subplots
    fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
    if rows == 1 and cols == 1:
        axes = np.array([axes])  # Garantir que axes seja um array
    axes = axes.flatten()

    # Plotar cada pizza
    for i, (group_name, group_data) in enumerate(grouped.iterrows()):
        if i < len(axes):
            # Remover valores zero
            data = group_data[group_data > 0]

            if not data.empty:
                # Calcular percentuais
                total = data.sum()

                # Criar rótulos com valores e percentuais
                labels = [f'{idx} ({val:.2f}, {val/total:.1%})' for idx, val in data.items()]

                # Plotar pizza
                axes[i].pie(data, labels=labels, autopct='%1.1f%%',
                           startangle=90, colors=colors[:len(data)])
                axes[i].set_title(f"{group_name}")
                axes[i].axis('equal')

    # Esconder eixos não utilizados
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')

    plt.suptitle(title or f"Distribuição de {val_col} por {cat2} para cada {cat1}", fontsize=16)
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)

    return save_plot_to_image()
