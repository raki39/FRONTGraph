"""
Configurações e constantes do projeto AgentGraph
"""
import os
from dotenv import load_dotenv
import logging

# Carrega variáveis de ambiente
load_dotenv()

# Compatibilidade com variáveis .env fornecidas
# Se REDIS_URL/REDIS_RESULT_BACKEND estiverem definidos e CELERY_* não, propagar
try:
    _redis_url = os.getenv("REDIS_URL")
    _redis_result = os.getenv("REDIS_RESULT_BACKEND")
    if _redis_url and not os.getenv("CELERY_BROKER_URL"):
        os.environ["CELERY_BROKER_URL"] = _redis_url
    if _redis_result and not os.getenv("CELERY_RESULT_BACKEND"):
        os.environ["CELERY_RESULT_BACKEND"] = _redis_result
    # Se USE_CELERY foi definido, alinhar com CELERY_ENABLED
    if os.getenv("USE_CELERY") and not os.getenv("CELERY_ENABLED"):
        os.environ["CELERY_ENABLED"] = os.getenv("USE_CELERY")
except Exception:
    pass

# Configurações de API
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configurações do LangSmith (observabilidade)
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "agentgraph-project")

# Detecção de ambiente
def is_docker_environment() -> bool:
    """
    Detecta se está rodando em ambiente Docker

    Returns:
        True se estiver em Docker, False caso contrário
    """
    # Método 1: Variável de ambiente específica
    if os.getenv("DOCKER_CONTAINER", "false").lower() == "true":
        return True

    # Método 2: Verificar se existe arquivo /.dockerenv
    if os.path.exists("/.dockerenv"):
        return True

    # Método 3: Verificar cgroup (Linux containers)
    try:
        with open("/proc/1/cgroup", "r") as f:
            content = f.read()
            if "docker" in content or "containerd" in content:
                return True
    except (FileNotFoundError, PermissionError):
        pass

    return False

# Configurações do Celery (processamento assíncrono)
CELERY_ENABLED = os.getenv("CELERY_ENABLED", "true").lower() == "true"

# URLs dinâmicas baseadas no ambiente
if is_docker_environment():
    # Configurações para Docker
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
    CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "8"))  # Alta concorrência para Docker
    CELERY_WORKER_COUNT = int(os.getenv("CELERY_WORKER_COUNT", "1"))  # Worker único otimizado
    REDIS_HOST = "redis"
    REDIS_PORT = 6379
else:
    # Configurações para Windows local
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "1"))  # Single-thread para Windows
    CELERY_WORKER_COUNT = int(os.getenv("CELERY_WORKER_COUNT", "1"))  # Single worker
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379

FLOWER_PORT = int(os.getenv("FLOWER_PORT", "5555"))

# Configurações de arquivos e diretórios
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploaded_data")
DEFAULT_CSV_PATH = os.getenv("DEFAULT_CSV_PATH", "tabela.csv")
SQL_DB_PATH = os.getenv("SQL_DB_PATH", "data.db")
UPLOADED_CSV_PATH = os.path.join(UPLOAD_DIR, "tabela.csv")

# Modelos disponíveis para seleção (usados no agentSQL)
AVAILABLE_MODELS = {
    "GPT-o3-mini": "o3-mini",
    "GPT-4o-mini": "gpt-4o-mini",
    "GPT-4o": "gpt-4o",
    "Claude-3.5-Sonnet": "claude-3-5-sonnet-20241022",
    "Gemini-1.5-Pro": "gemini-1.5-pro",
    "Gemini-2.0-Flash": "gemini-2.0-flash"
}

# Modelos para refinamento (apenas uso interno)
REFINEMENT_MODELS = {
    "LLaMA 70B": "meta-llama/Llama-3.3-70B-Instruct",
    "LlaMA 8B": "meta-llama/Llama-3.1-8B-Instruct",
    "DeepSeek-R1": "deepseek-ai/DeepSeek-R1-0528"
}

# Mapeamento completo de modelos (para compatibilidade)
LLAMA_MODELS = {**AVAILABLE_MODELS, **REFINEMENT_MODELS}

MAX_TOKENS_MAP = {
    # Modelos de refinamento
    "meta-llama/Llama-3.3-70B-Instruct": 900,
    "meta-llama/Llama-3.1-8B-Instruct": 700,
    "deepseek-ai/DeepSeek-R1-0528": 8192,
    # Modelos do agentSQL
    "o3-mini": 4096,
    "gpt-4o-mini": 4096,
    "gpt-4o": 4096,
    "claude-3-5-sonnet-20241022": 1024,
    "gemini-1.5-pro": 4096,
    "gemini-2.0-flash": 4096
}

# Modelos que usam OpenAI (GPT)
OPENAI_MODELS = {
    "o3-mini",
    "gpt-4o-mini",
    "gpt-4o",
}

# Modelos que usam Anthropic (Claude)
ANTHROPIC_MODELS = {
    "claude-3-5-sonnet-20241022"
}

