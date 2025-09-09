"""
AgentGraph - Aplicação principal com interface Gradio e LangGraph
Integrado com Celery + Redis + Flower para processamento assíncrono
"""
import asyncio
import logging
import gradio as gr
import tempfile
import os
import subprocess
import threading
import time
import atexit
from typing import List, Tuple, Optional, Dict
from PIL import Image

from agentgraph.graphs.main_graph import initialize_graph, get_graph_manager
from agentgraph.utils.config import (
    AVAILABLE_MODELS,
    REFINEMENT_MODELS,
    DEFAULT_MODEL,
    DEFAULT_TOP_K,
    GRADIO_SHARE,
    GRADIO_PORT,
    validate_config,
    is_langsmith_enabled,
    LANGSMITH_PROJECT,
    CELERY_ENABLED,
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_WORKER_CONCURRENCY,
    CELERY_WORKER_COUNT,
    FLOWER_PORT,
    is_docker_environment,
    get_environment_info,
    get_redis_connection_url,
    REDIS_HOST,
    REDIS_PORT
)
from agentgraph.utils.object_manager import get_object_manager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Variáveis globais
graph_manager = None
show_history_flag = False
connection_ready = False  # Controla se a conexão está pronta para uso
chat_blocked = False      # Controla se o chat está bloqueado durante carregamento

# Variáveis globais do Celery
celery_worker_process = None
flower_process = None
redis_process = None
celery_enabled = False
redis_available = False

# Variável global para armazenar a última SQL query (para criação de tabelas)
_last_sql_query = None

def kill_redis_processes():
    """Finaliza processos Redis existentes"""
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(
                ["taskkill", "/F", "/IM", "redis-server.exe"],
                capture_output=True,
                check=False  # Não falha se processo não existir
            )
            logging.info("[REDIS] Processos Redis existentes finalizados")
    except Exception as e:
        logging.warning(f"[REDIS] Erro ao finalizar processos Redis: {e}")

def start_local_redis():
    """Inicia Redis local da pasta do projeto"""
    global redis_process

    try:
        # Finaliza processos Redis existentes primeiro
        kill_redis_processes()

        # Procura pelo executável do Redis na pasta do projeto (caminhos corretos)
        redis_paths = [
            ("redis-windows/redis-server.exe", "redis-windows/redis.windows.conf"),
            ("redis-windows\\redis-server.exe", "redis-windows\\redis.windows.conf"),  # Windows paths
            ("redis-server.exe", "redis.windows.conf"),
            ("Redis/redis-server.exe", "Redis/redis.windows.conf")
        ]

        redis_exe = None
        redis_conf = None

        # Debug: Verifica se pasta redis-windows existe
        if os.path.exists("redis-windows"):
            logging.info("[REDIS] Pasta redis-windows encontrada")
        else:
            logging.warning("[REDIS] Pasta redis-windows NÃO encontrada")

        for exe_path, conf_path in redis_paths:
            logging.info(f"[REDIS] Testando: {exe_path}")
            if os.path.exists(exe_path):
                redis_exe = exe_path
                # Verifica se arquivo de configuração existe
                if os.path.exists(conf_path):
                    redis_conf = conf_path
                    logging.info(f"[REDIS] Encontrado arquivo de configuração: {redis_conf}")
                else:
                    logging.warning(f"[REDIS] Arquivo de configuração não encontrado: {conf_path}")
                break

        if not redis_exe:
            logging.warning("[REDIS] Executável redis-server.exe não encontrado na pasta do projeto")
            return False

        # Converte para caminhos absolutos (como no teste que funcionou)
        abs_exe_path = os.path.abspath(redis_exe)
        abs_conf_path = os.path.abspath(redis_conf) if redis_conf else None

        logging.info(f"[REDIS] Caminho absoluto executável: {abs_exe_path}")
        if abs_conf_path:
            logging.info(f"[REDIS] Caminho absoluto configuração: {abs_conf_path}")

        # Monta comando com caminhos absolutos
        if abs_conf_path and os.path.exists(abs_conf_path):
            cmd = [abs_exe_path, abs_conf_path]
            logging.info(f"[REDIS] Iniciando Redis local com configuração: {abs_exe_path} {abs_conf_path}")
        else:
            cmd = [abs_exe_path]
            logging.info(f"[REDIS] Iniciando Redis local sem configuração: {abs_exe_path}")

        # Inicia Redis em background
        redis_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
            cwd=os.getcwd()  # Usa diretório atual como no teste
        )

        # Aguarda um pouco para Redis inicializar
        time.sleep(3)

        if redis_process.poll() is None:
            logging.info("[REDIS] Redis local iniciado com sucesso")
            return True
        else:
            # Captura saída para debug
            try:
                stdout, stderr = redis_process.communicate(timeout=5)
                logging.error("[REDIS] Falha ao iniciar Redis local")
                logging.error(f"[REDIS] STDOUT: {stdout.decode().strip()}")
                logging.error(f"[REDIS] STDERR: {stderr.decode().strip()}")
                logging.error(f"[REDIS] Return code: {redis_process.returncode}")
            except:
                logging.error("[REDIS] Falha ao iniciar Redis local (timeout na comunicação)")
            return False

    except Exception as e:
        logging.error(f"[REDIS] Erro ao iniciar Redis local: {e}")
        logging.error(f"[REDIS] Comando tentado: {' '.join(cmd) if 'cmd' in locals() else 'N/A'}")
        return False

def check_redis_availability():
    """Verifica se Redis está disponível baseado no ambiente"""
    global redis_available

    try:
        import redis

        # Usa configurações dinâmicas baseadas no ambiente
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        redis_client.ping()
        redis_available = True

        env_info = get_environment_info()
        logging.info(f"[REDIS] Redis disponível em {env_info['environment']}: {REDIS_HOST}:{REDIS_PORT}")
        return True
    except Exception as e:
        redis_available = False
        env_info = get_environment_info()
        logging.warning(f"[REDIS] Redis não disponível em {env_info['environment']}: {e}")
        return False

