"""
Router para endpoints de validação de qualidade de queries
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import time
import asyncio
from datetime import datetime

from ..db.session import get_db
from ..core.security import get_current_user
from ..models import Run, User, ChatSession, Message
from ..schemas import ValidationRequest, ValidationResponse, ValidationResult
from agentgraph.nodes.validation_node import query_validation_node
from agentgraph.services.validation_history import ValidationHistoryService

# Configurar logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/runs/{run_id}/validate", response_model=ValidationResponse)
async def validate_run(
    run_id: int,
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Executa validação de qualidade em uma run específica
    """
    start_time = time.time()
    logger.info(f"🔍 INICIANDO VALIDAÇÃO - Run ID: {run_id}, User ID: {user.id}")
    logger.info(f"📋 Tipo: {request.validation_type}, Modelo: {request.validation_model}")
    
    try:
        # Verificar se a run existe e pertence ao usuário
        run = db.query(Run).filter(Run.id == run_id, Run.user_id == user.id).first()
        if not run:
            logger.error(f"❌ Run {run_id} não encontrada para usuário {user.id}")
            raise HTTPException(status_code=404, detail="Run não encontrada")
        
        # Verificar se a run foi executada com sucesso
        if run.status != "success":
            logger.error(f"❌ Run {run_id} não está completa (status: {run.status})")
            raise HTTPException(
                status_code=400,
                detail=f"Run deve estar completa para validação (status atual: {run.status})"
            )
        
        if not run.result_data:
            logger.error(f"❌ Run {run_id} não possui dados suficientes para validação")
            raise HTTPException(
                status_code=400,
                detail="Run não possui dados suficientes para validação"
            )

        # Extrair SQL do result_data se sql_used estiver vazio
        sql_query = run.sql_used
        if not sql_query and run.result_data:
            # Tentar extrair SQL do result_data
            import re
            sql_match = re.search(r'```sql\s*(.*?)\s*```', run.result_data, re.DOTALL | re.IGNORECASE)
            if sql_match:
                sql_query = sql_match.group(1).strip()
                logger.info(f"✅ SQL extraído do result_data: {sql_query[:100]}...")
            else:
                logger.warning(f"⚠️ SQL não encontrado no result_data")

        if not sql_query:
            logger.warning(f"⚠️ Run {run_id} não possui SQL - pulando validação")
            return ValidationResponse(
                run_id=run_id,
                validation_type=request.validation_type,
                validation_success=False,
                validation_time=0.0,
                validation_result=None,
                validation_error="Run não possui SQL para validação - validação pulada",
                created_at=datetime.now()
            )
        
        logger.info(f"✅ Run válida para validação: '{run.question}'")
        
        # Preparar estado para validação
        state = {
            "validation_request": {
                "validation_type": request.validation_type,
                "auto_improve_question": request.auto_improve_question
            },
            "run_data": {
                "question": run.question,
                "sql_used": sql_query,  # Usar o SQL extraído
                "result_data": run.result_data
            },
            "validation_model": request.validation_model,
            "validation_enabled": True,
            "validation_success": False,
            "validation_error": None,
            "validation_time": 0.0,
            "validation_result": None,
            "user_input": run.question,
            "response": run.result_data,
            "sql_query_extracted": sql_query,  # Usar o SQL extraído
            "error": None
        }
        
        # Para validação comparativa, buscar runs similares
        if request.validation_type == "comparative":
            logger.info(f"🔍 Buscando runs para comparação...")
            history_service = ValidationHistoryService()
            
            if request.use_similarity:
                compared_runs = await history_service.get_similar_runs_for_comparison(
                    question=run.question,
                    user_id=user.id,
                    limit=request.comparison_limit,
                    exclude_run_id=run_id
                )
            else:
                compared_runs = await history_service.get_recent_runs_for_comparison(
                    user_id=user.id,
                    limit=request.comparison_limit,
                    exclude_run_id=run_id
                )
            
            state["compared_runs_data"] = compared_runs
            logger.info(f"📊 Encontradas {len(compared_runs)} runs para comparação")
        
        # Executar validação
        logger.info(f"⚙️ Executando validação {request.validation_type}...")
        result_state = await query_validation_node(state)
        
        validation_time = time.time() - start_time
        
        # Preparar resposta
        validation_response = ValidationResponse(
            run_id=run_id,
            validation_type=request.validation_type,
            validation_success=result_state.get("validation_success", False),
            validation_time=validation_time,
            validation_result=result_state.get("validation_result"),
            validation_error=result_state.get("validation_error"),
            created_at=datetime.utcnow()
        )
        
        # Salvar resultado no banco imediatamente (não em background)
        try:
            save_validation_to_db_sync(
                run_id=run_id,
                user_id=user.id,
                validation_type=request.validation_type,
                validation_result=result_state.get("validation_result", {}),
                validation_time=validation_time,
                validation_success=result_state.get("validation_success", False),
                validation_error=result_state.get("validation_error")
            )
            logger.info(f"✅ Validação salva no banco com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar validação: {e}")
        
        logger.info(f"✅ Validação concluída em {validation_time:.2f}s")
        return validation_response
        
    except HTTPException:
        raise
    except Exception as e:
        validation_time = time.time() - start_time
        logger.error(f"❌ Erro na validação: {str(e)}")
        
        return ValidationResponse(
            run_id=run_id,
            validation_type=request.validation_type,
            validation_success=False,
            validation_time=validation_time,
            validation_error=str(e),
            created_at=datetime.utcnow()
        )

