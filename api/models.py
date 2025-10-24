from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, Enum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import enum
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False

Base = declarative_base()

class UserRole(enum.Enum):
    """Enum para roles de usuário no sistema"""
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    nome = Column(String(255), nullable=False)
    ativo = Column(Boolean, default=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    empresas = relationship("UserEmpresa", back_populates="user")

class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("UserEmpresa", back_populates="empresa")

class UserEmpresa(Base):
    __tablename__ = "users_empresas"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), primary_key=True)
    role = Column(String(50), nullable=False, default="member")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="empresas")
    empresa = relationship("Empresa", back_populates="users")

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner_empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    nome = Column(String(255), nullable=False)
    tipo = Column(String(20), nullable=False)  # csv/postgres
    source_path = Column(Text, nullable=True)
    db_uri = Column(Text, nullable=True)
    schema_snapshot = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgentConnection(Base):
    __tablename__ = "agent_connections"
    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner_empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    tipo = Column(String(20), nullable=False)  # sqlite/duckdb/postgres/clickhouse
    db_uri = Column(Text, nullable=True)
    pg_dsn = Column(Text, nullable=True)  # alternativa explícita para Postgres
    ch_dsn = Column(Text, nullable=True)  # alternativa explícita para ClickHouse
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner_empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    nome = Column(String(255), nullable=False)
    connection_id = Column(Integer, ForeignKey("agent_connections.id"), nullable=False)
    selected_model = Column(String(100), nullable=False)
    top_k = Column(Integer, nullable=False, default=10)
    include_tables_key = Column(String(255), nullable=True, default="*")
    # Flags/configurações adicionais
    advanced_mode = Column(Boolean, nullable=False, default=False)
    processing_enabled = Column(Boolean, nullable=False, default=False)
    refinement_enabled = Column(Boolean, nullable=False, default=False)
    single_table_mode = Column(Boolean, nullable=False, default=False)
    selected_table = Column(String(255), nullable=True)
    # Novos campos para UI/UX
    description = Column(Text, nullable=True)  # Descrição do agente
    icon = Column(String(100), nullable=True, default="MessageSquare")  # Nome do ícone
    color = Column(String(100), nullable=True, default="from-blue-500 to-cyan-500")  # Gradiente de cor
    features = Column(Text, nullable=True)  # JSON array de features como string
    # Versionamento e timestamps
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    task_id = Column(String(100), nullable=True)
    sql_used = Column(Text, nullable=True)
    result_data = Column(Text, nullable=True)  # Resposta textual do agente SQL
    status = Column(String(20), nullable=False, default="queued")  # queued/running/success/failure/timeout
    execution_ms = Column(Integer, nullable=True)
    result_rows_count = Column(Integer, nullable=True)
    error_type = Column(String(100), nullable=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)  # NOVO: Link para histórico
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

# ==========================================
# MODELOS DO SISTEMA DE HISTÓRICO
# ==========================================

class ChatSession(Base):
    """Sessão de conversa entre usuário e agente"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    total_messages = Column(Integer, default=0)
    status = Column(String(20), default="active")  # active, archived
    context_summary = Column(Text, nullable=True)

    # Relacionamentos
    messages = relationship("Message", back_populates="chat_session", cascade="all, delete-orphan")
    runs = relationship("Run", backref="chat_session")
    summaries = relationship("ConversationSummary", back_populates="chat_session", cascade="all, delete-orphan")

class Message(Base):
    """Mensagem individual em uma conversa"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sequence_order = Column(Integer, nullable=False)
    message_metadata = Column(JSONB, nullable=True)

    # Relacionamentos
    chat_session = relationship("ChatSession", back_populates="messages")
    embedding = relationship("MessageEmbedding", back_populates="message", uselist=False, cascade="all, delete-orphan")

class MessageEmbedding(Base):
    """Embedding vetorial de uma mensagem para busca semântica"""
    __tablename__ = "message_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    model_version = Column(String(50), default="text-embedding-3-small")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Campo de embedding - usa pgvector se disponível, senão fallback para texto
    if PGVECTOR_AVAILABLE:
        embedding = Column(Vector(1536))  # OpenAI embedding dimension
    else:
        embedding_text = Column(Text)  # Fallback sem pgvector

    # Relacionamentos
    message = relationship("Message", back_populates="embedding")

class ConversationSummary(Base):
    """Resumo de conversa para contexto compacto"""
    __tablename__ = "conversation_summaries"

    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    up_to_message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    chat_session = relationship("ChatSession", back_populates="summaries")

