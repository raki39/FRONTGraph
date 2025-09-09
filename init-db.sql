-- Script de inicialização do PostgreSQL
-- Cria extensão pgvector automaticamente

-- Conecta ao banco agentgraph
\c agentgraph;

-- Cria extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Verifica se a extensão foi criada
SELECT 'pgvector extension created successfully' as status, extname, extversion 
FROM pg_extension 
WHERE extname = 'vector';