# Modelos que usam Google (Gemini)
GOOGLE_MODELS = {
    "gemini-1.5-pro",
    "gemini-2.0-flash"
}

# Modelos que usam HuggingFace (para refinamento)
HUGGINGFACE_MODELS = {
    "meta-llama/Llama-3.3-70B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "deepseek-ai/DeepSeek-R1-0528"
}

# Configurações do agente
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "GPT-4o-mini")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "40"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "10"))

# Configurações do Gradio
GRADIO_SHARE = os.getenv("GRADIO_SHARE", "False").lower() == "true"
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7860"))

# Configurações de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configuração do logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Cria diretório de upload se não existir
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configuração das variáveis de ambiente para OpenAI
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Configuração das variáveis de ambiente para Google
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Configuração das variáveis de ambiente para Anthropic
if ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

# Configuração das variáveis de ambiente para LangSmith
if LANGSMITH_API_KEY:
    os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGSMITH_TRACING"] = str(LANGSMITH_TRACING).lower()
    os.environ["LANGSMITH_ENDPOINT"] = LANGSMITH_ENDPOINT
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
    logging.info(f"LangSmith configurado: projeto='{LANGSMITH_PROJECT}', tracing={LANGSMITH_TRACING}")
else:
    logging.info("LangSmith não configurado (LANGSMITH_API_KEY não encontrada)")

def get_active_csv_path():
    """Retorna o CSV ativo: o carregado ou o padrão."""
    if os.path.exists(UPLOADED_CSV_PATH):
        logging.info(f"[CSV] Usando arquivo CSV carregado: {UPLOADED_CSV_PATH}")
        return UPLOADED_CSV_PATH
    else:
        logging.info(f"[CSV] Usando arquivo CSV padrão: {DEFAULT_CSV_PATH}")
        return DEFAULT_CSV_PATH

def get_environment_info() -> dict:
    """
    Retorna informações sobre o ambiente de execução

    Returns:
        Dicionário com informações do ambiente
    """
    is_docker = is_docker_environment()

    return {
        "is_docker": is_docker,
        "environment": "Docker" if is_docker else "Windows Local",
        "redis_url": CELERY_BROKER_URL,
        "redis_host": REDIS_HOST,
        "redis_port": REDIS_PORT,
        "worker_concurrency": CELERY_WORKER_CONCURRENCY,
        "worker_count": CELERY_WORKER_COUNT,
        "celery_enabled": CELERY_ENABLED
    }

def get_redis_connection_url() -> str:
    """
    Retorna URL de conexão Redis baseada no ambiente

    Returns:
        URL de conexão Redis
    """
    return CELERY_BROKER_URL

def get_postgresql_host_for_environment() -> str:
    """
    Retorna host PostgreSQL apropriado para o ambiente

    Returns:
        Host PostgreSQL (localhost para Windows, host.docker.internal para Docker)
    """
    if is_docker_environment():
        return "host.docker.internal"  # Permite acesso ao PostgreSQL do host
    else:
        return "localhost"

def validate_config():
    """Valida se as configurações necessárias estão presentes."""
    errors = []
    warnings = []

    if not HUGGINGFACE_API_KEY:
        errors.append("HUGGINGFACE_API_KEY não configurada")

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY não configurada")

    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY não configurada")

    if not os.path.exists(DEFAULT_CSV_PATH):
        errors.append(f"Arquivo CSV padrão não encontrado: {DEFAULT_CSV_PATH}")

    # LangSmith é opcional - apenas aviso se não configurado
    if not LANGSMITH_API_KEY:
        warnings.append("LANGSMITH_API_KEY não configurada - observabilidade desabilitada")

    if errors:
        raise ValueError(f"Erros de configuração: {', '.join(errors)}")

    if warnings:
        for warning in warnings:
            logging.warning(warning)

    # Log informações do ambiente
    env_info = get_environment_info()
    logging.info(f"🌍 Ambiente detectado: {env_info['environment']}")
    logging.info(f"🔗 Redis URL: {env_info['redis_url']}")
    logging.info(f"⚙️ Workers: {env_info['worker_count']} x {env_info['worker_concurrency']} concurrency")

    logging.info("Configurações validadas com sucesso")
    return True

def is_langsmith_enabled() -> bool:
    """
    Verifica se o LangSmith está habilitado e configurado

    Returns:
        True se LangSmith estiver habilitado, False caso contrário
    """
    return bool(LANGSMITH_API_KEY and LANGSMITH_TRACING)

def get_langsmith_metadata() -> dict:
    """
    Retorna metadados padrão para traces do LangSmith

    Returns:
        Dicionário com metadados do projeto
    """
    if not is_langsmith_enabled():
        return {}

    return {
        "project": LANGSMITH_PROJECT,
        "application": "AgentGraph",
        "version": "1.0.0",
        "environment": "production"
    }
