from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr

# Auth
class UserCreate(BaseModel):
    nome: str
    email: EmailStr
    password: str

# Users / Empresas
class UserOut(BaseModel):
    id: int
    email: EmailStr
    nome: str
    ativo: bool
    created_at: datetime
    class Config:
        from_attributes = True

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

class AgentUpdate(BaseModel):
    selected_model: Optional[str] = None
    top_k: Optional[int] = None
    include_tables_key: Optional[str] = None
    advanced_mode: Optional[bool] = None
    processing_enabled: Optional[bool] = None
    refinement_enabled: Optional[bool] = None
    single_table_mode: Optional[bool] = None
    selected_table: Optional[str] = None

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
    version: int
    created_at: datetime
    updated_at: datetime
    connection: Optional[ConnectionOut] = None
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
        # Mapeia o campo do banco para o schema
        fields = {"embedding_model_version": "model_version"}

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

