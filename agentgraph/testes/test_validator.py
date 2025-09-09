#!/usr/bin/env python3
"""
Sistema de validação de resultados de testes
"""
import logging
import re
import asyncio
from typing import Dict, Any, Optional
import sys
import os

# Adiciona path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage
from utils.config import OPENAI_MODELS, ANTHROPIC_MODELS

class TestValidator:
    """
    Validador de resultados de testes usando LLM ou keywords
    """
    
    def __init__(self, validator_model: str = "gpt-4o-mini"):
        """
        Inicializa o validador
        
        Args:
            validator_model: Modelo LLM para validação
        """
        self.validator_model = validator_model
        self.llm = self._initialize_validator_llm()
        
    def _initialize_validator_llm(self):
        """Inicializa LLM para validação"""
        try:
            if self.validator_model in OPENAI_MODELS:
                return ChatOpenAI(
                    model=self.validator_model,
                    temperature=0.1,  # Baixa temperatura para consistência
                    max_tokens=1000
                )
            elif self.validator_model in ANTHROPIC_MODELS:
                return ChatAnthropic(
                    model=self.validator_model,
                    temperature=0.1,
                    max_tokens=1000
                )
            else:
                # Fallback para GPT-4o-mini
                logging.warning(f"Modelo {self.validator_model} não suportado, usando gpt-4o-mini")
                return ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.1,
                    max_tokens=1000
                )
        except Exception as e:
            logging.error(f"Erro ao inicializar LLM validador: {e}")
            return None
    
    async def validate_result(self, question: str, sql_query: str, response: str, 
                            method: str = 'llm', expected_content: str = None) -> Dict[str, Any]:
        """
        Valida resultado de um teste
        
        Args:
            question: Pergunta original
            sql_query: Query SQL gerada
            response: Resposta final do agente
            method: Método de validação ('llm' ou 'keyword')
            expected_content: Conteúdo esperado (para método keyword)
            
        Returns:
            Resultado da validação
        """
        try:
            if method == 'llm':
                return await self._validate_with_llm(question, sql_query, response)
            elif method == 'keyword':
                return self._validate_with_keyword(response, expected_content)
            else:
                return {
                    'valid': False,
                    'score': 0,
                    'reason': f'Método de validação inválido: {method}',
                    'method': method
                }
        except Exception as e:
            logging.error(f"Erro na validação: {e}")
            return {
                'valid': False,
                'score': 0,
                'reason': f'Erro na validação: {e}',
                'method': method
            }
    
    async def _validate_with_llm(self, question: str, sql_query: str, response: str) -> Dict[str, Any]:
        """
        Valida usando LLM
        
        Args:
            question: Pergunta original
            sql_query: Query SQL gerada
            response: Resposta final
            
        Returns:
            Resultado da validação
        """
        if not self.llm:
            return {
                'valid': False,
                'score': 0,
                'reason': 'LLM validador não disponível',
                'method': 'llm'
            }
        
        try:
            # Prompt para validação
            validation_prompt = f"""
Você é um especialista em SQL e análise de dados. Sua tarefa é avaliar se uma resposta gerada por um agente SQL está correta e adequada.

PERGUNTA ORIGINAL:
{question}

QUERY SQL GERADA:
{sql_query}

RESPOSTA FINAL:
{response}

CRITÉRIOS DE AVALIAÇÃO:
1. A query SQL está sintaticamente correta?
2. A query SQL responde adequadamente à pergunta?
3. A resposta final é coerente com a query e a pergunta?
4. A resposta contém informações relevantes e úteis?
5. Há erros evidentes na lógica ou execução?

INSTRUÇÕES:
- Analise cuidadosamente cada critério
- Dê uma pontuação de 0 a 100
- Considere válida (True) se pontuação >= 70
- Seja rigoroso mas justo na avaliação

RESPONDA EXATAMENTE NESTE FORMATO:
PONTUAÇÃO: [número de 0 a 100]
VÁLIDA: [True ou False]
RAZÃO: [explicação breve da avaliação]
"""
            
            # Executa validação
            message = HumanMessage(content=validation_prompt)
            response_llm = await self.llm.ainvoke([message])
            
            # Extrai resultado
            return self._parse_llm_validation(response_llm.content)
            
        except Exception as e:
            logging.error(f"Erro na validação LLM: {e}")
            return {
                'valid': False,
                'score': 0,
                'reason': f'Erro na validação LLM: {e}',
                'method': 'llm'
            }
    
    def _parse_llm_validation(self, llm_response: str) -> Dict[str, Any]:
        """
        Extrai resultado da validação LLM
        
        Args:
            llm_response: Resposta do LLM
            
        Returns:
            Resultado parseado
        """
        try:
            # Padrões para extrair informações
            score_pattern = r'PONTUAÇÃO:\s*(\d+)'
            valid_pattern = r'VÁLIDA:\s*(True|False)'
            reason_pattern = r'RAZÃO:\s*(.+?)(?:\n|$)'
            
            # Extrai pontuação
            score_match = re.search(score_pattern, llm_response, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else 0
            
            # Extrai validade
            valid_match = re.search(valid_pattern, llm_response, re.IGNORECASE)
            valid = valid_match.group(1).lower() == 'true' if valid_match else False
            
            # Extrai razão
            reason_match = re.search(reason_pattern, llm_response, re.IGNORECASE | re.DOTALL)
            reason = reason_match.group(1).strip() if reason_match else 'Sem razão fornecida'
            
            return {
                'valid': valid,
                'score': score,
                'reason': reason,
                'method': 'llm',
                'raw_response': llm_response
            }
            
        except Exception as e:
            logging.error(f"Erro ao parsear validação LLM: {e}")
            return {
                'valid': False,
                'score': 0,
                'reason': f'Erro ao parsear resposta: {e}',
                'method': 'llm',
                'raw_response': llm_response
            }
    
    def _validate_with_keyword(self, response: str, expected_content: str) -> Dict[str, Any]:
        """
        Valida usando palavras-chave
        
        Args:
            response: Resposta para validar
            expected_content: Conteúdo esperado
            
        Returns:
            Resultado da validação
        """
        if not expected_content:
            return {
                'valid': False,
                'score': 0,
                'reason': 'Conteúdo esperado não fornecido',
                'method': 'keyword'
            }
        
        try:
            # Normaliza textos
            response_normalized = response.lower().strip()
            expected_normalized = expected_content.lower().strip()
            
            # Verifica se contém o conteúdo esperado
            contains_expected = expected_normalized in response_normalized
            
            # Calcula score baseado na presença
            score = 100 if contains_expected else 0
            
            # Verifica se há erro explícito
            error_keywords = ['erro', 'error', 'falha', 'exception', 'não foi possível']
            has_error = any(keyword in response_normalized for keyword in error_keywords)
            
            if has_error:
                score = max(0, score - 50)  # Penaliza erros
            
            return {
                'valid': contains_expected and not has_error,
                'score': score,
                'reason': f'Conteúdo {"encontrado" if contains_expected else "não encontrado"}. {"Erro detectado" if has_error else "Sem erros"}',
                'method': 'keyword',
                'expected_content': expected_content,
                'contains_expected': contains_expected,
                'has_error': has_error
            }
            
        except Exception as e:
            logging.error(f"Erro na validação por keyword: {e}")
            return {
                'valid': False,
                'score': 0,
                'reason': f'Erro na validação: {e}',
                'method': 'keyword'
            }
    
    def validate_sql_syntax(self, sql_query: str) -> Dict[str, Any]:
        """
        Valida sintaxe SQL básica
        
        Args:
            sql_query: Query SQL para validar
            
        Returns:
            Resultado da validação de sintaxe
        """
        try:
            if not sql_query or not sql_query.strip():
                return {
                    'valid': False,
                    'reason': 'Query SQL vazia'
                }
            
            sql_normalized = sql_query.strip().upper()
            
            # Verificações básicas
            checks = {
                'has_select': 'SELECT' in sql_normalized,
                'has_from': 'FROM' in sql_normalized,
                'balanced_parentheses': sql_query.count('(') == sql_query.count(')'),
                'no_obvious_errors': not any(error in sql_normalized for error in ['ERROR', 'SYNTAX ERROR', 'INVALID'])
            }
            
            all_valid = all(checks.values())
            
            return {
                'valid': all_valid,
                'checks': checks,
                'reason': 'Sintaxe SQL válida' if all_valid else 'Problemas de sintaxe detectados'
            }
            
        except Exception as e:
            return {
                'valid': False,
                'reason': f'Erro na validação de sintaxe: {e}'
            }
    
    async def batch_validate(self, results: list, method: str = 'llm', expected_content: str = None) -> list:
        """
        Valida múltiplos resultados em lote
        
        Args:
            results: Lista de resultados para validar
            method: Método de validação
            expected_content: Conteúdo esperado
            
        Returns:
            Lista de validações
        """
        tasks = []
        
        for result in results:
            task = self.validate_result(
                question=result.get('question', ''),
                sql_query=result.get('sql_query', ''),
                response=result.get('response', ''),
                method=method,
                expected_content=expected_content
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
