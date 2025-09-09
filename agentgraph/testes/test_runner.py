#!/usr/bin/env python3
"""
Sistema de execução massiva de testes com paralelismo
"""
import asyncio
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import sys
import os

# Define variável de ambiente para indicar modo de teste
os.environ["TESTING_MODE"] = "true"

# Adiciona path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graphs.main_graph import AgentGraphManager
from testes.test_validator import TestValidator
from utils.config import AVAILABLE_MODELS

class MassiveTestRunner:
    """
    Executor de testes massivos com paralelismo otimizado
    """
    
    def __init__(self, max_workers: int = 5):
        """
        Inicializa o test runner

        Args:
            max_workers: Número máximo de workers paralelos
        """
        self.max_workers = max_workers
        logging.info(f"🔧 MassiveTestRunner inicializado com {max_workers} workers paralelos")
        self.validator = TestValidator()
        self.results = {
            'session_info': {},
            'group_results': [],
            'individual_results': [],
            'summary': {}
        }
        self.status = {
            'current_status': 'idle',
            'progress': 0,
            'current_group': None,
            'completed_tests': 0,
            'total_tests': 0,
            'start_time': None,
            'estimated_remaining': None,
            'errors': [],
            'current_test': None,
            'running_tests': {},  # {thread_id: {start_time, group_id, iteration, task, future}}
            'cancelled_tests': set(),
            'timeout_tests': set()
        }
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._test_timeout = 360  # 1.5 minutos timeout por teste
        self._active_futures = {}  # {thread_id: future} para cancelamento real
        self._cancel_events = {}  # {thread_id: Event} para cancelamento individual
        
    async def run_test_session(self, session: Dict[str, Any], validation_method: str = 'llm', expected_content: str = None) -> Dict[str, Any]:
        """
        Executa sessão completa de testes
        
        Args:
            session: Dados da sessão de teste
            validation_method: Método de validação ('llm' ou 'keyword')
            expected_content: Conteúdo esperado (para validação keyword)
            
        Returns:
            Resultados completos dos testes
        """
        try:
            print(f"\n🔥 MASSIVE TEST RUNNER INICIADO")
            print(f"📋 Sessão: {session['id']}")
            print(f"❓ Pergunta: {session['question']}")
            print(f"👥 Grupos: {len(session['groups'])}")

            total_tests = sum(group['iterations'] for group in session['groups'])
            print(f"🔢 Total de testes: {total_tests}")
            print(f"⚡ Workers paralelos: {self.max_workers}")
            print("-" * 60)

            logging.info(f"🚀 Iniciando sessão de testes: {session['id']}")

            # Atualiza status
            with self._lock:
                self.status.update({
                    'current_status': 'initializing',
                    'start_time': time.time(),
                    'total_tests': total_tests
                })
            
            # Armazena informações da sessão
            self.results['session_info'] = {
                'id': session['id'],
                'question': session['question'],
                'validation_method': validation_method,
                'expected_content': expected_content,
                'total_groups': len(session['groups']),
                'total_tests': self.status['total_tests'],
                'started_at': datetime.now().isoformat()
            }
            
            # Executa grupos de teste
            group_results = []
            
            for group_idx, group in enumerate(session['groups']):
                # Verifica se todos os testes foram cancelados
                with self._lock:
                    if len(self.status['cancelled_tests']) >= self.status['total_tests']:
                        print(f"🚫 Todos os testes foram cancelados - finalizando sessão")
                        logging.info("Todos os testes foram cancelados - finalizando sessão")
                        break

                print(f"\n📊 EXECUTANDO GRUPO {group_idx + 1}/{len(session['groups'])}")
                print(f"🤖 Modelo SQL: {group['sql_model_name']}")
                print(f"🔄 Processing Agent: {'✅ ' + group['processing_model_name'] if group['processing_enabled'] else '❌ Desativado'}")
                print(f"🔧 Question Refinement: {'✅ GPT-4o' if group.get('question_refinement_enabled', False) else '❌ Desativado'}")
                print(f"🔢 Iterações: {group['iterations']}")
                print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")

                logging.info(f"📊 Executando grupo {group_idx + 1}/{len(session['groups'])}: {group['sql_model_name']}")

                with self._lock:
                    self.status['current_group'] = group_idx + 1
                    self.status['current_status'] = 'running_group'

                # Executa testes do grupo em paralelo
                group_result = await self._run_group_tests(
                    session['question'],
                    group,
                    validation_method,
                    expected_content
                )
                
                group_results.append(group_result)
                self.results['group_results'] = group_results
                
                # Atualiza progresso
                completed_so_far = sum(len(gr['individual_results']) for gr in group_results)
                with self._lock:
                    self.status['completed_tests'] = completed_so_far
                    self.status['progress'] = (completed_so_far / self.status['total_tests']) * 100
                    
                    # Estima tempo restante
                    if self.status['start_time']:
                        elapsed = time.time() - self.status['start_time']
                        if completed_so_far > 0:
                            avg_time_per_test = elapsed / completed_so_far
                            remaining_tests = self.status['total_tests'] - completed_so_far
                            self.status['estimated_remaining'] = avg_time_per_test * remaining_tests
            
            # Gera resumo final
            self._generate_summary()

            with self._lock:
                self.status['current_status'] = 'completed'
                self.status['progress'] = 100
                self.status['end_time'] = time.time()
                total_time = self.status['end_time'] - self.status['start_time']
                self.status['total_execution_time'] = total_time

            logging.info(f"✅ Sessão de testes concluída: {session['id']}")
            logging.info(f"📊 Resumo final: {self.status['total_tests']} testes em {total_time:.2f}s")
            logging.info(f"🎯 Taxa geral de sucesso: {self.results['summary'].get('overall_success_rate', 0)}%")

            return self.results
            
        except Exception as e:
            logging.error(f"❌ Erro na sessão de testes: {e}")
            with self._lock:
                self.status['current_status'] = 'error'
                self.status['errors'].append(str(e))
            raise
    
    async def _run_group_tests(self, question: str, group: Dict[str, Any], validation_method: str, expected_content: str) -> Dict[str, Any]:
        """
        Executa testes de um grupo específico com paralelismo REAL

        Args:
            question: Pergunta do teste
            group: Configuração do grupo
            validation_method: Método de validação
            expected_content: Conteúdo esperado

        Returns:
            Resultados do grupo
        """
        print(f"🔄 Executando {group['iterations']} testes em paralelo (máx {self.max_workers} simultâneos)")
        logging.info(f"🔄 Executando {group['iterations']} testes para grupo {group['id']}")

        # Cria semáforo para controle de concorrência
        semaphore = asyncio.Semaphore(self.max_workers)

        print(f"⚡ Iniciando {group['iterations']} testes com paralelismo REAL...")
        start_time = time.time()

        # VOLTA AO PARALELISMO ORIGINAL QUE FUNCIONAVA
        print(f"🚀 Executando {group['iterations']} testes em paralelo (máx {self.max_workers} simultâneos)")

        # Cria tasks para execução paralela (COMO ESTAVA ANTES)
        semaphore = asyncio.Semaphore(self.max_workers)
        tasks = []

        print(f"⚡ Criando {group['iterations']} tasks paralelas...")
        for iteration in range(group['iterations']):
            # Verifica se todos os testes foram cancelados antes de criar mais tasks
            with self._lock:
                if len(self.status['cancelled_tests']) >= self.status['total_tests']:
                    print(f"🚫 Cancelamento detectado - parando criação de tasks")
                    break

            task = self._run_single_test(
                semaphore,
                question,
                group,
                iteration + 1,
                validation_method,
                expected_content
            )
            tasks.append(task)

        print(f"🚀 Executando {len(tasks)} testes em paralelo...")
        start_time = time.time()

        # Executa testes em paralelo com verificação de cancelamento
        try:
            individual_results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            print(f"🚫 Grupo {group['id']} cancelado durante execução")
            # Coleta resultados dos testes que já terminaram
            individual_results = []
            for task in tasks:
                if task.done() and not task.cancelled():
                    try:
                        result = task.result()
                        individual_results.append(result)
                    except Exception as e:
                        individual_results.append(e)
                else:
                    # Cria resultado cancelado para testes não terminados
                    cancelled_result = {
                        'group_id': group['id'],
                        'iteration': len(individual_results) + 1,
                        'success': False,
                        'cancelled': True,
                        'cancel_reason': 'group_cancelled',
                        'execution_time': 0,
                        'sql_query': None,
                        'final_response': "Teste cancelado durante execução do grupo",
                        'validation_valid': False,
                        'validation_score': 0,
                        'error': None,
                        'timestamp': datetime.now().isoformat()
                    }
                    individual_results.append(cancelled_result)

        execution_time = time.time() - start_time
        print(f"✅ Grupo {group['id']} concluído em {execution_time:.2f}s")

        execution_time = time.time() - start_time
        print(f"✅ Grupo {group['id']} concluído em {execution_time:.2f}s ({group['iterations']} testes)")
        
        # Filtra resultados válidos
        valid_results = []
        errors = []
        
        for result in individual_results:
            if isinstance(result, Exception):
                errors.append(str(result))
                logging.error(f"Erro em teste individual: {result}")
            else:
                valid_results.append(result)
                self.results['individual_results'].append(result)
        
        # Calcula estatísticas do grupo
        group_stats = self._calculate_group_stats(valid_results, group)
        group_stats['errors'] = errors
        group_stats['error_count'] = len(errors)
        
        logging.info(f"✅ Grupo {group['id']} concluído: {len(valid_results)} sucessos, {len(errors)} erros")
        
        return group_stats
    
    async def _run_single_test(self, semaphore: asyncio.Semaphore, question: str, group: Dict[str, Any],
                              iteration: int, validation_method: str, expected_content: str) -> Dict[str, Any]:
        """
        Executa um teste individual com paralelismo real

        Args:
            semaphore: Semáforo para controle de concorrência
            question: Pergunta do teste
            group: Configuração do grupo
            iteration: Número da iteração
            validation_method: Método de validação
            expected_content: Conteúdo esperado

        Returns:
            Resultado do teste individual
        """
        async with semaphore:
            try:
                start_time = time.time()

                # Cria thread_id único para este teste
                thread_id = f"test_{group['id']}_{iteration}_{uuid.uuid4().hex[:8]}"

                # Cria Event individual para cancelamento deste teste
                cancel_event = threading.Event()

                # Registra teste como em execução
                with self._lock:
                    self.status['running_tests'][thread_id] = {
                        'start_time': start_time,
                        'group_id': group['id'],
                        'iteration': iteration,
                        'question': question[:50] + '...' if len(question) > 50 else question
                    }
                    self.status['current_test'] = thread_id
                    self._cancel_events[thread_id] = cancel_event

                print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] 🚀 INICIANDO {thread_id} (Worker {asyncio.current_task().get_name() if asyncio.current_task() else 'unknown'})")
                logging.info(f"🔄 Iniciando teste {thread_id} - Grupo {group['id']}, Iteração {iteration}")

                # Verifica se foi cancelado antes de começar
                if thread_id in self.status['cancelled_tests']:
                    print(f"🚫 Teste {thread_id} cancelado antes de iniciar")
                    return self._create_cancelled_result(thread_id, group, iteration, start_time)

                # Registra task para cancelamento (NOVO)
                current_task = asyncio.current_task()
                with self._lock:
                    self._active_futures[thread_id] = current_task

                # Executa em thread separada para paralelismo real (COMO ESTAVA ANTES)
                loop = asyncio.get_event_loop()

                def run_sync_test():
                    """Executa teste de forma síncrona em thread separada COM VERIFICAÇÃO DE CANCELAMENTO"""
                    try:
                        # Verifica cancelamento antes de iniciar
                        if cancel_event.is_set() or thread_id in self.status['cancelled_tests']:
                            print(f"🚫 Teste {thread_id} cancelado antes de iniciar")
                            return {'cancelled': True, 'reason': 'cancelled_before_start'}

                        # Cria novo loop para esta thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)

                        try:
                            # Inicializa AgentGraphManager para este teste
                            graph_manager = AgentGraphManager()

                            # Verifica cancelamento antes de processar
                            if cancel_event.is_set() or thread_id in self.status['cancelled_tests']:
                                print(f"🚫 Teste {thread_id} cancelado antes de processar query")
                                return {'cancelled': True, 'reason': 'cancelled_before_processing'}

                            # Executa query com timeout
                            async def run_with_cancellation():
                                # Verifica cancelamento durante execução
                                if cancel_event.is_set() or thread_id in self.status['cancelled_tests']:
                                    raise asyncio.CancelledError(f"Teste {thread_id} cancelado durante execução")

                                return await graph_manager.process_query(
                                    user_input=question,
                                    selected_model=group['sql_model_name'],
                                    processing_enabled=group['processing_enabled'],
                                    processing_model=group['processing_model_name'] if group['processing_enabled'] else None,
                                    question_refinement_enabled=group.get('question_refinement_enabled', False),
                                    thread_id=thread_id
                                )

                            # Executa com timeout
                            result = new_loop.run_until_complete(
                                asyncio.wait_for(run_with_cancellation(), timeout=self._test_timeout)
                            )

                            # Verifica cancelamento após execução
                            if cancel_event.is_set() or thread_id in self.status['cancelled_tests']:
                                print(f"🚫 Teste {thread_id} cancelado após execução")
                                return {'cancelled': True, 'reason': 'cancelled_after_execution'}

                            return result

                        finally:
                            new_loop.close()

                    except asyncio.TimeoutError:
                        print(f"⏰ Teste {thread_id} TIMEOUT após {self._test_timeout}s")
                        logging.error(f"Timeout em teste {thread_id} após {self._test_timeout}s")
                        with self._lock:
                            self.status['timeout_tests'].add(thread_id)
                        return {'timeout': True, 'duration': self._test_timeout}
                    except asyncio.CancelledError:
                        print(f"🚫 Teste {thread_id} CANCELADO via CancelledError")
                        return {'cancelled': True, 'reason': 'asyncio_cancelled'}
                    except Exception as e:
                        print(f"❌ Erro em teste {thread_id}: {e}")
                        logging.error(f"Erro em thread separada para {thread_id}: {e}")
                        return {'error': str(e)}

                # Executa em ThreadPoolExecutor para paralelismo real (COMO ESTAVA ANTES)
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = loop.run_in_executor(executor, run_sync_test)

                    # Aguarda com verificação AGRESSIVA de cancelamento
                    check_count = 0
                    while not future.done():
                        await asyncio.sleep(0.05)  # Verifica a cada 50ms (mais frequente)
                        check_count += 1

                        # Verifica cancelamento
                        if (thread_id in self.status['cancelled_tests'] or
                            cancel_event.is_set()):

                            print(f"🚫 CANCELAMENTO DETECTADO para {thread_id} (check #{check_count})")

                            # Cancela future IMEDIATAMENTE
                            if not future.cancelled():
                                future.cancel()
                                print(f"🚫 Future cancelada para {thread_id}")

                            # Sinaliza Event para parar processamento interno
                            cancel_event.set()

                            # Aguarda um pouco para o cancelamento propagar
                            try:
                                await asyncio.wait_for(future, timeout=2.0)
                            except (asyncio.TimeoutError, asyncio.CancelledError):
                                print(f"🚫 Cancelamento forçado concluído para {thread_id}")
                            except:
                                pass

                            return self._create_cancelled_result(thread_id, group, iteration, start_time, 'user_cancelled')

                    result = await future

                execution_time = time.time() - start_time

                # Remove teste da lista de execução e limpa recursos
                with self._lock:
                    if thread_id in self.status['running_tests']:
                        del self.status['running_tests'][thread_id]
                    if self.status['current_test'] == thread_id:
                        self.status['current_test'] = None
                    if thread_id in self._active_futures:
                        del self._active_futures[thread_id]
                    if thread_id in self._cancel_events:
                        del self._cancel_events[thread_id]
                    # Remove da lista de cancelados também
                    self.status['cancelled_tests'].discard(thread_id)

                # Verifica tipo de resultado
                if isinstance(result, dict):
                    if result.get('cancelled'):
                        print(f"🚫 [{datetime.now().strftime('%H:%M:%S')}] CANCELADO {thread_id} - {result.get('reason', 'unknown')}")
                        logging.info(f"🚫 Teste {thread_id} cancelado")
                        return self._create_cancelled_result(thread_id, group, iteration, start_time, result.get('reason'))
                    elif result.get('timeout'):
                        print(f"⏰ [{datetime.now().strftime('%H:%M:%S')}] TIMEOUT {thread_id} após {result.get('duration')}s")
                        logging.warning(f"⏰ Teste {thread_id} timeout")
                        return self._create_timeout_result(thread_id, group, iteration, start_time, result.get('duration'))
                    elif result.get('error'):
                        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] ERRO {thread_id}: {result['error']}")
                        logging.error(f"❌ Teste {thread_id} erro: {result['error']}")

                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] 🎉 CONCLUÍDO {thread_id} em {execution_time:.2f}s")
                logging.info(f"✅ Teste {thread_id} concluído em {execution_time:.2f}s")

                # Valida resultado
                validation_result = await self.validator.validate_result(
                    question=question,
                    sql_query=result.get('sql_query_extracted', ''),
                    response=result.get('response', ''),
                    method=validation_method,
                    expected_content=expected_content
                )

                # Monta resultado individual
                individual_result = {
                    'group_id': group['id'],
                    'iteration': iteration,
                    'thread_id': thread_id,
                    'timestamp': datetime.now().isoformat(),
                    'execution_time': round(execution_time, 2),
                    'question': question,
                    'sql_model': group['sql_model_name'],
                    'processing_enabled': group['processing_enabled'],
                    'processing_model': group['processing_model_name'],
                    'question_refinement_enabled': group.get('question_refinement_enabled', False),
                    'original_question': result.get('original_user_input', question),
                    'refined_question': result.get('refined_question', question),
                    'question_refinement_applied': result.get('question_refinement_applied', False),
                    'question_refinement_changes': result.get('question_refinement_changes', []),
                    'sql_query': result.get('sql_query_extracted', ''),
                    'response': result.get('response', ''),
                    'error': result.get('error'),
                    'success': not bool(result.get('error')),
                    'validation': validation_result
                }

                # Atualiza progresso
                with self._lock:
                    self.status['completed_tests'] += 1
                    progress = (self.status['completed_tests'] / self.status['total_tests']) * 100
                    self.status['progress'] = progress

                    # Estima tempo restante
                    if self.status['start_time']:
                        elapsed = time.time() - self.status['start_time']
                        if self.status['completed_tests'] > 0:
                            avg_time_per_test = elapsed / self.status['completed_tests']
                            remaining_tests = self.status['total_tests'] - self.status['completed_tests']
                            self.status['estimated_remaining'] = avg_time_per_test * remaining_tests

                            # Print visual do progresso
                            remaining_min = int(self.status['estimated_remaining'] // 60)
                            remaining_sec = int(self.status['estimated_remaining'] % 60)

                            print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] Progresso: {self.status['completed_tests']}/{self.status['total_tests']} ({progress:.1f}%) - Restam ~{remaining_min}m{remaining_sec}s")

                logging.info(f"📊 Progresso: {self.status['completed_tests']}/{self.status['total_tests']} ({progress:.1f}%)")

                return individual_result

            except Exception as e:
                logging.error(f"❌ Erro em teste individual (grupo {group['id']}, iteração {iteration}): {e}")

                # Atualiza progresso mesmo com erro
                with self._lock:
                    self.status['completed_tests'] += 1
                    self.status['errors'].append(f"Grupo {group['id']}, Iteração {iteration}: {e}")

                return {
                    'group_id': group['id'],
                    'iteration': iteration,
                    'thread_id': f"error_{group['id']}_{iteration}",
                    'timestamp': datetime.now().isoformat(),
                    'execution_time': time.time() - start_time,
                    'question': question,
                    'sql_model': group['sql_model_name'],
                    'processing_enabled': group['processing_enabled'],
                    'processing_model': group['processing_model_name'],
                    'sql_query': '',
                    'response': '',
                    'error': str(e),
                    'success': False,
                    'validation': {'valid': False, 'score': 0, 'reason': f'Erro de execução: {e}'}
                }
    
    def _calculate_group_stats(self, results: List[Dict[str, Any]], group: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula estatísticas de um grupo
        
        Args:
            results: Resultados individuais do grupo
            group: Configuração do grupo
            
        Returns:
            Estatísticas do grupo
        """
        if not results:
            return {
                'group_id': group['id'],
                'group_config': group,
                'total_tests': 0,
                'success_rate': 0,
                'validation_rate': 0,
                'consistency_rate': 0,
                'avg_execution_time': 0,
                'individual_results': []
            }
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get('success', False))
        valid_responses = sum(1 for r in results if r.get('validation', {}).get('valid', False))
        
        # Calcula consistência baseada na porcentagem de testes válidos
        successful_results = [r for r in results if r.get('success', False)]
        sql_queries = [r.get('sql_query', '') for r in successful_results]

        # Consistência baseada na porcentagem de validações corretas
        validation_consistency = self._calculate_validation_consistency(successful_results)
        sql_consistency = self._calculate_consistency(sql_queries)
        
        avg_execution_time = sum(r.get('execution_time', 0) for r in results) / total_tests
        
        return {
            'group_id': group['id'],
            'group_config': group,
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'valid_responses': valid_responses,
            'success_rate': round((successful_tests / total_tests) * 100, 2),
            'validation_rate': round((valid_responses / total_tests) * 100, 2),
            'validation_consistency': round(validation_consistency, 2),
            'sql_consistency': round(sql_consistency * 100, 2),
            'avg_execution_time': round(avg_execution_time, 2),
            'individual_results': results
        }
    
    def _calculate_consistency(self, items: List[str]) -> float:
        """
        Calcula taxa de consistência entre itens (para SQL queries)

        Args:
            items: Lista de strings para comparar

        Returns:
            Taxa de consistência (0-1)
        """
        if len(items) <= 1:
            return 1.0

        # Conta ocorrências únicas
        unique_items = set(items)
        most_common_count = max(items.count(item) for item in unique_items)

        return most_common_count / len(items)

    def _calculate_validation_consistency(self, results: List[dict]) -> float:
        """
        Calcula consistência baseada na porcentagem de testes válidos vs inválidos

        Args:
            results: Lista de resultados dos testes com informações de validação

        Returns:
            Porcentagem de testes válidos (0-100%)
        """
        if not results:
            return 0.0

        # Conta quantos testes foram validados como corretos
        valid_count = 0
        total_count = len(results)

        for result in results:
            validation = result.get('validation', {})
            is_valid = validation.get('valid', False)
            if is_valid:
                valid_count += 1

        # Consistência = porcentagem de testes válidos
        consistency_rate = (valid_count / total_count) * 100

        print(f"🔍 [VALIDATION_CONSISTENCY] Total: {total_count}, Válidos: {valid_count}, Inválidos: {total_count - valid_count}")
        print(f"🔍 [VALIDATION_CONSISTENCY] Consistência: {valid_count}/{total_count} = {consistency_rate:.1f}%")

        return round(consistency_rate, 2)
    
    def _generate_summary(self):
        """Gera resumo geral dos testes"""
        group_results = self.results.get('group_results', [])
        
        if not group_results:
            self.results['summary'] = {}
            return
        
        total_tests = sum(gr['total_tests'] for gr in group_results)
        total_successful = sum(gr['successful_tests'] for gr in group_results)
        total_valid = sum(gr['valid_responses'] for gr in group_results)
        
        avg_success_rate = sum(gr['success_rate'] for gr in group_results) / len(group_results)
        avg_validation_rate = sum(gr['validation_rate'] for gr in group_results) / len(group_results)
        avg_validation_consistency = sum(gr['validation_consistency'] for gr in group_results) / len(group_results)
        avg_sql_consistency = sum(gr['sql_consistency'] for gr in group_results) / len(group_results)

        # Garante que as médias não passem de 100%
        avg_validation_consistency = min(avg_validation_consistency, 100.0)
        avg_sql_consistency = min(avg_sql_consistency, 100.0)
        
        self.results['summary'] = {
            'total_groups': len(group_results),
            'total_tests': total_tests,
            'total_successful': total_successful,
            'total_valid': total_valid,
            'overall_success_rate': round((total_successful / total_tests) * 100, 2),
            'overall_validation_rate': round((total_valid / total_tests) * 100, 2),
            'avg_validation_consistency': round(avg_validation_consistency, 2),
            'avg_sql_consistency': round(avg_sql_consistency, 2),
            'best_performing_group': max(group_results, key=lambda x: x['validation_rate']),
            'most_consistent_group': max(group_results, key=lambda x: x['validation_consistency'])
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual dos testes"""
        with self._lock:
            status = self.status.copy()
            # Adiciona informações dos testes em execução
            status['running_tests_count'] = len(self.status['running_tests'])
            status['running_tests_details'] = list(self.status['running_tests'].values())
            return status

    def cancel_current_test(self, thread_id: str = None) -> bool:
        """
        Cancela teste específico ou o mais antigo em execução COM CANCELAMENTO FORÇADO

        Args:
            thread_id: ID do teste específico para cancelar (opcional)

        Returns:
            True se cancelou algum teste
        """
        with self._lock:
            if thread_id:
                if thread_id in self.status['running_tests']:
                    self.status['cancelled_tests'].add(thread_id)

                    # CANCELAMENTO FORÇADO - Sinaliza Event individual
                    if thread_id in self._cancel_events:
                        self._cancel_events[thread_id].set()
                        print(f"🚫 Event de cancelamento ativado para {thread_id}")

                    # CANCELAMENTO FORÇADO - Cancela future se existir
                    if thread_id in self._active_futures:
                        future = self._active_futures[thread_id]
                        if not future.done():
                            future.cancel()
                            print(f"🚫 Future cancelada forçadamente para {thread_id}")

                    print(f"🚫 Teste {thread_id} marcado para cancelamento FORÇADO")
                    logging.info(f"Teste {thread_id} cancelado FORÇADAMENTE pelo usuário")
                    return True
            else:
                # Cancela o teste mais antigo
                if self.status['running_tests']:
                    oldest_test = min(
                        self.status['running_tests'].items(),
                        key=lambda x: x[1]['start_time']
                    )
                    thread_id = oldest_test[0]
                    self.status['cancelled_tests'].add(thread_id)

                    # CANCELAMENTO FORÇADO - Sinaliza Event individual
                    if thread_id in self._cancel_events:
                        self._cancel_events[thread_id].set()
                        print(f"🚫 Event de cancelamento ativado para {thread_id}")

                    # CANCELAMENTO FORÇADO - Cancela future se existir
                    if thread_id in self._active_futures:
                        future = self._active_futures[thread_id]
                        if not future.done():
                            future.cancel()
                            print(f"🚫 Future cancelada forçadamente para {thread_id}")

                    print(f"🚫 Teste mais antigo {thread_id} marcado para cancelamento FORÇADO")
                    logging.info(f"Teste mais antigo {thread_id} cancelado FORÇADAMENTE pelo usuário")
                    return True
        return False

    def cancel_all_tests(self) -> int:
        """
        Cancela todos os testes em execução

        Returns:
            Número de testes cancelados
        """
        with self._lock:
            running_count = len(self.status['running_tests'])
            for thread_id in self.status['running_tests'].keys():
                self.status['cancelled_tests'].add(thread_id)

            print(f"🚫 {running_count} testes marcados para cancelamento")
            logging.info(f"{running_count} testes cancelados pelo usuário")
            return running_count

    def skip_stuck_tests(self, max_duration: int = 120) -> int:
        """
        Marca testes travados (que excedem tempo limite) para cancelamento

        Args:
            max_duration: Tempo máximo em segundos

        Returns:
            Número de testes marcados como travados
        """
        current_time = time.time()
        stuck_count = 0

        with self._lock:
            for thread_id, test_info in self.status['running_tests'].items():
                if current_time - test_info['start_time'] > max_duration:
                    if thread_id not in self.status['cancelled_tests']:
                        self.status['timeout_tests'].add(thread_id)
                        self.status['cancelled_tests'].add(thread_id)
                        stuck_count += 1
                        print(f"⏰ Teste {thread_id} marcado como travado (>{max_duration}s)")
                        logging.warning(f"Teste {thread_id} travado - timeout após {max_duration}s")

        return stuck_count

    def _create_cancelled_result(self, thread_id: str, group: Dict[str, Any], iteration: int, start_time: float, reason: str = 'user_cancelled') -> Dict[str, Any]:
        """Cria resultado para teste cancelado"""
        execution_time = time.time() - start_time
        return {
            'thread_id': thread_id,
            'group_id': group['id'],
            'iteration': iteration,
            'success': False,
            'cancelled': True,
            'cancel_reason': reason,
            'execution_time': execution_time,
            'sql_query': None,
            'final_response': f"Teste cancelado: {reason}",
            'validation_valid': False,
            'validation_score': 0,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }

    def _create_timeout_result(self, thread_id: str, group: Dict[str, Any], iteration: int, start_time: float, duration: int) -> Dict[str, Any]:
        """Cria resultado para teste com timeout"""
        execution_time = time.time() - start_time
        return {
            'thread_id': thread_id,
            'group_id': group['id'],
            'iteration': iteration,
            'success': False,
            'timeout': True,
            'timeout_duration': duration,
            'execution_time': execution_time,
            'sql_query': None,
            'final_response': f"Teste travado - timeout após {duration}s",
            'validation_valid': False,
            'validation_score': 0,
            'error': f"Timeout após {duration}s",
            'timestamp': datetime.now().isoformat()
        }
    
    def get_results(self) -> Dict[str, Any]:
        """Retorna resultados dos testes"""
        return self.results
