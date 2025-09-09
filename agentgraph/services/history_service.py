"""
Serviço de histórico para busca semântica e gerenciamento de conversas
Funciona dentro do Worker Celery com acesso direto ao PostgreSQL
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class HistoryService:
    """Serviço para gerenciamento de histórico de conversas"""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Inicializa o serviço de histórico

        Args:
            db_session: Sessão do banco (opcional, cria uma nova se não fornecida)
        """
        self.db_session = db_session or self._create_worker_session()
        self.history_enabled = os.getenv("HISTORY_ENABLED", "true").lower() == "true"
        self.max_messages = int(os.getenv("HISTORY_MAX_MESSAGES", "15"))
        self.similarity_threshold = float(os.getenv("HISTORY_SIMILARITY_THRESHOLD", "0.75"))

        logger.info(f"[HISTORY_SERVICE] Inicializado - Enabled: {self.history_enabled}, Max: {self.max_messages}")

    def _create_worker_session(self) -> Session:
        """Cria sessão específica para Worker Celery"""
        try:
            database_url = os.getenv("DATABASE_URL") or os.getenv("PG_HOST", "postgres")

            if not database_url.startswith("postgresql"):
                # Constrói URL a partir das variáveis individuais
                host = os.getenv("PG_HOST", "postgres")
                port = os.getenv("PG_PORT", "5432")
                db = os.getenv("PG_DB", "agentgraph")
                user = os.getenv("PG_USER", "agent")
                password = os.getenv("PG_PASSWORD", "agent")
                database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

            engine = create_engine(
                database_url,
                pool_size=3,  # Pool menor para Worker
                max_overflow=5,
                pool_pre_ping=True
            )

            Session = sessionmaker(bind=engine)
            session = Session()

            # Testa conexão
            session.execute(text("SELECT 1"))
            logger.info("[HISTORY_SERVICE] Conexão com PostgreSQL estabelecida")

            return session

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro ao conectar ao banco: {e}")
            raise

    def is_enabled(self) -> bool:
        """Verifica se o sistema de histórico está habilitado"""
        return self.history_enabled

    def get_or_create_chat_session(self, user_id: int, agent_id: int, title: str = None) -> int:
        """
        Obtém ou cria uma sessão de chat

        Args:
            user_id: ID do usuário
            agent_id: ID do agente
            title: Título da sessão (opcional)

        Returns:
            ID da sessão de chat
        """
        try:
            if not self.history_enabled:
                return None

            # Busca sessão ativa recente (últimas 24h)
            recent_session = self.db_session.execute(text("""
                SELECT id FROM chat_sessions
                WHERE user_id = :user_id
                AND agent_id = :agent_id
                AND status = 'active'
                AND last_activity > NOW() - INTERVAL '24 hours'
                ORDER BY last_activity DESC
                LIMIT 1
            """), {
                "user_id": user_id,
                "agent_id": agent_id
            }).fetchone()

            if recent_session:
                # Atualiza última atividade
                self.db_session.execute(text("""
                    UPDATE chat_sessions
                    SET last_activity = NOW()
                    WHERE id = :session_id
                """), {"session_id": recent_session[0]})
                self.db_session.commit()

                logger.info(f"[HISTORY_SERVICE] Sessão existente reutilizada: {recent_session[0]}")
                return recent_session[0]

            # Cria nova sessão
            if not title:
                title = f"Conversa {datetime.now().strftime('%d/%m %H:%M')}"

            result = self.db_session.execute(text("""
                INSERT INTO chat_sessions (user_id, agent_id, title, created_at, last_activity, total_messages, status)
                VALUES (:user_id, :agent_id, :title, NOW(), NOW(), 0, 'active')
                RETURNING id
            """), {
                "user_id": user_id,
                "agent_id": agent_id,
                "title": title
            })

            session_id = result.fetchone()[0]
            self.db_session.commit()

            logger.info(f"[HISTORY_SERVICE] Nova sessão criada: {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro ao obter/criar sessão: {e}")
            self.db_session.rollback()
            return None

    def get_relevant_history(self, user_id: int, agent_id: int, query_text: str,
                           chat_session_id: int = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        Busca histórico relevante usando busca semântica e recência

        Args:
            user_id: ID do usuário
            agent_id: ID do agente
            query_text: Texto da query atual
            chat_session_id: ID da sessão atual (opcional)
            limit: Limite de mensagens (opcional)

        Returns:
            Lista de mensagens relevantes formatadas
        """
        try:
            if not self.history_enabled:
                return []

            limit = limit or self.max_messages
            relevant_messages = []

            # 1. Busca mensagens recentes da sessão atual
            if chat_session_id:
                recent_messages = self._get_recent_session_messages(chat_session_id, limit=5)
                relevant_messages.extend(recent_messages)

            # 2. Busca mensagens similares via embedding (se pgvector disponível)
            try:
                similar_messages = self._get_similar_messages(user_id, agent_id, query_text, limit=10, chat_session_id=chat_session_id)
                relevant_messages.extend(similar_messages)
            except Exception as e:
                logger.warning(f"[HISTORY_SERVICE] Busca semântica falhou, usando busca textual: {e}")
                # IMPORTANTE: Rollback da transação antes do fallback
                self.db_session.rollback()
                # Fallback para busca textual simples (restringe à sessão atual)
                text_messages = self._get_text_similar_messages(user_id, agent_id, query_text, limit=5, chat_session_id=chat_session_id)
                relevant_messages.extend(text_messages)

            # 2.5. Garante inclusão da ÚLTIMA INTERAÇÃO (pergunta + resposta)
            try:
                if chat_session_id:
                    last_pair = self.get_last_interaction(chat_session_id)
                    if last_pair:
                        user_msg, assistant_msg = last_pair
                        # Marca fonte e score alto para priorizar a última interação
                        user_msg.update({"source": "last_interaction", "relevance_score": 1.1})
                        assistant_msg.update({"source": "last_interaction", "relevance_score": 1.05})
                        relevant_messages.extend([user_msg, assistant_msg])
                        logger.info("[HISTORY_SERVICE] Última interação adicionada ao conjunto de histórico")
            except Exception as e:
                logger.warning(f"[HISTORY_SERVICE] Falha ao garantir última interação: {e}")

            # 3. Remove duplicatas e ordena por relevância
            unique_messages = self._deduplicate_and_rank(relevant_messages, limit)

            logger.info(f"[HISTORY_SERVICE] Histórico recuperado: {len(unique_messages)} mensagens")
            return unique_messages

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro ao buscar histórico: {e}")
            return []

    def _get_recent_session_messages(self, chat_session_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca mensagens recentes da sessão atual"""
        try:
            result = self.db_session.execute(text("""
                SELECT m.role, m.content, m.sql_query, m.created_at, m.sequence_order
                FROM messages m
                WHERE m.chat_session_id = :session_id
                ORDER BY m.sequence_order DESC
                LIMIT :limit
            """), {
                "session_id": chat_session_id,
                "limit": limit
            })

            messages = []
            for row in result:
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "sql_query": row[2],
                    "created_at": row[3],
                    "sequence_order": row[4],
                    "source": "recent_session",
                    "relevance_score": 1.0  # Máxima relevância para mensagens da sessão
                })

            return messages

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro ao buscar mensagens recentes: {e}")
            return []
    def get_last_interaction(self, chat_session_id: int) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Retorna a última interação (pergunta do usuário e resposta do assistente) da sessão.

        Args:
            chat_session_id: ID da sessão de chat

        Returns:
            Tupla (user_message, assistant_message) ou None se não houver par completo.
        """
        try:
            # Busca a última mensagem de usuário pela ordem de sequência
            result_user = self.db_session.execute(text(
                """
                SELECT id, role, content, sql_query, created_at, sequence_order
                FROM messages
                WHERE chat_session_id = :session_id AND role = 'user'
                ORDER BY sequence_order DESC
                LIMIT 1
                """
            ), {"session_id": chat_session_id})
            user_row = result_user.fetchone()
            if not user_row:
                return None

            user_msg = {
                "id": user_row[0],
                "role": user_row[1],
                "content": user_row[2],
                "sql_query": user_row[3],
                "created_at": user_row[4],
                "sequence_order": user_row[5],
            }

            # Busca a próxima mensagem do assistente (imediatamente após a do usuário)
            result_assistant = self.db_session.execute(text(
                """
                SELECT id, role, content, sql_query, created_at, sequence_order
                FROM messages
                WHERE chat_session_id = :session_id AND role = 'assistant' AND sequence_order = :seq
                ORDER BY sequence_order ASC
                LIMIT 1
                """
            ), {"session_id": chat_session_id, "seq": user_msg["sequence_order"] + 1})
            assistant_row = result_assistant.fetchone()

            if not assistant_row:
                # Fallback: pega a resposta de assistente mais recente após a mensagem do usuário
                result_assistant = self.db_session.execute(text(
                    """
                    SELECT id, role, content, sql_query, created_at, sequence_order
                    FROM messages
                    WHERE chat_session_id = :session_id AND role = 'assistant' AND created_at >= :after
                    ORDER BY created_at ASC
                    LIMIT 1
                    """
                ), {"session_id": chat_session_id, "after": user_msg["created_at"]})
                assistant_row = result_assistant.fetchone()

            if not assistant_row:
                return None

            assistant_msg = {
                "id": assistant_row[0],
                "role": assistant_row[1],
                "content": assistant_row[2],
                "sql_query": assistant_row[3],
                "created_at": assistant_row[4],
                "sequence_order": assistant_row[5],
            }

            return (user_msg, assistant_msg)

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro ao obter última interação: {e}")
            self.db_session.rollback()
            return None


    def _get_similar_messages(self, user_id: int, agent_id: int, query_text: str, limit: int = 10, chat_session_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Busca mensagens similares via embedding (requer pgvector)"""
        try:
            # Primeiro, gera embedding da query atual
            from agentgraph.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.get_embedding(query_text)

            # Busca mensagens similares - SOLUÇÃO CORRETA: usar exec_driver_sql
            from pgvector.psycopg2 import register_vector

            # Prepara query com paramstyle nativo do psycopg2 (%s)
            sql = """
                SELECT m.role, m.content, m.sql_query, m.created_at,
                       (me.embedding <-> %s::vector) AS distance
                FROM messages m
                JOIN message_embeddings me ON m.id = me.message_id
                JOIN chat_sessions cs ON m.chat_session_id = cs.id
                WHERE cs.user_id = %s
                  AND cs.agent_id = %s
                  AND m.role = 'user'
                  AND cs.id = %s
                  AND (me.embedding <-> %s::vector) < %s
                ORDER BY distance ASC
                LIMIT %s
            """

            # Parâmetros na ordem correta (inclui chat_session_id para restringir à sessão atual)
            params = (
                query_embedding,
                user_id,
                agent_id,
                chat_session_id if chat_session_id else -1,
                query_embedding,
                1.0 - self.similarity_threshold,
                limit
            )

            # Executa usando engine do SQLAlchemy com paramstyle nativo
            engine = self.db_session.get_bind()
            with engine.begin() as conn:
                # Registra pgvector (necessário para ::vector)
                # Obtém conexão raw do psycopg2
                raw_conn = conn.connection.dbapi_connection
                register_vector(raw_conn)

                # Executa query com paramstyle nativo
                result = conn.exec_driver_sql(sql, params)
                rows = result.mappings().all()

            messages = []
            for row in rows:
                similarity_score = 1.0 - row['distance']  # Converte distância para similaridade
                messages.append({
                    "role": row['role'],
                    "content": row['content'],
                    "sql_query": row['sql_query'],
                    "created_at": row['created_at'],
                    "source": "semantic_search",
                    "relevance_score": similarity_score
                })

            return messages

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro na busca semântica: {e}")
            raise

    def _get_similar_messages_with_embedding(self, user_id: int, agent_id: int, query_embedding: list, limit: int = 10):
        """
        Busca mensagens similares usando embedding direto (para testes)
        """
        try:
            from pgvector.psycopg2 import register_vector

            # Prepara query com paramstyle nativo do psycopg2 (%s)
            sql = """
                SELECT m.role, m.content, m.sql_query, m.created_at,
                       (me.embedding <-> %s::vector) AS distance
                FROM messages m
                JOIN message_embeddings me ON m.id = me.message_id
                JOIN chat_sessions cs ON m.chat_session_id = cs.id
                WHERE cs.user_id = %s
                  AND cs.agent_id = %s
                  AND m.role = 'user'
                  AND (me.embedding <-> %s::vector) < %s
                ORDER BY distance ASC
                LIMIT %s
            """

            # Parâmetros na ordem correta
            params = (
                query_embedding,  # Lista de floats
                user_id,
                agent_id,
                query_embedding,  # Lista de floats
                1.0 - self.similarity_threshold,
                limit
            )

            # Executa usando engine do SQLAlchemy com paramstyle nativo
            engine = self.db_session.get_bind()
            with engine.begin() as conn:
                # Registra pgvector (necessário para ::vector)
                raw_conn = conn.connection.dbapi_connection
                register_vector(raw_conn)

                # Executa query com paramstyle nativo
                result = conn.exec_driver_sql(sql, params)
                rows = result.mappings().all()

            messages = []
            for row in rows:
                similarity_score = 1.0 - row['distance']  # Converte distância para similaridade
                messages.append({
                    "role": row['role'],
                    "content": row['content'],
                    "sql_query": row['sql_query'],
                    "created_at": row['created_at'],
                    "source": "semantic_search",
                    "relevance_score": similarity_score
                })

            return messages

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro na busca semântica com embedding: {e}")
            return []

    def _get_text_similar_messages(self, user_id: int, agent_id: int, query_text: str, limit: int = 5, chat_session_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Busca mensagens similares via texto (fallback)"""
        try:
            # Busca textual simples usando ILIKE
            keywords = query_text.lower().split()[:3]  # Primeiras 3 palavras

            result = self.db_session.execute(text("""
                SELECT m.role, m.content, m.sql_query, m.created_at
                FROM messages m
                JOIN chat_sessions cs ON m.chat_session_id = cs.id
                WHERE cs.user_id = :user_id
                AND cs.agent_id = :agent_id
                AND m.role = 'user'
                AND cs.id = :session_id
                AND (
                    LOWER(m.content) LIKE :keyword1 OR
                    LOWER(m.content) LIKE :keyword2 OR
                    LOWER(m.content) LIKE :keyword3
                )
                ORDER BY m.created_at DESC
                LIMIT :limit
            """), {
                "user_id": user_id,
                "agent_id": agent_id,
                "session_id": chat_session_id if chat_session_id else -1,
                "keyword1": f"%{keywords[0] if len(keywords) > 0 else ''}%",
                "keyword2": f"%{keywords[1] if len(keywords) > 1 else ''}%",
                "keyword3": f"%{keywords[2] if len(keywords) > 2 else ''}%",
                "limit": limit
            })

            messages = []
            for row in result:
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "sql_query": row[2],
                    "created_at": row[3],
                    "source": "text_search",
                    "relevance_score": 0.5  # Score médio para busca textual
                })

            return messages

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro na busca textual: {e}")
            return []

    def _deduplicate_and_rank(self, messages: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Remove duplicatas e ordena por relevância"""
        try:
            # Remove duplicatas baseado no conteúdo
            seen_content = set()
            unique_messages = []

            for msg in messages:
                content_key = f"{msg['role']}:{msg['content'][:100]}"  # Primeiros 100 chars
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    unique_messages.append(msg)

            # Ordena por relevância (score + recência)
            unique_messages.sort(key=lambda x: (
                x.get('relevance_score', 0),
                x.get('created_at', datetime.min)
            ), reverse=True)

            return unique_messages[:limit]

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro ao deduplificar: {e}")
            return messages[:limit]

    def format_history_for_context(self, messages: List[Dict[str, Any]]) -> str:
        """
        Formata historico para inclusao no contexto do ProcessingAgent e AgentSQL,
        em duas secoes:
        - ULTIMA_INTERACAO: ultimo par pergunta->resposta (e SQL se houver)
        - HISTORICO_RELEVANTE: pares relevantes anteriores

        Cada linha segue exatamente o formato:
        [PERGUNTA] <texto> -> [RESPOSTA] <texto> -> [QUERYSQL] <sql>
        (omitimos [QUERYSQL] se nao houver)
        """
        if not messages:
            return ""

        try:
            import re

            def sanitize(text: str) -> str:
                if not isinstance(text, str):
                    return ""
                # Remove linhas indesejadas e colapsa quebras/espacos
                lines = []
                for ln in (text.replace("\r", "\n").split("\n")):
                    ls = ln.strip()
                    if not ls:
                        continue
                    low = ls.lower()
                    if ls.startswith("```"):
                        continue
                    if "query sql utilizada" in low:
                        continue
                    if ls.startswith("⏱") or ls.startswith("---"):
                        continue
                    lines.append(ls)
                s = " ".join(lines)
                s = re.sub(r"\s+", " ", s)
                return s.strip()

            def extract_sql_and_strip(text: str) -> Tuple[str, str]:
                """Extrai a query SQL do texto e retorna (texto_sem_sql, sql).
                Regras simples: prioriza bloco ```sql```; senao, primeira ocorrencia de SELECT/WITH ate ';'."""
                if not isinstance(text, str) or not text.strip():
                    return "", ""
                raw = text
                # 1) bloco ```sql ... ```
                m = re.search(r"```sql\s*(.*?)\s*```", raw, re.IGNORECASE | re.DOTALL)
                if not m:
                    m = re.search(r"```\s*(SELECT|WITH)(.*?)\s*```", raw, re.IGNORECASE | re.DOTALL)
                    if m:
                        # recompoe para ter a query completa
                        raw_query = (m.group(1) + (m.group(2) or "")).strip()
                        sql = raw_query
                        raw_wo = raw.replace(m.group(0), " ")
                        return raw_wo, sql
                if m:
                    sql = m.group(1).strip()
                    raw_wo = raw.replace(m.group(0), " ")
                    return raw_wo, sql
                # 2) SELECT/WITH ate ponto e virgula
                m2 = re.search(r"(?is)(SELECT\s+.*?;)", raw)
                if not m2:
                    m2 = re.search(r"(?is)(WITH\s+.*?;)", raw)
                if m2:
                    sql = m2.group(1).strip()
                    raw_wo = raw.replace(m2.group(1), " ")
                    return raw_wo, sql
                # 3) SELECT/WITH sem ';' (pega do match ate fim)
                m3 = re.search(r"(?is)(SELECT\s+.+)$", raw)
                if not m3:
                    m3 = re.search(r"(?is)(WITH\s+.+)$", raw)
                if m3:
                    sql = m3.group(1).strip()
                    raw_wo = raw.replace(m3.group(1), " ")
                    return raw_wo, sql
                return raw, ""


            # Ordena por created_at e sequence_order (quando existir) para pareamento deterministico
            def order_key(m: Dict[str, Any]):
                created = m.get('created_at') or datetime.min
                seq = m.get('sequence_order') if m.get('sequence_order') is not None else 0
                return (created, seq)
            ordered_all = sorted(messages, key=order_key)

            # Construcao de pares em toda a lista (user -> proximo assistant posterior)
            pairs_all: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]] = []
            pending_user = None
            for m in ordered_all:
                role = m.get('role')
                if role == 'user':
                    pending_user = m
                elif role == 'assistant' and pending_user is not None:
                    pairs_all.append((pending_user, m))
                    pending_user = None

            # Identifica a ultima interacao: preferir mensagens com source=last_interaction; senao, o ultimo par cronologico
            last_pair: Optional[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]] = None
            last_user_candidates = [m for m in messages if m.get('source') == 'last_interaction' and m.get('role') == 'user']
            last_asst_candidates = [m for m in messages if m.get('source') == 'last_interaction' and m.get('role') == 'assistant']
            if last_user_candidates or last_asst_candidates:
                u = max(last_user_candidates, key=order_key) if last_user_candidates else None
                a = max(last_asst_candidates, key=order_key) if last_asst_candidates else None
                if u or a:
                    last_pair = (u, a)
            if last_pair is None and pairs_all:
                last_pair = pairs_all[-1]

            def pair_score(u: Optional[Dict[str, Any]], a: Optional[Dict[str, Any]]) -> float:
                us = float((u or {}).get('relevance_score', 0.0))
                as_ = float((a or {}).get('relevance_score', 0.0))
                return max(us, as_)

            # Pairs relevantes: todos os pares exceto o da ultima interacao, ordenados por score desc
            relevant_pairs: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]] = []
            for u, a in pairs_all:
                if last_pair and u == last_pair[0] and a == last_pair[1]:
                    continue
                relevant_pairs.append((u, a))
            relevant_pairs.sort(key=lambda p: pair_score(p[0], p[1]), reverse=True)

            def fmt_pair(u: Optional[Dict[str, Any]], a: Optional[Dict[str, Any]]):
                if not u and not a:
                    return None
                # Extrai SQL do conteudo do assistente, se nao houver no campo dedicado
                raw_ans = (a or {}).get('content')
                raw_ans = raw_ans if isinstance(raw_ans, str) else ""
                raw_wo_sql, sql_from_content = extract_sql_and_strip(raw_ans)

                q = sanitize((u or {}).get('content'))
                atext = sanitize(raw_wo_sql if raw_wo_sql else raw_ans)
                sqlq_raw = (a or {}).get('sql_query')
                sqlq = sanitize(sqlq_raw) if isinstance(sqlq_raw, str) and sqlq_raw.strip() else sanitize(sql_from_content)
                if not q and not atext and not sqlq:
                    return None
                parts = []
                if q:
                    parts.append(f"[PERGUNTA] {q}")
                if atext:
                    parts.append(f"[RESPOSTA] {atext}")
                if sqlq:
                    parts.append(f"[QUERYSQL] {sqlq}")
                return " -> ".join(parts)

            lines: List[str] = []

            # Secao 1: Ultima interacao
            if last_pair:
                lp = fmt_pair(last_pair[0], last_pair[1])
                if lp:
                    lines.append("ULTIMA_INTERACAO:")
                    lines.append(lp)

            # Secao 2: Historico relevante
            rel_lines: List[str] = []
            for up, ap in relevant_pairs:
                ln = fmt_pair(up, ap)
                if not ln:
                    continue
                # Evita duplicar a ultima interacao
                if last_pair and up == last_pair[0] and ap == last_pair[1]:
                    continue
                rel_lines.append(ln)

            # Fallback: se nao houver pares relevantes, tenta recompor pergunta para respostas soltas
            if not rel_lines:
                singles: List[str] = []

                def in_last_pair(m: Dict[str, Any]) -> bool:
                    return bool(last_pair and (m is last_pair[0] or m is last_pair[1]))

                # Indexa a ultima pergunta anterior a cada resposta (por tempo)
                users_before: List[Dict[str, Any]] = [m for m in ordered_all if m.get('role') == 'user']

                for m in ordered_all:
                    if in_last_pair(m):
                        continue
                    role = m.get('role')
                    content_raw = m.get('content') if isinstance(m.get('content'), str) else ""
                    content_wo_sql, sql_from_msg = extract_sql_and_strip(content_raw)
                    content = sanitize(content_wo_sql if content_wo_sql else content_raw)
                    sql_here = sanitize(sql_from_msg)

                    if role == 'assistant':
                        # Busca a ultima pergunta anterior a esta resposta
                        prev_q = ""
                        m_created = m.get('created_at') or datetime.min
                        m_seq = m.get('sequence_order') if m.get('sequence_order') is not None else -1
                        for u in reversed(users_before):
                            u_created = u.get('created_at') or datetime.min
                            u_seq = u.get('sequence_order') if u.get('sequence_order') is not None else -1
                            if (u_created, u_seq) <= (m_created, m_seq):
                                prev_q = sanitize(u.get('content'))
                                break
                        parts = []
                        if prev_q:
                            parts.append(f"[PERGUNTA] {prev_q}")
                        if content:
                            parts.append(f"[RESPOSTA] {content}")
                        if sql_here:
                            parts.append(f"[QUERYSQL] {sql_here}")
                        if parts:
                            singles.append(" -> ".join(parts))
                    elif role == 'user':
                        # Se for apenas pergunta sem resposta associada, ainda adiciona a pergunta
                        if content:
                            singles.append(f"[PERGUNTA] {content}")

                rel_lines = singles

            if rel_lines:
                if lines:
                    lines.append("")
                lines.append("HISTORICO_RELEVANTE:")
                lines.extend(rel_lines)

            formatted_context = "\n".join(lines)
            logger.info(f"[HISTORY_SERVICE] Contexto formatado: {len(formatted_context)} chars")
            return formatted_context

        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro ao formatar contexto: {e}")
            return ""

    def close(self):
        """Fecha a sessão do banco"""
        try:
            if self.db_session:
                self.db_session.close()
                logger.info("[HISTORY_SERVICE] Sessão do banco fechada")
        except Exception as e:
            logger.error(f"[HISTORY_SERVICE] Erro ao fechar sessão: {e}")


def get_history_service(db_session: Optional[Session] = None) -> HistoryService:
    """
    Factory function para obter instância do HistoryService

    Args:
        db_session: Sessão do banco (opcional)

    Returns:
        Instância do HistoryService
    """
    return HistoryService(db_session)
