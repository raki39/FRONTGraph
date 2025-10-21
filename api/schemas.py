from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum
import json

# Enums
class UserRoleEnum(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

# Auth
class UserCreate(BaseModel):
    nome: str
    email: EmailStr
    password: str
    role: Optional[UserRoleEnum] = UserRoleEnum.USER

# Users / Empresas
class UserOut(BaseModel):
    id: int
    email: EmailStr
    nome: str
    ativo: bool
    role: UserRoleEnum
    created_at: datetime
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    ativo: Optional[bool] = None
    role: Optional[UserRoleEnum] = None

class UserRoleUpdate(BaseModel):
    role: UserRoleEnum

class TokenWithUSer(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    
class EmpresaOut(BaseModel):
    id: int
    nome: str
    slug: str
    created_at: datetime
    class Config:
        from_attributes = True

# Datasets
class DatasetCreate(BaseModel):
    nome: str
    tipo: str  # csv/postgres
    source_path: Optional[str] = None
    db_uri: Optional[str] = None

class DatasetOut(BaseModel):
    id: int
    nome: str
    tipo: str
    source_path: Optional[str]
    db_uri: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

# Connections
class ConnectionCreate(BaseModel):
    tipo: str  # sqlite/duckdb/postgres
    dataset_id: Optional[int] = None  # para csv/sqlite
    pg_dsn: Optional[str] = None

class ConnectionUpdate(BaseModel):
    pg_dsn: Optional[str] = None

class ConnectionOut(BaseModel):
    id: int
    owner_user_id: Optional[int]
    tipo: str
    db_uri: Optional[str]
    pg_dsn: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

# Agents
class AgentCreate(BaseModel):
    nome: str
    connection_id: int
    selected_model: str
    top_k: int = 10
    include_tables_key: str = "*"
    advanced_mode: bool = False
    processing_enabled: bool = False
    refinement_enabled: bool = False
    single_table_mode: bool = False
    selected_table: str | None = None
    # Novos campos para UI/UX
    description: str | None = None
    icon: str | None = "MessageSquare"
    color: str | None = "from-blue-500 to-cyan-500"
    features: List[str] | None = None

class AgentUpdate(BaseModel):
    selected_model: Optional[str] = None
    top_k: Optional[int] = None
    include_tables_key: Optional[str] = None
    advanced_mode: Optional[bool] = None
    processing_enabled: Optional[bool] = None
    refinement_enabled: Optional[bool] = None
    single_table_mode: Optional[bool] = None
    selected_table: Optional[str] = None
    # Novos campos para UI/UX
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    features: Optional[List[str]] = None

class AgentOut(BaseModel):
    id: int
    owner_user_id: Optional[int]
    nome: str
    connection_id: int
    selected_model: str
    top_k: int
    include_tables_key: Optional[str]
    advanced_mode: bool
    processing_enabled: bool
    refinement_enabled: bool
    single_table_mode: bool
    selected_table: Optional[str]
    # Novos campos para UI/UX
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    features: Optional[List[str]]
    version: int
    created_at: datetime
    updated_at: datetime
    connection: Optional[ConnectionOut] = None

    @field_validator('features', mode='before')
    @classmethod
    def parse_features(cls, v):
        """Converte string JSON para lista"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    class Config:
        from_attributes = True

# Runs
class RunCreate(BaseModel):
    question: str
    chat_session_id: Optional[int] = None  # NOVO: Link para histórico

class RunOut(BaseModel):
    id: int
    agent_id: int
    user_id: int
    question: str
    task_id: Optional[str]
    sql_used: Optional[str]
    result_data: Optional[str]  # Resposta textual do agente SQL
    status: str
    execution_ms: Optional[int]
    result_rows_count: Optional[int]
    error_type: Optional[str]
    created_at: datetime
    finished_at: Optional[datetime]
    chat_session_id: Optional[int] = None  # NOVO: Link para histórico
    class Config:
        from_attributes = True

# ==========================================
# SCHEMAS DO SISTEMA DE HISTÓRICO
# ==========================================

# Chat Sessions
class ChatSessionCreate(BaseModel):
    agent_id: int
    title: Optional[str] = None  # Se não fornecido, será gerado automaticamente

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None  # active, archived

class ChatSessionOut(BaseModel):
    id: int
    user_id: int
    agent_id: int
    title: str
    created_at: datetime
    last_activity: datetime
    total_messages: int
    status: str
    context_summary: Optional[str]
    last_message: Optional[str] = None  # Última mensagem para contexto
    class Config:
        from_attributes = True

# Pagination Schema (definido antes para ser usado em outros schemas)
class PaginationInfo(BaseModel):
    """Informações de paginação"""
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

class ChatSessionListOut(BaseModel):
    """Schema otimizado para listagem de chat sessions"""
    id: int
    title: str
    last_message: Optional[str] = None
    messages_count: int
    updated_at: datetime
    status: str
    agent_id: int
    class Config:
        from_attributes = True

class ChatSessionListResponse(BaseModel):
    """Schema para resposta paginada de chat sessions"""
    sessions: List[ChatSessionListOut]
    pagination: PaginationInfo

    class Config:
        from_attributes = True

# Messages
class MessageCreate(BaseModel):
    role: str  # user, assistant, system
    content: str
    sql_query: Optional[str] = None
    message_metadata: Optional[Dict[str, Any]] = None

class MessageOut(BaseModel):
    id: int
    chat_session_id: int
    run_id: Optional[int]
    role: str
    content: str
    sql_query: Optional[str]
    created_at: datetime
    sequence_order: int
    message_metadata: Optional[Dict[str, Any]]
    class Config:
        from_attributes = True

# Message Embeddings
class MessageEmbeddingOut(BaseModel):
    id: int
    message_id: int
    embedding_model_version: str
    created_at: datetime

    class Config:
        from_attributes = True

# Conversation Summaries
class ConversationSummaryOut(BaseModel):
    id: int
    chat_session_id: int
    up_to_message_id: int
    summary: str
    created_at: datetime
    class Config:
        from_attributes = True

# Schemas compostos para responses
class ChatSessionWithMessages(ChatSessionOut):
    messages: List[MessageOut] = []

class MessageWithEmbedding(MessageOut):
    embedding: Optional[MessageEmbeddingOut] = None


# ==========================================
# SCHEMAS ADMIN
# ==========================================

# Admin User Management
class AdminUserCreate(BaseModel):
    nome: str
    email: EmailStr
    password: str
    ativo: bool = True

class AdminUserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    ativo: Optional[bool] = None

class AdminUserOut(UserOut):
    """Schema admin com informações extras"""
    pass

# Admin Dataset Management
class AdminDatasetCreate(BaseModel):
    nome: str
    tipo: str  # csv/postgres
    source_path: Optional[str] = None
    db_uri: Optional[str] = None
    owner_user_id: Optional[int] = None
    owner_empresa_id: Optional[int] = None

class AdminDatasetUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None
    source_path: Optional[str] = None
    db_uri: Optional[str] = None
    owner_user_id: Optional[int] = None
    owner_empresa_id: Optional[int] = None

class AdminDatasetOut(DatasetOut):
    """Schema admin com informações extras"""
    pass

# Admin Connection Management
class AdminConnectionCreate(BaseModel):
    tipo: str  # sqlite/duckdb/postgres
    dataset_id: Optional[int] = None
    pg_dsn: Optional[str] = None
    owner_user_id: Optional[int] = None
    owner_empresa_id: Optional[int] = None

class AdminConnectionUpdate(BaseModel):
    tipo: Optional[str] = None
    pg_dsn: Optional[str] = None
    owner_user_id: Optional[int] = None
    owner_empresa_id: Optional[int] = None

class AdminConnectionOut(ConnectionOut):
    """Schema admin com informações extras"""
    pass

# Admin Agent Management
class AdminAgentCreate(BaseModel):
    nome: str
    connection_id: int
    selected_model: str
    top_k: int = 10
    include_tables_key: str = "*"
    advanced_mode: bool = False
    processing_enabled: bool = False
    refinement_enabled: bool = False
    single_table_mode: bool = False
    selected_table: str | None = None
    description: str | None = None
    icon: str | None = "MessageSquare"
    color: str | None = "from-blue-500 to-cyan-500"
    features: List[str] | None = None
    owner_user_id: Optional[int] = None
    owner_empresa_id: Optional[int] = None

class AdminAgentUpdate(BaseModel):
    nome: Optional[str] = None
    connection_id: Optional[int] = None
    selected_model: Optional[str] = None
    top_k: Optional[int] = None
    include_tables_key: Optional[str] = None
    advanced_mode: Optional[bool] = None
    processing_enabled: Optional[bool] = None
    refinement_enabled: Optional[bool] = None
    single_table_mode: Optional[bool] = None
    selected_table: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    features: Optional[List[str]] = None
    owner_user_id: Optional[int] = None
    owner_empresa_id: Optional[int] = None

class AdminAgentOut(AgentOut):
    """Schema admin com informações extras"""

    @field_validator('features', mode='before')
    @classmethod
    def parse_features(cls, v):
        """Converte string JSON para lista"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

# Admin Run Management
class AdminRunOut(RunOut):
    """Schema admin com informações extras"""
    pass

# Pagination Schemas (já definido acima)

class PaginatedRunsResponse(BaseModel):
    """Resposta paginada para runs"""
    runs: List[RunOut]
    pagination: PaginationInfo

class PaginatedAdminRunsResponse(BaseModel):
    """Resposta paginada para runs admin"""
    runs: List[AdminRunOut]
    pagination: PaginationInfo

# Admin Statistics
class AdminStatsOut(BaseModel):
    total_users: int
    active_users: int
    total_agents: int
    total_connections: int
    total_datasets: int
    total_runs: int
    runs_by_status: Dict[str, int]
    recent_activity: List[Dict[str, Any]]

# Admin System Info
class AdminSystemInfoOut(BaseModel):
    version: str
    environment: str
    database_status: str
    redis_status: str
    celery_status: str
    total_storage_mb: Optional[float]
    uptime_seconds: Optional[float]


# ==========================================
# SCHEMAS DE VALIDAÇÃO
# ==========================================

class ValidationRequest(BaseModel):
    """Schema para requisição de validação"""
    validation_type: str = "individual"  # individual, comparative
    validation_model: str = "gpt-4o-mini"
    auto_improve_question: bool = False
    num_runs_to_compare: int = 3  # Para validação comparativa: quantas últimas runs comparar

class ValidationResult(BaseModel):
    """Schema para resultado de validação"""
    overall_score: float
    question_clarity: float
    query_correctness: float
    response_accuracy: float
    suggestions: Union[str, List[str]] = []
    improved_question: Optional[str] = None
    inconsistencies_found: Optional[List[str]] = None
    observations: Optional[str] = None
    issues_found: Optional[List[str]] = None
    sql_query: Optional[str] = None
    response: Optional[str] = None

class ValidationResponse(BaseModel):
    """Schema para resposta de validação"""
    success: bool
    message: str
    validation_result: ValidationResult
    execution_time: float
    metadata: Dict[str, Any] = {}

