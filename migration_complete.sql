-- ============================================
-- MIGRATION COMPLETA - TODAS AS TABELAS
-- ============================================

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    role VARCHAR(50) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. EMPRESAS
CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. USERS_EMPRESAS
CREATE TABLE IF NOT EXISTS users_empresas (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    empresa_id INTEGER PRIMARY KEY REFERENCES empresas(id),
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. DATASETS
CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    owner_user_id INTEGER REFERENCES users(id),
    owner_empresa_id INTEGER REFERENCES empresas(id),
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    source_path TEXT,
    db_uri TEXT,
    schema_snapshot TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. AGENT_CONNECTIONS
CREATE TABLE IF NOT EXISTS agent_connections (
    id SERIAL PRIMARY KEY,
    owner_user_id INTEGER REFERENCES users(id),
    owner_empresa_id INTEGER REFERENCES empresas(id),
    tipo VARCHAR(20) NOT NULL,
    db_uri TEXT,
    pg_dsn TEXT,
    ch_dsn TEXT,
    mysql_dsn TEXT,
    oracle_dsn TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. AGENTS
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    owner_user_id INTEGER REFERENCES users(id),
    owner_empresa_id INTEGER REFERENCES empresas(id),
    nome VARCHAR(255) NOT NULL,
    connection_id INTEGER NOT NULL REFERENCES agent_connections(id),
    selected_model VARCHAR(100) NOT NULL,
    top_k INTEGER NOT NULL DEFAULT 10,
    include_tables_key VARCHAR(255) DEFAULT '*',
    advanced_mode BOOLEAN NOT NULL DEFAULT FALSE,
    processing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    refinement_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    single_table_mode BOOLEAN NOT NULL DEFAULT FALSE,
    selected_table VARCHAR(255),
    description TEXT,
    icon VARCHAR(100) DEFAULT 'MessageSquare',
    color VARCHAR(100) DEFAULT 'from-blue-500 to-cyan-500',
    features TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. CHAT_SESSIONS
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_messages INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    context_summary TEXT
);

-- 8. RUNS
CREATE TABLE IF NOT EXISTS runs (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    question TEXT NOT NULL,
    task_id VARCHAR(100),
    sql_used TEXT,
    result_data TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    execution_ms INTEGER,
    result_rows_count INTEGER,
    error_type VARCHAR(100),
    chat_session_id INTEGER REFERENCES chat_sessions(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. MESSAGES
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    chat_session_id INTEGER NOT NULL REFERENCES chat_sessions(id),
    run_id INTEGER REFERENCES runs(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sql_query TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sequence_order INTEGER NOT NULL,
    message_metadata JSONB
);

-- 10. MESSAGE_EMBEDDINGS
CREATE TABLE IF NOT EXISTS message_embeddings (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES messages(id),
    model_version VARCHAR(50) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    embedding_text TEXT
);

-- 11. CONVERSATION_SUMMARIES
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id SERIAL PRIMARY KEY,
    chat_session_id INTEGER NOT NULL REFERENCES chat_sessions(id),
    up_to_message_id INTEGER NOT NULL REFERENCES messages(id),
    summary TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 12. VALIDATION_INTERACTIONS
CREATE TABLE IF NOT EXISTS validation_interactions (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    validation_type VARCHAR(50) NOT NULL,
    original_query TEXT,
    suggested_query TEXT,
    observations TEXT,
    critical_issues TEXT,
    corrected_questions TEXT,
    validation_success BOOLEAN,
    validation_error TEXT,
    validation_time FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_agents_owner ON agents(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_agents_connection ON agents(connection_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_agent ON chat_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat_session ON messages(chat_session_id);
CREATE INDEX IF NOT EXISTS idx_messages_run ON messages(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_agent ON runs(agent_id);
CREATE INDEX IF NOT EXISTS idx_runs_user ON runs(user_id);
CREATE INDEX IF NOT EXISTS idx_runs_chat_session ON runs(chat_session_id);
CREATE INDEX IF NOT EXISTS idx_validation_run ON validation_interactions(run_id);

-- ============================================
-- FIM DA MIGRATION
-- ============================================