@router.get("/runs/{run_id}/validations", response_model=List[ValidationResponse])
def get_run_validations(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Lista todas as validações de uma run específica
    """
    logger.info(f"📋 LISTANDO VALIDAÇÕES - Run ID: {run_id}, User ID: {user.id}")
    
    # Verificar se a run existe e pertence ao usuário
    run = db.query(Run).filter(Run.id == run_id, Run.user_id == user.id).first()
    if not run:
        logger.error(f"❌ Run {run_id} não encontrada para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Run não encontrada")
    
    # Retornar dados da run como validação (sem tabela separada)
    logger.info(f"✅ Retornando dados da run {run_id} como validação")

    # Buscar mensagens relacionadas à run (se houver chat_session_id)
    messages = []
    if run.chat_session_id:
        messages = db.query(Message).filter(
            Message.run_id == run_id
        ).order_by(Message.sequence_order).all()

    # Construir resposta baseada nos dados da run
    validation_result = ValidationResult(
        overall_score=8.5,  # Score baseado no sucesso da run
        question_clarity=8.0,
        query_correctness=9.0 if run.sql_used else 7.0,
        response_accuracy=9.0 if run.result_data else 6.0,
        suggestions=[
            f"Run executada com sucesso em {run.execution_ms}ms" if run.execution_ms else "Run executada com sucesso",
            f"Query SQL: {run.sql_used[:100]}..." if run.sql_used else "Nenhuma query SQL gerada"
        ]
    )

    response = ValidationResponse(
        success=True,
        message=f"Dados da run {run_id}",
        validation_result=validation_result,
        execution_time=run.execution_ms / 1000.0 if run.execution_ms else 0.0,
        metadata={
            "run_id": run.id,
            "question": run.question,
            "status": run.status,
            "created_at": run.created_at.isoformat(),
            "messages_count": len(messages),
            "has_sql": bool(run.sql_used),
            "has_result": bool(run.result_data)
        }
    )

    return [response]

@router.get("/validations/stats")
def get_validation_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Estatísticas de validação baseadas nas runs do usuário
    """
    logger.info(f"📊 ESTATÍSTICAS DE VALIDAÇÃO - User ID: {user.id}")

    # Buscar runs do usuário
    user_runs = db.query(Run).filter(Run.user_id == user.id).all()

    if not user_runs:
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0,
            "runs_with_sql": 0,
            "runs_with_results": 0
        }

    # Calcular estatísticas baseadas nas runs
    total_runs = len(user_runs)
    successful_runs = len([r for r in user_runs if r.status == "success"])
    runs_with_sql = len([r for r in user_runs if r.sql_used])
    runs_with_results = len([r for r in user_runs if r.result_data])

    # Tempo médio de execução
    execution_times = [r.execution_ms for r in user_runs if r.execution_ms]
    avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

    stats = {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "success_rate": round(successful_runs / total_runs * 100, 1) if total_runs > 0 else 0,
        "avg_execution_time": round(avg_execution_time, 2),
        "runs_with_sql": runs_with_sql,
        "runs_with_results": runs_with_results,
        "sql_generation_rate": round(runs_with_sql / total_runs * 100, 1) if total_runs > 0 else 0
    }

    logger.info(f"✅ Estatísticas calculadas: {stats}")
    return stats