def start_celery_worker():
    """Inicia worker(s) do Celery baseado no ambiente"""
    global celery_worker_process

    try:
        import sys
        env_info = get_environment_info()

        # Nome único do worker baseado no timestamp (usado em ambos os ambientes)
        import time
        worker_name = f"worker-{int(time.time())}@agentgraph"

        if is_docker_environment():
            # Configuração para Docker - múltiplos workers
            logging.info(f"[CELERY] Iniciando {CELERY_WORKER_COUNT} workers Docker com {CELERY_WORKER_CONCURRENCY} concurrency cada")

            # Pool baseado na variável de ambiente ou padrão
            pool_type = os.getenv("CELERY_POOL", "prefork")

            # Inicia múltiplos workers
            celery_worker_processes = []

            for worker_id in range(CELERY_WORKER_COUNT):
                worker_name_multi = f"worker-{worker_id}-{int(time.time())}@agentgraph"

                cmd = [
                    sys.executable, "-m", "celery",
                    "-A", "tasks",
                    "worker",
                    f"--concurrency={CELERY_WORKER_CONCURRENCY}",
                    f"--hostname={worker_name_multi}",
                    "--loglevel=INFO",
                    f"--pool={pool_type}",  # Pool dinâmico
                    "--without-gossip",  # Desabilita gossip
                    "--without-mingle",  # Desabilita mingle
                    "--events"  # Habilita events explicitamente
                ]

                logging.info(f"[CELERY] Iniciando worker {worker_id+1}/{CELERY_WORKER_COUNT}: {worker_name_multi}")

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd(),
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                celery_worker_processes.append(process)

            # Usa o primeiro processo para logs (compatibilidade)
            celery_worker_process = celery_worker_processes[0] if celery_worker_processes else None

            logging.info(f"[CELERY] Pool configurado: {pool_type}")
            logging.info(f"[CELERY] Total: {CELERY_WORKER_COUNT} workers x {CELERY_WORKER_CONCURRENCY} concurrency = {CELERY_WORKER_COUNT * CELERY_WORKER_CONCURRENCY} processos")

        else:
            # Configuração para Windows - single worker com solo pool
            cmd = [
                sys.executable, "-m", "celery",
                "-A", "tasks",
                "worker",
                f"--concurrency={CELERY_WORKER_CONCURRENCY}",
                f"--hostname={worker_name}",  # Nome único também no Windows
                "--loglevel=INFO",
                "--pool=solo"  # Single-thread para Windows
            ]

            logging.info(f"[CELERY] Iniciando worker único para Windows: {' '.join(cmd)}")

            celery_worker_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd(),
                text=True,
                bufsize=1,
                universal_newlines=True
            )

        # Aguarda um pouco para verificar se iniciou
        time.sleep(5)

        if celery_worker_process.poll() is None:
            logging.info("[CELERY] ✅ Worker Celery iniciado com sucesso")

            # Lê algumas linhas de output para verificar se está funcionando
            try:
                import threading
                def read_worker_output():
                    for line in iter(celery_worker_process.stdout.readline, ''):
                        if line.strip():
                            logging.info(f"[CELERY_WORKER] {line.strip()}")

                # Inicia thread para ler output do worker
                worker_thread = threading.Thread(target=read_worker_output, daemon=True)
                worker_thread.start()

            except Exception as e:
                logging.warning(f"[CELERY] Não foi possível ler output do worker: {e}")

            return True
        else:
            # Worker falhou, captura erro
            try:
                stdout, stderr = celery_worker_process.communicate(timeout=5)
                logging.error("[CELERY] ❌ Falha ao iniciar worker Celery")
                logging.error(f"[CELERY] STDOUT: {stdout}")
                logging.error(f"[CELERY] STDERR: {stderr}")
            except:
                logging.error("[CELERY] ❌ Worker falhou e não foi possível capturar erro")
            return False

    except Exception as e:
        logging.error(f"[CELERY] Erro ao iniciar worker: {e}")
        logging.error(f"[CELERY] Comando tentado: {' '.join(cmd) if 'cmd' in locals() else 'N/A'}")
        logging.error(f"[CELERY] Diretório atual: {os.getcwd()}")

        # Tenta verificar se celery está instalado
        try:
            import celery
            logging.info(f"[CELERY] Celery instalado na versão: {celery.__version__}")
        except ImportError:
            logging.error("[CELERY] Celery não está instalado!")

        return False

def start_flower_monitoring():
    """Inicia Flower para monitoramento baseado no ambiente"""
    global flower_process

    try:
        import sys
        env_info = get_environment_info()

        cmd = [
            sys.executable, "-m", "celery",
            "-A", "tasks",
            "flower",
            f"--port={FLOWER_PORT}"
        ]

        if is_docker_environment():
            # No Docker, adiciona configurações específicas
            cmd.extend([
                "--broker=redis://redis:6379/0",
                "--address=0.0.0.0",  # Permite acesso externo no Docker
                "--basic_auth=admin:admin",  # Autenticação básica
                "--auto_refresh=False"  # Desabilita auto-refresh para reduzir overhead
            ])
            logging.info(f"[FLOWER] Iniciando Flower para Docker: {' '.join(cmd)}")

            flower_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd(),
                text=True,
                bufsize=1,
                universal_newlines=True
            )
        else:
            # No Windows, usa console separado
            logging.info(f"[FLOWER] Iniciando Flower para Windows: {' '.join(cmd)}")

            flower_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
                cwd=os.getcwd()
            )

        # Aguarda um pouco para verificar se iniciou
        time.sleep(3)

        if flower_process.poll() is None:
            logging.info(f"[FLOWER] Flower iniciado em http://localhost:{FLOWER_PORT}")
            return True
        else:
            logging.error("[FLOWER] Falha ao iniciar Flower")
            return False

    except Exception as e:
        logging.error(f"[FLOWER] Erro ao iniciar Flower: {e}")
        return False

def initialize_celery_system():
    """Inicializa sistema Celery completo baseado no ambiente"""
    global celery_enabled

    # Verifica se Celery está habilitado na configuração
    if not CELERY_ENABLED:
        logging.info("[CELERY_INIT] Celery desabilitado na configuração")
        celery_enabled = False
        return False

    env_info = get_environment_info()
    logging.info(f"[CELERY_INIT] Inicializando sistema Celery para {env_info['environment']}...")

    # 1. Verificar Redis baseado no ambiente
    if not check_redis_availability():
        if is_docker_environment():
            # No Docker, Redis deve estar disponível como serviço
            logging.error("[CELERY_INIT] Redis não disponível no Docker - verifique docker-compose.yml")
            celery_enabled = False
            return False
        else:
            # No Windows, tenta iniciar Redis local
            logging.info("[CELERY_INIT] Redis não disponível, tentando iniciar Redis local...")

            if start_local_redis():
                # Aguarda Redis inicializar e testa novamente
                time.sleep(2)
                if not check_redis_availability():
                    logging.warning("[CELERY_INIT] Redis local iniciado mas não conecta - Celery desabilitado")
                    celery_enabled = False
                    return False
            else:
                logging.warning("[CELERY_INIT] Não foi possível iniciar Redis local - Celery desabilitado")
                celery_enabled = False
                return False

    # 2. Iniciar Worker
    if not start_celery_worker():
        logging.warning("[CELERY_INIT] Worker não iniciou - Celery desabilitado")
        celery_enabled = False
        return False

    # 3. Iniciar Flower
    if not start_flower_monitoring():
        logging.warning("[CELERY_INIT] Flower não iniciou - Continuando sem monitoramento")
        # Flower é opcional, não desabilita Celery

    # Verificar se worker está realmente ativo
    time.sleep(3)  # Aguarda worker inicializar
    if verify_worker_active():
        logging.info("[CELERY_INIT] ✅ Worker verificado e ativo!")
    else:
        logging.warning("[CELERY_INIT] ⚠️ Worker pode não estar ativo")

    celery_enabled = True
    logging.info("[CELERY_INIT] Sistema Celery inicializado com sucesso!")
    return True

def verify_worker_active():
    """Verifica se worker Celery está ativo"""
    try:
        from celery import Celery

        # Conecta ao Celery
        celery_app = Celery(
            'test',
            broker=CELERY_BROKER_URL,
            backend=CELERY_RESULT_BACKEND
        )

        # Verifica workers ativos
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()

        if active_workers:
            worker_names = list(active_workers.keys())
            logging.info(f"[CELERY_VERIFY] ✅ Workers ativos: {worker_names}")
            return True
        else:
            logging.warning("[CELERY_VERIFY] ❌ Nenhum worker ativo encontrado")
            return False

    except Exception as e:
        logging.error(f"[CELERY_VERIFY] Erro ao verificar workers: {e}")
        return False

def cleanup_celery_processes():
    """Limpa processos do Celery ao encerrar"""
    global celery_worker_process, flower_process, redis_process

    logging.info("[CLEANUP] Encerrando processos Celery...")

    if celery_worker_process:
        try:
            celery_worker_process.terminate()
            celery_worker_process.wait(timeout=10)
            logging.info("[CLEANUP] Worker Celery encerrado")
        except Exception as e:
            logging.error(f"[CLEANUP] Erro ao encerrar worker: {e}")
            try:
                celery_worker_process.kill()
            except:
                pass

    if flower_process:
        try:
            flower_process.terminate()
            flower_process.wait(timeout=5)
            logging.info("[CLEANUP] Flower encerrado")
        except Exception as e:
            logging.error(f"[CLEANUP] Erro ao encerrar Flower: {e}")
            try:
                flower_process.kill()
            except:
                pass

    if redis_process:
        try:
            redis_process.terminate()
            redis_process.wait(timeout=5)
            logging.info("[CLEANUP] Redis local encerrado")
        except Exception as e:
            logging.error(f"[CLEANUP] Erro ao encerrar Redis: {e}")
            try:
                redis_process.kill()
            except:
                pass

    # Força finalização de todos os processos Redis
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(
                ["taskkill", "/F", "/IM", "redis-server.exe"],
                capture_output=True,
                check=False
            )
            logging.info("[CLEANUP] Processos Redis finalizados via taskkill")
    except Exception as e:
        logging.warning(f"[CLEANUP] Erro ao finalizar Redis via taskkill: {e}")