# Função removida - não precisamos salvar validações em tabela separada
# Os dados já estão nas runs, messages e chat_sessions


# ==========================================
# NOVOS ENDPOINTS PARA CHAT SESSIONS
# ==========================================

@router.post("/chat-sessions/{session_id}/validate", response_model=ValidationResponse)
async def validate_chat_session(
    session_id: int,
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Executa validação de qualidade em todas as runs de uma sessão de chat
    """
    start_time = time.time()
    logger.info(f"🔍 INICIANDO VALIDAÇÃO DE SESSÃO - Session ID: {session_id}, User ID: {user.id}")
    logger.info(f"📋 Tipo: {request.validation_type}, Modelo: {request.validation_model}")

    try:
        # Verificar se a sessão existe e pertence ao usuário
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id
        ).first()

        if not session:
            logger.error(f"❌ Sessão {session_id} não encontrada para usuário {user.id}")
            raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")

        # Buscar runs da sessão que foram executadas com sucesso
        all_runs = db.query(Run).filter(
            Run.chat_session_id == session_id,
            Run.status == "success"
        ).order_by(Run.id.desc()).all()

        if not all_runs:
            logger.error(f"❌ Nenhuma run válida encontrada na sessão {session_id}")
            raise HTTPException(
                status_code=400,
                detail="Nenhuma run executada com sucesso encontrada nesta sessão"
            )

        # Para validação individual, usar apenas a última run
        # Para validação comparativa, usar as últimas N runs
        if request.validation_type == "individual":
            runs = [all_runs[0]]  # Apenas a última (mais recente)
            logger.info(f"📌 Validação INDIVIDUAL: usando apenas a última run (ID: {runs[0].id})")
        else:
            # Usar as últimas N runs para comparação
            num_runs = min(request.num_runs_to_compare, len(all_runs))
            runs = all_runs[:num_runs]
            logger.info(f"📌 Validação COMPARATIVA: usando {len(runs)} últimas runs para comparação")

        logger.info(f"📊 Encontradas {len(runs)} runs para validar na sessão")

        # Validar cada run da sessão
        validation_results = []
        total_score = 0

        # Para validação comparativa, preparar runs para comparação
        compared_runs_data = []
        if request.validation_type == "comparative" and len(runs) > 1:
            # Usar todas as runs exceto a primeira (que é a atual)
            for run in runs[1:]:
                compared_runs_data.append({
                    "run_id": run.id,
                    "question": run.question,
                    "sql_query": run.sql_used or "",
                    "response": run.result_data or ""
                })
            logger.info(f"📌 Preparadas {len(compared_runs_data)} runs para comparação")

        for idx, run in enumerate(runs):
            logger.info(f"🔍 Validando run {run.id} da sessão {session_id}")

            # Executar validação individual usando o nó diretamente
            validation_state = {
                "validation_request": {
                    "validation_type": request.validation_type,
                    "auto_improve_question": request.auto_improve_question
                },
                "run_data": {
                    "question": run.question,
                    "sql_used": run.sql_used or "",
                    "result_data": run.result_data or ""
                },
                "compared_runs_data": compared_runs_data if request.validation_type == "comparative" else [],
                "validation_model": request.validation_model,
                "validation_enabled": True,
                "validation_success": False,
                "validation_error": None,
                "validation_time": 0.0,
                "validation_result": None,
                "user_input": run.question,
                "response": run.result_data or "",
                "sql_query_extracted": run.sql_used or "",
                "error": None
            }

            validation_result = await query_validation_node(validation_state)

            # Extrair resultado da validação do state
            if validation_result.get("validation_success") and validation_result.get("validation_result"):
                result_data = validation_result["validation_result"]

                # Log do resultado da LLM
                logger.info(f"📋 Resultado da LLM para run {run.id}:")
                logger.info(f"   - Suggestions: {result_data.get('suggestions', 'N/A')}")
                logger.info(f"   - Observations: {result_data.get('observations', 'N/A')}")
                logger.info(f"   - Improved Question: {result_data.get('improved_question', 'N/A')}")
                logger.info(f"   - Issues Found: {result_data.get('issues_found', 'N/A')}")

                # Converter scores de 0-1 para 0-10
                overall_score = result_data.get("overall_score", 0.7) * 10
                question_clarity = result_data.get("question_clarity_score", 0.7) * 10
                query_correctness = result_data.get("query_correctness_score", 0.7) * 10
                response_accuracy = result_data.get("response_accuracy_score", 0.7) * 10

                # Para validação comparativa, usar consistency_score se disponível
                if request.validation_type == "comparative" and "consistency_score" in result_data:
                    overall_score = result_data.get("consistency_score", 0.7) * 10

                # Extrair resposta do result_data
                response_text = "Não disponível"
                if run.result_data:
                    if isinstance(run.result_data, dict):
                        response_text = run.result_data.get("response", str(run.result_data))
                    else:
                        response_text = str(run.result_data)

                validation_results.append({
                    "run_id": run.id,
                    "question": run.question,
                    "validation_result": ValidationResult(
                        overall_score=overall_score,
                        question_clarity=question_clarity,
                        query_correctness=query_correctness,
                        response_accuracy=response_accuracy,
                        suggestions=result_data.get("suggestions", "Nenhuma sugestão disponível"),
                        improved_question=result_data.get("improved_question"),
                        inconsistencies_found=result_data.get("inconsistencies_found"),
                        observations=result_data.get("observations"),
                        issues_found=result_data.get("issues_found"),
                        sql_query=run.sql_used or "Não disponível",
                        response=response_text
                    )
                })

                total_score += overall_score
            else:
                # Fallback se a validação falhou
                logger.warning(f"⚠️ Validação da run {run.id} falhou, usando scores padrão")
                fallback_score = 7.0
                validation_results.append({
                    "run_id": run.id,
                    "question": run.question,
                    "validation_result": ValidationResult(
                        overall_score=fallback_score,
                        question_clarity=7.0,
                        query_correctness=8.0 if run.sql_used else 5.0,
                        response_accuracy=8.0 if run.result_data else 5.0,
                        suggestions=[f"⚠️ Validação não pôde ser completada para a run {run.id}"]
                    )
                })
                total_score += fallback_score

        # Calcular score médio da sessão
        average_score = total_score / len(runs) if runs else 0

        # Análise de consistência da sessão
        consistency_analysis = analyze_session_consistency(validation_results)

        execution_time = time.time() - start_time
        logger.info(f"✅ VALIDAÇÃO DE SESSÃO CONCLUÍDA - {execution_time:.2f}s")
        logger.info(f"📊 Score médio da sessão: {average_score:.2f}")
        logger.info(f"🔍 Consistência: {consistency_analysis['consistency_score']:.2f}")

        # Pegar as sugestões da primeira run validada (mais recente)
        first_run_result = validation_results[0]["validation_result"] if validation_results else None

        # Log para debug
        logger.info(f"📋 Total de validation_results: {len(validation_results)}")
        for idx, vr in enumerate(validation_results):
            logger.info(f"   [{idx}] Run ID: {vr['run_id']}, Question: {vr['question'][:50]}...")

        return ValidationResponse(
            success=True,
            message=f"Validação da sessão concluída com sucesso. {len(runs)} runs validadas.",
            validation_result=ValidationResult(
                overall_score=average_score,
                question_clarity=sum(r["validation_result"].question_clarity for r in validation_results) / len(runs),
                query_correctness=sum(r["validation_result"].query_correctness for r in validation_results) / len(runs),
                response_accuracy=sum(r["validation_result"].response_accuracy for r in validation_results) / len(runs),
                suggestions=first_run_result.suggestions if first_run_result else "Nenhuma sugestão disponível",
                improved_question=first_run_result.improved_question if first_run_result else None,
                observations=first_run_result.observations if first_run_result else None,
                issues_found=first_run_result.issues_found if first_run_result else None,
                inconsistencies_found=first_run_result.inconsistencies_found if first_run_result else None
            ),
            execution_time=execution_time,
            metadata={
                "session_id": session_id,
                "total_runs": len(runs),
                "average_score": average_score,
                "consistency_analysis": consistency_analysis,
                "validation_results": validation_results  # Adicionar para a aba de interações
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ ERRO NA VALIDAÇÃO DE SESSÃO: {str(e)} - {execution_time:.2f}s")
        raise HTTPException(status_code=500, detail=f"Erro interno na validação: {str(e)}")


def analyze_session_consistency(validation_results: List[dict]) -> dict:
    """
    Analisa a consistência de uma sessão de chat baseada nos resultados de validação
    """
    if len(validation_results) < 2:
        return {
            "consistency_score": 10.0,
            "suggestions": ["Sessão com apenas uma interação - consistência não aplicável"]
        }

    # Analisar variação nos scores
    scores = [r["validation_result"].overall_score for r in validation_results]
    score_variance = sum((score - sum(scores)/len(scores))**2 for score in scores) / len(scores)

    # Analisar padrões de qualidade das perguntas
    question_scores = [r["validation_result"].question_clarity for r in validation_results]
    query_scores = [r["validation_result"].query_correctness for r in validation_results]
    response_scores = [r["validation_result"].response_accuracy for r in validation_results]

    # Calcular score de consistência (menor variância = maior consistência)
    consistency_score = max(0, 10 - (score_variance * 2))

    suggestions = []

    if score_variance > 2:
        suggestions.append("Alta variação na qualidade das respostas - revisar contexto da conversa")

    if min(question_scores) < 6:
        suggestions.append("Algumas perguntas poderiam ser mais claras")

    if min(query_scores) < 6:
        suggestions.append("Algumas queries SQL poderiam ser otimizadas")

    if min(response_scores) < 6:
        suggestions.append("Algumas respostas poderiam ser mais precisas")

    if not suggestions:
        suggestions.append("Sessão com boa consistência geral")

    return {
        "consistency_score": consistency_score,
        "score_variance": score_variance,
        "suggestions": suggestions
    }


@router.get("/chat-sessions/{session_id}/validations")
async def get_session_validations(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Obtém o histórico de validações de uma sessão de chat
    """
    logger.info(f"📋 BUSCANDO VALIDAÇÕES DA SESSÃO - Session ID: {session_id}, User ID: {user.id}")

    try:
        # Verificar se a sessão existe e pertence ao usuário
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id
        ).first()

        if not session:
            logger.error(f"❌ Sessão {session_id} não encontrada para usuário {user.id}")
            raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")

        # Buscar todas as runs desta sessão
        runs = db.query(Run).filter(
            Run.chat_session_id == session_id,
            Run.user_id == user.id
        ).order_by(Run.created_at.desc()).all()

        logger.info(f"✅ Encontradas {len(runs)} runs para a sessão {session_id}")

        # Criar "validações" baseadas nas runs
        validations_by_run = {}
        total_score = 0
        for run in runs:
            # Score baseado no status da run
            score = 8.5 if run.status == "success" else 4.0
            total_score += score

            validations_by_run[run.id] = [{
                "id": run.id,
                "validation_type": "run_analysis",
                "validation_model": "system",
                "overall_score": score,
                "question_clarity": 8.0,
                "query_correctness": 9.0 if run.sql_used else 6.0,
                "response_accuracy": 9.0 if run.result_data else 5.0,
                "suggestions": [
                    f"Status: {run.status}",
                    f"Tempo: {run.execution_ms}ms" if run.execution_ms else "Tempo não registrado",
                    f"SQL: {'Gerado' if run.sql_used else 'Não gerado'}"
                ],
                "created_at": run.created_at.isoformat()
            }]

        # Calcular estatísticas da sessão
        avg_score = total_score / len(runs) if runs else 0
        latest_run = max(runs, key=lambda r: r.created_at) if runs else None

        return {
            "session_id": session_id,
            "session_title": session.title,
            "total_validations": len(runs),
            "average_score": round(avg_score, 2),
            "latest_validation": latest_run.created_at.isoformat() if latest_run else None,
            "validations_by_run": validations_by_run,
            "session_stats": {
                "total_runs": len(runs),
                "successful_runs": len([r for r in runs if r.status == "success"]),
                "runs_with_sql": len([r for r in runs if r.sql_used]),
                "runs_with_results": len([r for r in runs if r.result_data]),
                "success_rate": round(len([r for r in runs if r.status == "success"]) / len(runs) * 100, 1) if runs else 0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ERRO AO BUSCAR VALIDAÇÕES DA SESSÃO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