async def initialize_app():
    """Inicializa a aplicação"""
    global graph_manager, connection_ready

    try:
        # Valida configurações
        validate_config()

        # Inicializa sistema Celery (opcional)
        initialize_celery_system()

        # Debug: Status final do Celery
        logging.info(f"[INIT] Status final celery_enabled: {celery_enabled}")
        logging.info(f"[INIT] CELERY_ENABLED config: {CELERY_ENABLED}")

        # Inicializa o grafo
        graph_manager = await initialize_graph()

        # Inicializa como conectado (base padrão já carregada)
        connection_ready = True

        # Informa sobre o status do LangSmith
        if is_langsmith_enabled():
            logging.info(f"✅ LangSmith habilitado - Projeto: '{LANGSMITH_PROJECT}'")
            logging.info("🔍 Traces serão enviados para LangSmith automaticamente")
        else:
            logging.info("ℹ️ LangSmith não configurado - Executando sem observabilidade")

        # Registra função de cleanup para encerramento
        atexit.register(cleanup_celery_processes)

        logging.info("Aplicação inicializada com sucesso")
        return True

    except Exception as e:
        logging.error(f"Erro ao inicializar aplicação: {e}")
        return False

def run_async(coro):
    """Executa corrotina de forma síncrona"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

def chatbot_response(user_input: str, selected_model: str, advanced_mode: bool = False, processing_enabled: bool = False, processing_model: str = "GPT-4o-mini", connection_type: str = "csv", postgresql_config: Optional[Dict] = None, selected_table: str = None, single_table_mode: bool = False, top_k: int = 10) -> Tuple[str, Optional[str]]:
    """
    Processa resposta do chatbot usando LangGraph

    Args:
        user_input: Entrada do usuário
        selected_model: Modelo LLM selecionado
        advanced_mode: Se deve usar refinamento avançado
        processing_enabled: Se o Processing Agent está habilitado
        processing_model: Modelo para o Processing Agent
        connection_type: Tipo de conexão ("csv" ou "postgresql")
        postgresql_config: Configuração postgresql (se aplicável)
        selected_table: Tabela selecionada (para postgresql)
        single_table_mode: Se deve usar apenas uma tabela (postgresql)
        top_k: Número máximo de resultados (LIMIT) para queries SQL

    Returns:
        Tupla com (resposta_texto, caminho_imagem_grafico)
    """
    global graph_manager

    if not graph_manager:
        return "❌ Sistema não inicializado. Tente recarregar a página.", None

    try:
        # Log simples
        logging.info(f"[CHATBOT] Usando Celery: {celery_enabled}")
        logging.info(f"[CHATBOT] 📊 TOP_K para LangGraph: {top_k}")

        # Processa query através do LangGraph
        result = run_async(graph_manager.process_query(
            user_input=user_input,
            selected_model=selected_model,
            advanced_mode=advanced_mode,
            processing_enabled=processing_enabled,
            processing_model=processing_model,
            connection_type=connection_type,
            postgresql_config=postgresql_config,
            selected_table=selected_table,
            single_table_mode=single_table_mode,
            top_k=top_k,
            use_celery=celery_enabled
        ))

        response_text = result.get("response", "Erro ao processar resposta")
        graph_image_path = None
        show_create_table_btn = False

        # Captura SQL query para uso posterior na criação de tabelas
        sql_query = result.get("sql_query_extracted") or result.get("sql_query")
        if sql_query and connection_type == "postgresql":
            # Armazena a SQL query globalmente para uso no modal
            global _last_sql_query
            _last_sql_query = sql_query
            show_create_table_btn = True
            logging.info(f"[RESPOND] ✅ SQL query capturada para criação de tabela: {sql_query[:50]}...")
            logging.info(f"[RESPOND] ✅ Botão de criar tabela será mostrado")
        else:
            logging.info(f"[RESPOND] ❌ Botão de criar tabela não será mostrado (SQL: {bool(sql_query)}, Conn: {connection_type})")

        # Verifica se foi gerado um gráfico
        if result.get("graph_generated", False) and result.get("graph_image_id"):
            graph_image_path = save_graph_image_to_temp(result["graph_image_id"])

            # Adiciona informação sobre o gráfico na resposta
            if graph_image_path:
                graph_type = result.get("graph_type", "gráfico")
                response_text += f"\n\n📊 **Gráfico gerado**: {graph_type.replace('_', ' ').title()}"

        return response_text, graph_image_path, gr.update(visible=show_create_table_btn)

    except Exception as e:
        error_msg = f"Erro no chatbot: {e}"
        logging.error(error_msg)
        logging.error(f"Detalhes do erro: {type(e).__name__}: {str(e)}")
        return error_msg, None

def save_graph_image_to_temp(graph_image_id: str) -> Optional[str]:
    """
    Salva imagem do gráfico em arquivo temporário para exibição no Gradio

    Args:
        graph_image_id: ID da imagem no ObjectManager

    Returns:
        Caminho do arquivo temporário ou None se falhar
    """
    try:
        obj_manager = get_object_manager()
        graph_image = obj_manager.get_object(graph_image_id)

        if graph_image and isinstance(graph_image, Image.Image):
            # Cria arquivo temporário
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            graph_image.save(temp_file.name, format='PNG')
            temp_file.close()

            logging.info(f"[GRADIO] Gráfico salvo em: {temp_file.name}")
            return temp_file.name

    except Exception as e:
        logging.error(f"[GRADIO] Erro ao salvar gráfico: {e}")

    return None

def handle_csv_upload(file) -> str:
    """
    Processa upload de arquivo csv

    Args:
        file: Arquivo enviado pelo Gradio

    Returns:
        Mensagem de feedback
    """
    global graph_manager

    if not graph_manager:
        return "❌ Sistema não inicializado."

    if not file:
        return "❌ Nenhum arquivo selecionado."

    try:
        # Log detalhado do arquivo recebido
        logging.info(f"[UPLOAD] Arquivo recebido: {file}")
        logging.info(f"[UPLOAD] Nome do arquivo: {file.name}")
        logging.info(f"[UPLOAD] Tipo do arquivo: {type(file)}")

        # Verifica se o arquivo existe
        import os
        if not os.path.exists(file.name):
            return f"❌ Arquivo não encontrado: {file.name}"

        # Verifica se é um arquivo csv
        if not file.name.lower().endswith('.csv'):
            return "❌ Por favor, selecione um arquivo csv válido."

        # Verifica o tamanho do arquivo
        file_size = os.path.getsize(file.name)
        file_size_mb = file_size / (1024 * 1024)
        file_size_gb = file_size / (1024 * 1024 * 1024)

        if file_size_gb >= 1:
            size_str = f"{file_size_gb:.2f} GB"
        else:
            size_str = f"{file_size_mb:.2f} MB"

        logging.info(f"[UPLOAD] Tamanho do arquivo: {file_size} bytes ({size_str})")

        if file_size == 0:
            return "❌ O arquivo está vazio."

        if file_size > 5 * 1024 * 1024 * 1024:  # 5GB
            return "❌ Arquivo muito grande. Máximo permitido: 5GB."

        # Aviso para arquivos grandes
        if file_size_mb > 100:
            logging.info(f"[UPLOAD] Arquivo grande detectado ({size_str}). Processamento pode demorar...")
            return f"⏳ Processando arquivo grande ({size_str}). Aguarde..."

        # Processa upload através do CustomNodeManager
        logging.info(f"[UPLOAD] Iniciando processamento do arquivo: {file.name}")
        result = run_async(graph_manager.custom_node_manager.handle_csv_upload(file.name, graph_manager.object_manager))

        # Atualiza IDs do sistema se upload foi bem-sucedido
        if result.get("success") and result.get("engine_id") and result.get("db_id"):
            graph_manager.engine_id = result["engine_id"]
            graph_manager.db_id = result["db_id"]

            # Cria novo agente SQL
            from agentgraph.agents.sql_agent import SQLAgentManager
            new_db = graph_manager.object_manager.get_database(graph_manager.db_id)
            if not new_db:
                logging.error(f"[UPLOAD] Banco de dados não encontrado com ID: {graph_manager.db_id}")
                return "❌ Erro: Banco de dados não encontrado após upload"

            top_k = graph_manager.object_manager.get_global_config('top_k', 10)
            new_sql_agent = SQLAgentManager(
                db=new_db,
                model_name="gpt-4o-mini",
                single_table_mode=False,
                selected_table=None,
                top_k=top_k
            )
            graph_manager.agent_id = graph_manager.object_manager.store_sql_agent(new_sql_agent, graph_manager.db_id)

            # Limpa cache
            cache_manager = graph_manager.object_manager.get_cache_manager(graph_manager.cache_id)
            if cache_manager:
                cache_manager.clear_cache()

            logging.info("[UPLOAD] Sistema atualizado com novo CSV")

        logging.info(f"[UPLOAD] Resultado do processamento: {result}")
        return result.get("message", "Erro no upload")

    except Exception as e:
        error_msg = f"❌ Erro ao processar upload: {e}"
        logging.error(error_msg)
        logging.error(f"[UPLOAD] Detalhes do erro: {type(e).__name__}: {str(e)}")
        import traceback
        logging.error(f"[UPLOAD] Traceback: {traceback.format_exc()}")
        return error_msg

def reset_system() -> str:
    """
    Reseta o sistema ao estado inicial
    
    Returns:
        Mensagem de feedback
    """
    global graph_manager
    
    if not graph_manager:
        return "❌ Sistema não inicializado."
    
    try:
        # Reseta sistema através do CustomNodeManager
        result = run_async(graph_manager.custom_node_manager.reset_system(
            graph_manager.engine_id,
            graph_manager.agent_id,
            graph_manager.cache_id
        ))

        # Atualiza IDs se reset foi bem-sucedido
        if result.get("success"):
            graph_manager.engine_id = result.get("engine_id", graph_manager.engine_id)
            graph_manager.agent_id = result.get("agent_id", graph_manager.agent_id)
            logging.info("[RESET] Sistema resetado com sucesso")
        
        return result.get("message", "Erro no reset")
        
    except Exception as e:
        error_msg = f"❌ Erro ao resetar sistema: {e}"
        logging.error(error_msg)
        return error_msg

def handle_postgresql_connection(host: str, port: str, database: str, username: str, password: str) -> str:
    """
    Processa conexão postgresql

    Args:
        host: Host do postgresql
        port: Porta do postgresql
        database: Nome do banco
        username: Nome de usuário
        password: Senha

    Returns:
        Mensagem de feedback
    """
    global graph_manager

    if not graph_manager:
        return "❌ Sistema não inicializado."

    try:
        # Valida campos obrigatórios
        if not all([host, port, database, username, password]):
            return "❌ Todos os campos são obrigatórios para conexão postgresql."

        # Valida porta
        try:
            port_int = int(port)
            if port_int < 1 or port_int > 65535:
                return "❌ Porta deve estar entre 1 e 65535."
        except ValueError:
            return "❌ Porta deve ser um número válido."

        # Prepara configuração postgresql
        postgresql_config = {
            "host": host.strip(),
            "port": port_int,
            "database": database.strip(),
            "username": username.strip(),
            "password": password
        }

        # Cria estado inicial para a conexão
        initial_state = {
            "user_input": "Conectar postgresql",
            "selected_model": "gpt-4o-mini",
            "advanced_mode": False,
            "processing_enabled": False,
            "processing_model": "gpt-4o-mini",
            "connection_type": "postgresql",
            "postgresql_config": postgresql_config,
            "selected_table": None,
            "single_table_mode": False
        }

        # Processa conexão através do CustomNodeManager
        logging.info(f"[POSTGRESQL] Iniciando conexão: {host}:{port}/{database}")
        result = run_async(graph_manager.custom_node_manager.handle_postgresql_connection(initial_state))

        # Atualiza sistema se conexão foi bem-sucedida
        if result.get("success"):
            graph_manager.engine_id = result.get("engine_id")
            graph_manager.db_id = result.get("db_id")

            # Cria novo agente SQL com configurações do estado
            from agentgraph.agents.sql_agent import SQLAgentManager
            new_db = graph_manager.object_manager.get_database(graph_manager.db_id)
            if not new_db:
                logging.error(f"[POSTGRESQL] Banco de dados não encontrado com ID: {graph_manager.db_id}")
                return "❌ Erro: Banco de dados não encontrado após conexão PostgreSQL"

            single_table_mode = initial_state.get("single_table_mode", False)
            selected_table = initial_state.get("selected_table")
            selected_model = initial_state.get("selected_model", "gpt-4o-mini")
            top_k = initial_state.get("top_k", 10)

            new_sql_agent = SQLAgentManager(
                db=new_db,
                model_name=selected_model,
                single_table_mode=single_table_mode,
                selected_table=selected_table,
                top_k=top_k
            )

            graph_manager.agent_id = graph_manager.object_manager.store_sql_agent(new_sql_agent, graph_manager.db_id)

            # Armazena metadados de conexão
            connection_info = result.get("connection_info", {})
            graph_manager.object_manager.store_connection_metadata(graph_manager.db_id, connection_info)

            # Limpa cache
            cache_manager = graph_manager.object_manager.get_cache_manager(graph_manager.cache_id)
            if cache_manager:
                cache_manager.clear_cache()

            logging.info("[POSTGRESQL] Sistema atualizado com nova conexão PostgreSQL")

        logging.info(f"[POSTGRESQL] Resultado da conexão: {result}")
        return result.get("message", "Erro na conexão postgresql")

    except Exception as e:
        error_msg = f"❌ Erro ao conectar postgresql: {e}"
        logging.error(error_msg)
        logging.error(f"[POSTGRESQL] Detalhes do erro: {type(e).__name__}: {str(e)}")
        return error_msg

def toggle_advanced_mode(enabled: bool) -> str:
    """
    Alterna modo avançado usando nó específico

    Args:
        enabled: Se deve habilitar modo avançado

    Returns:
        Mensagem de status
    """
    global graph_manager

    if not graph_manager:
        return "❌ Sistema não inicializado."

    return run_async(graph_manager.custom_node_manager.toggle_advanced_mode(enabled))

def toggle_history():
    """Alterna exibição do histórico usando nó específico"""
    global show_history_flag, graph_manager

    show_history_flag = not show_history_flag

    if show_history_flag and graph_manager:
        return run_async(graph_manager.custom_node_manager.get_history(graph_manager.cache_id))
    else:
        return {}

def apply_top_k(top_k_value: int) -> str:
    """
    Aplica novo valor de TOP_K e força recriação do agente SQL

    Args:
        top_k_value: Novo valor de TOP_K

    Returns:
        Mensagem de feedback
    """
    global graph_manager

    if not graph_manager:
        return "❌ Sistema não inicializado."

    try:
        # Valida o valor
        if not isinstance(top_k_value, (int, float)) or top_k_value < 1:
            return "❌ TOP_K deve ser um número maior que 0."

        top_k_value = int(top_k_value)

        if top_k_value > 10000:
            return "❌ TOP_K muito alto. Máximo permitido: 10.000."

        # Força recriação do agente SQL com novo TOP_K usando nó específico
        result = run_async(graph_manager.custom_node_manager.force_recreate_agent(
            agent_id=graph_manager.agent_id,
            top_k=top_k_value
        ))

        if result.get("success", False):
            # IMPORTANTE: Atualizar TOP_K no ObjectManager para o Celery
            if hasattr(graph_manager, 'object_manager') and graph_manager.object_manager:
                try:
                    # Atualiza configuração global do TOP_K no ObjectManager
                    graph_manager.object_manager.update_global_config('top_k', top_k_value)
                    logging.info(f"[APPLY_TOP_K] TOP_K {top_k_value} atualizado no ObjectManager para Celery")
                except Exception as e:
                    logging.warning(f"[APPLY_TOP_K] Erro ao atualizar ObjectManager: {e}")

            return f"✅ TOP_K atualizado para {top_k_value}. Agente SQL recriado e configuração salva para Celery."
        else:
            return f"❌ Erro ao aplicar TOP_K: {result.get('message', 'Erro desconhecido')}"

    except Exception as e:
        error_msg = f"❌ Erro ao aplicar TOP_K: {e}"
        logging.error(error_msg)
        return error_msg

def respond(message: str, chat_history: List[Dict[str, str]], selected_model: str, advanced_mode: bool, processing_enabled: bool = False, processing_model: str = "GPT-4o-mini", connection_type: str = "csv", postgresql_config: Optional[Dict] = None, selected_table: str = None, single_table_mode: bool = False, top_k: int = 10):
    """
    Função de resposta para o chatbot Gradio

    Args:
        message: Mensagem do usuário
        chat_history: Histórico do chat (formato messages)
        selected_model: Modelo selecionado
        advanced_mode: Modo avançado habilitado
        processing_enabled: Se o Processing Agent está habilitado
        processing_model: Modelo para o Processing Agent
        connection_type: Tipo de conexão ("csv" ou "postgresql")
        postgresql_config: Configuração postgresql (se aplicável)
        selected_table: Tabela selecionada (para postgresql)
        single_table_mode: Se deve usar apenas uma tabela (postgresql)
        top_k: Número máximo de resultados (LIMIT) para queries SQL

    Returns:
        Tupla com (mensagem_vazia, histórico_atualizado, imagem_grafico)
    """
    import logging

    logging.info(f"[GRADIO RESPOND] ===== NOVA REQUISIÇÃO =====")
    logging.info(f"[GRADIO RESPOND] Message: {message}")
    logging.info(f"[GRADIO RESPOND] Selected model: {selected_model}")
    logging.info(f"[GRADIO RESPOND] Advanced mode: {advanced_mode}")
    logging.info(f"[GRADIO RESPOND] Processing enabled: {processing_enabled}")
    logging.info(f"[GRADIO RESPOND] Processing model: {processing_model}")
    logging.info(f"[GRADIO RESPOND] 📊 TOP_K recebido: {top_k}")

    if not message.strip():
        return "", chat_history, None

    # Processa resposta
    response, graph_image_path, create_table_btn_update = chatbot_response(message, selected_model, advanced_mode, processing_enabled, processing_model, connection_type, postgresql_config, selected_table, single_table_mode, top_k)

    # Atualiza histórico no formato messages
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": response})

    return "", chat_history, graph_image_path, create_table_btn_update

def handle_csv_and_clear_chat(file):
    """
    Processa csv e limpa chat com indicador de carregamento melhorado

    Args:
        file: Arquivo csv

    Returns:
        Tupla com (feedback, chat_limpo, grafico_limpo, status)
    """
    global connection_ready

    if file is None:
        connection_ready = False
        return "", [], gr.update(visible=False), "**Status**: <span class='status-error'>Nenhum arquivo selecionado</span>"

    # Indica carregamento
    connection_ready = False

    # Processa arquivo
    feedback = handle_csv_upload(file)

    # Status final baseado no resultado
    if "✅" in feedback:
        connection_ready = True
        final_status = "**Status**: <span class='status-connected'>csv processado com sucesso</span>"
    else:
        connection_ready = False
        final_status = "**Status**: <span class='status-error'>Erro no processamento do csv</span>"

    return feedback, [], gr.update(visible=False), final_status

def is_connection_ready(conn_type, pg_host=None, pg_port=None, pg_db=None, pg_user=None, pg_pass=None):
    """
    Verifica se há uma conexão de dados ativa e pronta para uso

    Args:
        conn_type: Tipo de conexão ("csv" ou "postgresql")
        pg_host, pg_port, pg_db, pg_user, pg_pass: Credenciais postgresql

    Returns:
        True se conexão está pronta, False caso contrário
    """
    global connection_ready, chat_blocked
    return connection_ready and not chat_blocked

def show_loading_in_chat(message):
    """
    Mostra mensagem de carregamento apenas no chat

    Args:
        message: Mensagem de carregamento

    Returns:
        Histórico atualizado com mensagem de carregamento
    """
    global chat_blocked
    chat_blocked = True

    return [
        {"role": "user", "content": "Alterando tipo de conexão..."},
        {"role": "assistant", "content": f"🔄 {message}"}
    ]

def clear_loading_from_chat():
    """
    Remove carregamento do chat
    """
    global chat_blocked
    chat_blocked = False

def load_default_csv_and_cleanup_postgresql():
    """
    Carrega a base csv padrão e limpa conexões postgresql ativas

    Returns:
        Mensagem de feedback sobre a operação
    """
    global connection_ready

    try:
        from agentgraph.utils.config import DEFAULT_CSV_PATH
        from agentgraph.utils.object_manager import get_object_manager
        import os

        # Verifica se o arquivo padrão existe
        if not os.path.exists(DEFAULT_CSV_PATH):
            connection_ready = False
            return "Arquivo csv padrão (tabela.csv) não encontrado"

        # Limpa conexões postgresql ativas
        obj_manager = get_object_manager()

        # Fecha engines postgresql (SQLAlchemy engines têm método dispose)
        for engine_id, engine in obj_manager._engines.items():
            try:
                if hasattr(engine, 'dispose'):
                    engine.dispose()
                    logging.info(f"[CLEANUP] Engine postgresql {engine_id} fechada")
            except Exception as e:
                logging.warning(f"[CLEANUP] Erro ao fechar engine {engine_id}: {e}")

        # Limpa objetos postgresql do ObjectManager
        obj_manager.clear_all()
        logging.info("[CLEANUP] Objetos postgresql limpos do ObjectManager")

        # Carrega csv padrão através do CustomNodeManager
        logging.info(f"[CSV_DEFAULT] Carregando arquivo padrão: {DEFAULT_CSV_PATH}")
        result = run_async(graph_manager.custom_node_manager.handle_csv_upload(DEFAULT_CSV_PATH, graph_manager.object_manager))

        # Atualiza sistema se carregamento foi bem-sucedido
        if result.get("success") and result.get("engine_id") and result.get("db_id"):
            graph_manager.engine_id = result["engine_id"]
            graph_manager.db_id = result["db_id"]

            # Cria novo agente SQL
            from agentgraph.agents.sql_agent import SQLAgentManager
            new_db = graph_manager.object_manager.get_database(graph_manager.db_id)
            if not new_db:
                logging.error(f"[CSV_DEFAULT] Banco de dados não encontrado com ID: {graph_manager.db_id}")
                return "❌ Erro: Banco de dados não encontrado após carregamento padrão"

            top_k = graph_manager.object_manager.get_global_config('top_k', 10)
            new_sql_agent = SQLAgentManager(
                db=new_db,
                model_name="gpt-4o-mini",
                single_table_mode=False,
                selected_table=None,
                top_k=top_k
            )
            graph_manager.agent_id = graph_manager.object_manager.store_sql_agent(new_sql_agent, graph_manager.db_id)

            # Limpa cache
            cache_manager = graph_manager.object_manager.get_cache_manager(graph_manager.cache_id)
            if cache_manager:
                cache_manager.clear_cache()

            logging.info("[CSV_DEFAULT] Sistema atualizado com CSV padrão")

        if result.get("success", False):
            connection_ready = True
            return f"✅ Base padrão carregada: {os.path.basename(DEFAULT_CSV_PATH)}"
        else:
            connection_ready = False
            return f"Erro ao carregar base padrão: {result.get('message', 'Erro desconhecido')}"

    except Exception as e:
        connection_ready = False
        error_msg = f"Erro ao carregar base padrão: {e}"
        logging.error(f"[CSV_DEFAULT] {error_msg}")
        return error_msg

def reset_all():
    """
    Reseta tudo e limpa interface

    Returns:
        Tupla com (feedback, chat_limpo, arquivo_limpo, grafico_limpo)
    """
    feedback = reset_system()
    return feedback, [], None, gr.update(visible=False)

# Funções globais para modal de criação de tabela
def show_create_table_modal():
    """Mostra o modal de criação de tabela"""
    logging.info("[CREATE_TABLE] 🎯 Botão de criar tabela clicado!")
    logging.info("[CREATE_TABLE] 🎯 Abrindo modal...")
    return gr.update(visible=True), ""

def hide_create_table_modal():
    """Esconde o modal de criação de tabela"""
    logging.info("[CREATE_TABLE] ❌ Modal fechado")
    return gr.update(visible=False), ""

def create_table_from_sql(table_name, pg_host, pg_port, pg_db, pg_user, pg_pass):
    """Cria nova tabela no PostgreSQL baseada na SQL query"""
    global _last_sql_query

    try:
        from agentgraph.utils.postgresql_table_creator import create_table_from_query, validate_table_name

        if not table_name or not table_name.strip():
            return gr.update(visible=False), "❌ Nome da tabela é obrigatório"

        # Valida nome da tabela
        if not validate_table_name(table_name.strip()):
            return gr.update(visible=False), "❌ Nome da tabela inválido. Use apenas letras, números e underscore, começando com letra."

        # Recupera a SQL query do estado global
        if not _last_sql_query:
            return gr.update(visible=False), "❌ Nenhuma query SQL disponível. Execute uma consulta primeiro."

        # Prepara configuração PostgreSQL
        postgresql_config = {
            "host": pg_host,
            "port": pg_port,
            "database": pg_db,
            "username": pg_user,
            "password": pg_pass
        }

        # Cria a tabela (função assíncrona executada de forma síncrona)
        result = run_async(create_table_from_query(
            table_name.strip(),
            _last_sql_query,
            postgresql_config
        ))

        return gr.update(visible=False), result["message"]

    except Exception as e:
        return gr.update(visible=False), f"❌ Erro ao criar tabela: {str(e)}"

# Interface Gradio
def create_interface():
    """Cria interface Gradio"""

    # CSS customizado para interface limpa e moderna
    custom_css = """
    .gradio-container {
        padding: 20px 30px !important;
    }

    /* Seções de configuração */
    .config-section {
        background: #f8f9fa;
        border-radius: 15px;
        padding: 0;
        margin: 16px 0;
        overflow: hidden;
    }

    /* Headers dos containers com espaçamento adequado */
    .gradio-container h3 {
        margin: 0 !important;
        color: #f1f3f4 !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }

    /* Espaçamento para status e informações nos containers */
    .config-section .status-connected,
    .config-section .status-loading,
    .config-section .status-error,
    .config-section .status-waiting {
        padding: 8px 20px !important;
        display: block !important;
    }

    .prose.svelte-lag733 {
        padding: 12px 20px !important;
        margin: 0 !important;
    }

    /* Conteúdo dos containers */
    .config-content {
        padding: 20px;
    }

    /* Status indicators melhorados */
    .status-connected {
        color: #28a745;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    .status-loading {
        color: #ffc107;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    .status-loading::before {
        content: "⏳";
        animation: pulse 1.5s infinite;
    }

    .status-error {
        color: #dc3545;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    .status-waiting {
        color: #6c757d;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    /* Animação de carregamento */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Espaçamentos internos */
    .gr-form {
        padding: 16px;
    }

    .gr-box {
        padding: 16px;
        margin: 12px 0;
    }

    /* Melhorias para seção postgresql */
    .pg-section {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
    }

    .pg-feedback {
        padding: 12px;
        margin: 8px 0;
        border-radius: 6px;
        background: #f1f3f4;
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(), css=custom_css) as demo:

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## Configurações")

                # 1. CONEXÃO DE DADOS
                with gr.Group():
                    gr.Markdown("### Conexão de Dados")

                    with gr.Group():
                        connection_type = gr.Radio(
                            choices=[("CSV", "csv"), ("PostgreSQL", "postgresql")],
                            value="csv",
                            label="Tipo de Conexão"
                        )

                        # Status da conexão
                        connection_status = gr.Markdown("**Status**: <span class='status-connected'>Base padrão carregada</span>")

                # Seção csv
                with gr.Group(visible=True) as csv_section:
                    csv_file = gr.File(
                        file_types=[".csv"],
                        label="Arquivo csv"
                    )
                    upload_feedback = gr.Markdown()

                # Seção postgresql
                with gr.Group(visible=False) as postgresql_section:
                    with gr.Group():
                        with gr.Row():
                            # Host padrão baseado no ambiente
                            from agentgraph.utils.config import get_postgresql_host_for_environment
                            default_pg_host = get_postgresql_host_for_environment()

                            pg_host = gr.Textbox(
                                label="Host",
                                value=default_pg_host,
                                placeholder=default_pg_host,
                                scale=2
                            )
                            pg_port = gr.Textbox(
                                label="Porta",
                                value="5432",
                                placeholder="5432",
                                scale=1
                            )

                        pg_database = gr.Textbox(
                            label="Banco de Dados",
                            placeholder="nome_do_banco"
                        )

                        with gr.Row():
                            pg_username = gr.Textbox(
                                label="Usuário",
                                placeholder="usuario",
                                scale=1
                            )
                            pg_password = gr.Textbox(
                                label="Senha",
                                type="password",
                                placeholder="senha",
                                scale=1
                            )

                        pg_connect_btn = gr.Button(
                            "Conectar postgresql",
                            variant="primary",
                            size="lg"
                        )

                        pg_feedback = gr.Markdown()

                    # Configuração de tabelas (visível após conexão)
                    with gr.Group(visible=False) as pg_table_section:
                        gr.Markdown("#### Configuração de Tabelas")

                        with gr.Group():
                            pg_single_table_mode = gr.Checkbox(
                                label="Modo Tabela Única",
                                value=False
                            )

                            # Seletor de tabela
                            with gr.Group(visible=False) as pg_table_selector_group:
                                pg_table_selector = gr.Dropdown(
                                    choices=[],
                                    label="Selecionar Tabela",
                                    interactive=True
                                )

                            pg_table_info = gr.Markdown()

                # 2. CONFIGURAÇÃO DE MODELOS
                with gr.Group():
                    gr.Markdown("### Configuração de Agentes")

                    with gr.Group():
                        # Processing Agent
                        processing_checkbox = gr.Checkbox(
                            label="Processing Agent",
                            value=False
                        )
                        processing_model_selector = gr.Dropdown(
                            choices=list(AVAILABLE_MODELS.keys()) + list(REFINEMENT_MODELS.keys()),
                            value="GPT-4o-mini",
                            label="Modelo do Processing Agent",
                            visible=False
                        )

                        # Modelo principal SQL
                        model_selector = gr.Dropdown(
                            list(AVAILABLE_MODELS.keys()),
                            value=DEFAULT_MODEL,
                            label="Modelo SQL Principal"
                        )

                # 3. CONFIGURAÇÕES AVANÇADAS
                with gr.Group():
                    gr.Markdown("### Configurações Avançadas")

                    with gr.Group():
                        advanced_checkbox = gr.Checkbox(
                            label="Refinar Resposta"
                        )

                        # Controle TOP_K para LIMIT das queries SQL
                        with gr.Group():
                            top_k_input = gr.Number(
                                value=DEFAULT_TOP_K,
                                label="LIMIT",
                                minimum=1,
                                maximum=100000,
                                step=1,
                                info="Define quantos registros serão retornados nas consultas SQL"
                            )
                            top_k_apply_btn = gr.Button(
                                "Aplicar",
                                variant="primary",
                                scale=1
                            )
                            top_k_feedback = gr.Markdown("", visible=False)

                # 4. STATUS E CONTROLES
                with gr.Group():
                    gr.Markdown("### Status do Sistema")

                    with gr.Group():
                        # Status do LangSmith
                        if is_langsmith_enabled():
                            gr.Markdown(f"**LangSmith**: Ativo")
                        else:
                            gr.Markdown("**LangSmith**: Desabilitado")

                        reset_btn = gr.Button(
                            "Resetar Sistema",
                            variant="secondary"
                        )
                
            with gr.Column(scale=4):
                gr.Markdown("## Agent86")
                chatbot = gr.Chatbot(
                    height=600,
                    show_label=False,
                    container=True,
                    type="messages"
                )

                msg = gr.Textbox(placeholder="Digite sua pergunta aqui...", lines=1, label="")
                btn = gr.Button("Enviar", variant="primary")
                history_btn = gr.Button("Histórico", variant="secondary")
                history_output = gr.JSON()

                # Componente para exibir gráficos - posicionado após histórico
                graph_image = gr.Image(
                    label="📊 Visualização de Dados",
                    visible=False,
                    height=500,  # Altura maior para ocupar mais espaço
                    show_label=True,
                    container=True,
                    interactive=False,
                    show_download_button=True
                )

                # Botão para criar tabela PostgreSQL (aparece quando disponível)
                create_table_btn = gr.Button(
                    "📊 Criar Tabela no PostgreSQL",
                    visible=False,
                    variant="secondary",
                    size="sm"
                )

                # Modal para criar tabela PostgreSQL
                with gr.Group(visible=False) as create_table_modal:
                    gr.Markdown("### 📊 Criar Nova Tabela no PostgreSQL")

                    with gr.Row():
                        table_name_input = gr.Textbox(
                            label="Nome da Tabela",
                            placeholder="Digite o nome da nova tabela...",
                            value="",
                            scale=3
                        )

                    with gr.Row():
                        gr.Markdown("**Atenção:** A tabela será criada com todos os dados da query (sem LIMIT).")

                    with gr.Row():
                        create_table_confirm_btn = gr.Button(
                            "✅ Confirmar Criação",
                            variant="primary",
                            scale=1
                        )
                        create_table_cancel_btn = gr.Button(
                            "❌ Cancelar",
                            variant="secondary",
                            scale=1
                        )

                    create_table_status = gr.Markdown("", visible=False)

                download_file = gr.File(visible=False)



        # Função para mostrar carregamento de transição no chat
        def show_transition_loading(conn_type):
            """Mostra carregamento de transição apenas no chat"""
            if conn_type == "csv":
                loading_chat = show_loading_in_chat("Fechando postgresql e carregando base csv padrão...")
                return "", loading_chat, gr.update(visible=False)
            else:
                return "", [], gr.update(visible=False)

        # Event handlers (usando as funções originais do sistema)
        def handle_response_with_graph(message, chat_history, model, advanced, processing_enabled, processing_model, conn_type, pg_host, pg_port, pg_db, pg_user, pg_pass, pg_table, pg_single_mode, top_k_value):
            """Wrapper para lidar com resposta e gráfico"""

            # Verifica se há conexão ativa antes de processar
            if not is_connection_ready(conn_type, pg_host, pg_port, pg_db, pg_user, pg_pass):
                error_msg = "⚠️ **Aguarde**: Configure e conecte a uma fonte de dados antes de fazer perguntas."
                chat_history.append({"role": "user", "content": message})
                chat_history.append({"role": "assistant", "content": error_msg})
                return "", chat_history, gr.update(visible=False)

            # Prepara configuração postgresql se necessário
            postgresql_config = None
            if conn_type == "postgresql":
                postgresql_config = {
                    "host": pg_host,
                    "port": pg_port,
                    "database": pg_db,
                    "username": pg_user,
                    "password": pg_pass
                }

            # Converte top_k_value para int se necessário
            top_k = int(top_k_value) if top_k_value else 10
            empty_msg, updated_history, graph_path, create_table_btn_update = respond(message, chat_history, model, advanced, processing_enabled, processing_model, conn_type, postgresql_config, pg_table, pg_single_mode, top_k)

            # Controla visibilidade do componente de gráfico
            if graph_path:
                return empty_msg, updated_history, gr.update(value=graph_path, visible=True), create_table_btn_update
            else:
                return empty_msg, updated_history, gr.update(visible=False), create_table_btn_update

        def toggle_processing_agent(enabled):
            """Controla visibilidade do seletor de modelo do Processing Agent"""
            return gr.update(visible=enabled)

        def toggle_connection_type(conn_type):
            """Controla visibilidade das seções de conexão - FECHA POSTGRES IMEDIATAMENTE"""
            global connection_ready

            if conn_type == "csv":
                # PRIMEIRO: Fecha container postgresql imediatamente
                # SEGUNDO: Executa transição em background
                feedback_msg = load_default_csv_and_cleanup_postgresql()
                if "✅" in feedback_msg:
                    connection_ready = True
                    status_msg = "**Status**: <span class='status-connected'>Base padrão carregada</span>"
                else:
                    connection_ready = False
                    status_msg = "**Status**: <span class='status-error'>Erro na conexão</span>"

                return (
                    gr.update(visible=True),   # csv_section - MOSTRA IMEDIATAMENTE
                    gr.update(visible=False),  # postgresql_section - FECHA IMEDIATAMENTE
                    feedback_msg,              # upload_feedback
                    status_msg,                # connection_status
                    # Limpa campos postgresql IMEDIATAMENTE
                    gr.update(value=""),       # pg_host
                    gr.update(value="5432"),   # pg_port
                    gr.update(value=""),       # pg_database
                    gr.update(value=""),       # pg_username
                    gr.update(value=""),       # pg_password
                    gr.update(value=""),       # pg_feedback
                    gr.update(visible=False),  # pg_table_section
                    gr.update(value=False),    # pg_single_table_mode
                    gr.update(visible=False),  # pg_table_selector_group
                    gr.update(choices=[], value=None),  # pg_table_selector
                    gr.update(value="")        # pg_table_info
                )

            else:  # postgresql
                connection_ready = False
                status_msg = "**Status**: <span class='status-waiting'>Aguardando configuração postgresql</span>"
                return (
                    gr.update(visible=False),  # csv_section
                    gr.update(visible=True),   # postgresql_section
                    "",                        # upload_feedback
                    status_msg,                # connection_status
                    # Mantém campos postgresql como estão
                    gr.update(),  # pg_host
                    gr.update(),  # pg_port
                    gr.update(),  # pg_database
                    gr.update(),  # pg_username
                    gr.update(),  # pg_password
                    gr.update(),  # pg_feedback
                    gr.update(),  # pg_table_section
                    gr.update(),  # pg_single_table_mode
                    gr.update(),  # pg_table_selector_group
                    gr.update(),  # pg_table_selector
                    gr.update()   # pg_table_info
                )

        def handle_postgresql_connect(host, port, database, username, password):
            """Wrapper para conexão postgresql"""
            global connection_ready

            # Executa conexão
            connection_ready = False
            result = handle_postgresql_connection(host, port, database, username, password)

            # Se conexão foi bem-sucedida, retorna tabelas disponíveis
            if "✅" in result:
                connection_ready = True
                try:
                    # Obtém tabelas do ObjectManager
                    from agentgraph.utils.object_manager import get_object_manager
                    obj_manager = get_object_manager()

                    # Busca metadados de conexão mais recente
                    all_metadata = obj_manager.get_all_connection_metadata()
                    if all_metadata:
                        latest_metadata = list(all_metadata.values())[-1]
                        tables = latest_metadata.get("tables", [])

                        # Status de sucesso
                        success_status = "**Status**: <span class='status-connected'>postgresql conectado com sucesso</span>"
                        table_info = f"**Modo Multi-Tabela ativo** - {len(tables)} tabelas disponíveis"

                        # Retorna resultado + atualização do seletor
                        return (
                            f"✅ **Conectado com sucesso!** {len(tables)} tabelas encontradas",  # feedback
                            gr.update(visible=True),  # pg_table_section
                            False,  # pg_single_table_mode (padrão desativado)
                            gr.update(visible=False),  # pg_table_selector_group (oculto por padrão)
                            gr.update(choices=tables, value=tables[0] if tables else None),  # pg_table_selector
                            table_info,  # pg_table_info
                            success_status  # connection_status
                        )
                except Exception as e:
                    logging.error(f"Erro ao obter tabelas: {e}")

            # Se falhou, mantém seção de tabela oculta
            connection_ready = False
            error_status = "**Status**: <span class='status-error'>Falha na conexão postgresql</span>"
            return (
                result,  # feedback
                gr.update(visible=False),  # pg_table_section
                False,  # pg_single_table_mode
                gr.update(visible=False),  # pg_table_selector_group
                gr.update(choices=[], value=None),  # pg_table_selector
                "",  # pg_table_info
                error_status  # connection_status
            )

        def toggle_table_mode(single_mode_enabled, current_table):
            """Alterna entre modo multi-tabela e tabela única"""
            if single_mode_enabled:
                # Modo tabela única ativado
                return (
                    gr.update(visible=True),  # pg_table_selector_group
                    f"**Modo Tabela Única ativo** - Usando: {current_table or 'Selecione uma tabela'}"
                )
            else:
                # Modo multi-tabela ativado
                return (
                    gr.update(visible=False),  # pg_table_selector_group
                    "**Modo Multi-Tabela ativo** - Pode usar todas as tabelas e fazer JOINs"
                )

        # Configuração de concorrência baseada no ambiente
        if is_docker_environment():
            # Docker: Alta concorrência sem fila
            concurrency_limit = None  # Sem limite
            logging.info("[GRADIO] Docker - Configurando alta concorrência sem limite")
        else:
            # Windows: Concorrência limitada para estabilidade
            concurrency_limit = 1
            logging.info("[GRADIO] Windows - Configurando concorrência limitada")

        msg.submit(
            handle_response_with_graph,
            inputs=[msg, chatbot, model_selector, advanced_checkbox, processing_checkbox, processing_model_selector, connection_type, pg_host, pg_port, pg_database, pg_username, pg_password, pg_table_selector, pg_single_table_mode, top_k_input],
            outputs=[msg, chatbot, graph_image, create_table_btn],
            show_progress=True,  # Mostra carregamento no input do chat
            concurrency_limit=concurrency_limit
        )

        btn.click(
            handle_response_with_graph,
            inputs=[msg, chatbot, model_selector, advanced_checkbox, processing_checkbox, processing_model_selector, connection_type, pg_host, pg_port, pg_database, pg_username, pg_password, pg_table_selector, pg_single_table_mode, top_k_input],
            outputs=[msg, chatbot, graph_image, create_table_btn],
            concurrency_limit=concurrency_limit
        )

        # Conecta botão de aplicar TOP_K
        top_k_apply_btn.click(
            apply_top_k,
            inputs=[top_k_input],
            outputs=[top_k_feedback]
        ).then(
            lambda: gr.update(visible=True),
            outputs=[top_k_feedback]
        )

        csv_file.change(
            handle_csv_and_clear_chat,
            inputs=csv_file,
            outputs=[upload_feedback, chatbot, graph_image, connection_status],
            show_progress="minimal"  # Mostra carregamento mínimo
        )

        reset_btn.click(
            reset_all,
            outputs=[upload_feedback, chatbot, csv_file, graph_image]
        )

        advanced_checkbox.change(
            toggle_advanced_mode,
            inputs=advanced_checkbox,
            outputs=[]
        )

        history_btn.click(
            toggle_history,
            outputs=history_output
        )

        processing_checkbox.change(
            toggle_processing_agent,
            inputs=processing_checkbox,
            outputs=processing_model_selector
        )

        # Executa toggle imediatamente (sem carregamento nos campos)
        connection_type.change(
            toggle_connection_type,
            inputs=connection_type,
            outputs=[
                csv_section, postgresql_section, upload_feedback, connection_status,
                pg_host, pg_port, pg_database, pg_username, pg_password, pg_feedback,
                pg_table_section, pg_single_table_mode, pg_table_selector_group,
                pg_table_selector, pg_table_info
            ],
            show_progress=False  # Não mostra carregamento nos campos
        )

        pg_connect_btn.click(
            handle_postgresql_connect,
            inputs=[pg_host, pg_port, pg_database, pg_username, pg_password],
            outputs=[pg_feedback, pg_table_section, pg_single_table_mode, pg_table_selector_group, pg_table_selector, pg_table_info, connection_status],
            show_progress="minimal"  # Mostra carregamento mínimo
        )

        # Event handler para toggle de modo de tabela
        pg_single_table_mode.change(
            toggle_table_mode,
            inputs=[pg_single_table_mode, pg_table_selector],
            outputs=[pg_table_selector_group, pg_table_info]
        )

        # Event handler para botão de criar tabela
        create_table_btn.click(
            show_create_table_modal,
            outputs=[create_table_modal, table_name_input]
        )

        # Event handlers para modal de criação de tabela
        create_table_cancel_btn.click(
            hide_create_table_modal,
            outputs=[create_table_modal, create_table_status]
        )

        create_table_confirm_btn.click(
            create_table_from_sql,
            inputs=[table_name_input, pg_host, pg_port, pg_database, pg_username, pg_password],
            outputs=[create_table_modal, create_table_status]
        )

    return demo

async def main():
    """Função principal"""
    # Inicializa aplicação
    success = await initialize_app()

    if not success:
        logging.error("Falha na inicialização. Encerrando aplicação.")
        return

    # Cria e lança interface
    demo = create_interface()

    # Tenta diferentes portas se a padrão estiver ocupada
    ports_to_try = [GRADIO_PORT, 7861, 7862, 7863, 7864, 0]  # 0 = porta automática

    for port in ports_to_try:
        try:
            logging.info(f"Tentando iniciar interface Gradio na porta {port}")

            # Configurações para Docker
            server_name = "0.0.0.0" if GRADIO_SHARE else "127.0.0.1"

            if GRADIO_SHARE:
                logging.info("🌐 Configurando link público do Gradio...")

            # Configurações baseadas no ambiente
            if is_docker_environment():
                # Docker: Configurações para alta concorrência
                max_threads = int(os.getenv("GRADIO_MAX_THREADS", "50"))
                logging.info(f"[GRADIO] Docker - Max threads: {max_threads}")

                demo.launch(
                    server_name=server_name,
                    server_port=port if port != 0 else None,
                    share=GRADIO_SHARE,
                    show_error=True,
                    quiet=False,
                    max_threads=max_threads
                )
            else:
                # Windows: Configurações padrão
                logging.info(f"[GRADIO] Windows - Configurações padrão")

                demo.launch(
                    server_name=server_name,
                    server_port=port if port != 0 else None,
                    share=GRADIO_SHARE,
                    show_error=True,
                    quiet=False
                )
            break  # Se chegou aqui, deu certo
        except OSError as e:
            if "Cannot find empty port" in str(e) and port != ports_to_try[-1]:
                logging.warning(f"Porta {port} ocupada, tentando próxima...")
                continue
            else:
                logging.error(f"Erro ao iniciar servidor: {e}")
                raise
        except Exception as e:
            logging.error(f"Erro inesperado ao iniciar interface: {e}")
            raise

if __name__ == "__main__":
    run_async(main())
