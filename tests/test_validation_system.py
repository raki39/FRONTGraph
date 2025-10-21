"""
Testes para o sistema de validação de queries SQL
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Imports do sistema de validação
from agentgraph.agents.validation_agent import ValidationAgentManager
from agentgraph.nodes.validation_node import (
    query_validation_node, 
    validate_validation_state,
    should_execute_validation
)

class TestValidationAgentManager:
    """Testes para o ValidationAgentManager"""
    
    def test_initialization(self):
        """Testa inicialização do agente"""
        agent = ValidationAgentManager(model="gpt-4o-mini")
        assert agent.model == "gpt-4o-mini"
        assert agent.llm is not None
    
    def test_initialization_with_claude(self):
        """Testa inicialização com modelo Claude"""
        with patch('agentgraph.agents.validation_agent.ChatAnthropic') as mock_claude:
            mock_claude.return_value = Mock()
            agent = ValidationAgentManager(model="claude-3-sonnet")
            assert agent.model == "claude-3-sonnet"
            mock_claude.assert_called_once()
    
    def test_initialization_fallback(self):
        """Testa fallback para modelo desconhecido"""
        with patch('agentgraph.agents.validation_agent.ChatOpenAI') as mock_openai:
            mock_openai.return_value = Mock()
            agent = ValidationAgentManager(model="unknown-model")
            # Deve usar GPT-4o-mini como fallback
            mock_openai.assert_called_with(model="gpt-4o-mini", temperature=0.1)
    
    @pytest.mark.asyncio
    async def test_validate_individual_success(self):
        """Testa validação individual bem-sucedida"""
        # Mock do LLM
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.content = '''
        {
            "question_clarity_score": 0.85,
            "query_correctness_score": 0.90,
            "response_accuracy_score": 0.88,
            "overall_score": 0.88,
            "issues_found": ["Pergunta muito genérica"],
            "suggestions": ["Especificar período"],
            "improved_question": "Pergunta melhorada"
        }
        '''
        mock_llm.ainvoke.return_value = mock_response
        
        agent = ValidationAgentManager()
        agent.llm = mock_llm
        
        result = await agent.validate_individual(
            question="Qual o total de vendas?",
            sql_query="SELECT SUM(valor) FROM vendas",
            response="Total: R$ 10.000",
            auto_improve=True
        )
        
        assert result["question_clarity_score"] == 0.85
        assert result["query_correctness_score"] == 0.90
        assert result["response_accuracy_score"] == 0.88
        assert result["overall_score"] == 0.88
        assert "Pergunta muito genérica" in result["issues_found"]
        assert "Especificar período" in result["suggestions"]
        assert result["improved_question"] == "Pergunta melhorada"
    
    @pytest.mark.asyncio
    async def test_validate_individual_error_handling(self):
        """Testa tratamento de erro na validação individual"""
        # Mock do LLM que gera erro
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("Erro de API")
        
        agent = ValidationAgentManager()
        agent.llm = mock_llm
        
        result = await agent.validate_individual(
            question="Teste",
            sql_query="SELECT 1",
            response="Resultado",
            auto_improve=False
        )
        
        # Deve retornar resultado fallback
        assert result["question_clarity_score"] == 0.5
        assert result["query_correctness_score"] == 0.5
        assert result["response_accuracy_score"] == 0.5
        assert result["overall_score"] == 0.5
        assert "Erro na análise - tente novamente" in result["issues_found"]
    
    @pytest.mark.asyncio
    async def test_validate_comparative_success(self):
        """Testa validação comparativa bem-sucedida"""
        # Mock do LLM
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.content = '''
        {
            "consistency_score": 0.75,
            "inconsistencies_found": ["Queries diferentes para pergunta similar"],
            "suggestions": ["Padronizar formato de data"],
            "improved_question": "Pergunta padronizada"
        }
        '''
        mock_llm.ainvoke.return_value = mock_response
        
        agent = ValidationAgentManager()
        agent.llm = mock_llm
        
        current_run = {
            "question": "Vendas do mês",
            "sql_query": "SELECT SUM(valor) FROM vendas WHERE MONTH(data) = 12",
            "response": "Total: R$ 5.000"
        }
        
        compared_runs = [
            {
                "question": "Vendas de dezembro",
                "sql_query": "SELECT SUM(valor) FROM vendas WHERE data >= '2024-12-01'",
                "response": "Total: R$ 4.800"
            }
        ]
        
        result = await agent.validate_comparative(current_run, compared_runs)
        
        assert result["consistency_score"] == 0.75
        assert "Queries diferentes para pergunta similar" in result["inconsistencies_found"]
        assert "Padronizar formato de data" in result["suggestions"]
        assert result["improved_question"] == "Pergunta padronizada"
    
    def test_parse_validation_response_success(self):
        """Testa parse bem-sucedido da resposta"""
        agent = ValidationAgentManager()
        
        response_content = '''
        Análise da query:
        {
            "question_clarity_score": 0.9,
            "overall_score": 0.85
        }
        Fim da análise.
        '''
        
        result = agent._parse_validation_response(response_content)
        
        assert result["question_clarity_score"] == 0.9
        assert result["overall_score"] == 0.85
    
    def test_parse_validation_response_error(self):
        """Testa parse com erro"""
        agent = ValidationAgentManager()
        
        # Resposta sem JSON válido
        response_content = "Erro na análise, não foi possível processar"
        
        result = agent._parse_validation_response(response_content)
        
        # Deve retornar resultado fallback
        assert "Erro na análise - tente novamente" in result["issues_found"]

class TestValidationNode:
    """Testes para o nodo de validação"""
    
    @pytest.mark.asyncio
    async def test_query_validation_node_individual_success(self):
        """Testa nodo de validação individual bem-sucedido"""
        # Mock do ValidationAgentManager
        with patch('agentgraph.nodes.validation_node.ValidationAgentManager') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.validate_individual.return_value = {
                "question_clarity_score": 0.8,
                "query_correctness_score": 0.9,
                "response_accuracy_score": 0.85,
                "overall_score": 0.85,
                "issues_found": [],
                "suggestions": ["Ótima pergunta!"]
            }
            mock_agent_class.return_value = mock_agent
            
            state = {
                "validation_request": {
                    "validation_type": "individual",
                    "auto_improve_question": False
                },
                "run_data": {
                    "question": "Qual o total de vendas?",
                    "sql_used": "SELECT SUM(valor) FROM vendas",
                    "result_data": "Total: R$ 10.000"
                },
                "validation_model": "gpt-4o-mini"
            }
            
            result_state = await query_validation_node(state)
            
            assert result_state["validation_success"] is True
            assert result_state["validation_error"] is None
            assert result_state["validation_result"]["overall_score"] == 0.85
            assert result_state["validation_time"] > 0
    
    @pytest.mark.asyncio
    async def test_query_validation_node_comparative_success(self):
        """Testa nodo de validação comparativa bem-sucedido"""
        with patch('agentgraph.nodes.validation_node.ValidationAgentManager') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.validate_comparative.return_value = {
                "consistency_score": 0.7,
                "inconsistencies_found": ["Pequenas diferenças"],
                "suggestions": ["Padronizar queries"]
            }
            mock_agent_class.return_value = mock_agent
            
            state = {
                "validation_request": {
                    "validation_type": "comparative"
                },
                "run_data": {
                    "question": "Vendas do mês",
                    "sql_used": "SELECT SUM(valor) FROM vendas",
                    "result_data": "Total: R$ 5.000"
                },
                "compared_runs_data": [
                    {
                        "question": "Vendas de dezembro",
                        "sql_query": "SELECT SUM(valor) FROM vendas",
                        "response": "Total: R$ 4.800"
                    }
                ]
            }
            
            result_state = await query_validation_node(state)
            
            assert result_state["validation_success"] is True
            assert result_state["validation_result"]["consistency_score"] == 0.7
    
    @pytest.mark.asyncio
    async def test_query_validation_node_missing_data(self):
        """Testa nodo com dados ausentes"""
        state = {
            "validation_request": {
                "validation_type": "individual"
            }
            # run_data ausente
        }
        
        result_state = await query_validation_node(state)
        
        assert result_state["validation_success"] is False
        assert "run_data não encontrado" in result_state["validation_error"]
    
    def test_validate_validation_state_success(self):
        """Testa validação de state bem-sucedida"""
        state = {
            "validation_request": {
                "validation_type": "individual"
            },
            "run_data": {
                "question": "Teste",
                "sql_used": "SELECT 1",
                "result_data": "Resultado"
            }
        }
        
        assert validate_validation_state(state) is True
    
    def test_validate_validation_state_missing_fields(self):
        """Testa validação de state com campos ausentes"""
        state = {
            "validation_request": {
                "validation_type": "individual"
            },
            "run_data": {
                "question": "Teste"
                # sql_used e result_data ausentes
            }
        }
        
        assert validate_validation_state(state) is False
    
    def test_validate_validation_state_comparative_missing_runs(self):
        """Testa validação comparativa sem runs de comparação"""
        state = {
            "validation_request": {
                "validation_type": "comparative"
            },
            "run_data": {
                "question": "Teste",
                "sql_used": "SELECT 1",
                "result_data": "Resultado"
            }
            # compared_runs_data ausente
        }
        
        assert validate_validation_state(state) is False
    
    def test_should_execute_validation_valid(self):
        """Testa roteamento para validação válida"""
        state = {
            "validation_request": {"validation_type": "individual"},
            "run_data": {
                "question": "Teste",
                "sql_used": "SELECT 1", 
                "result_data": "Resultado"
            }
        }
        
        assert should_execute_validation(state) == "query_validation"
    
    def test_should_execute_validation_invalid(self):
        """Testa roteamento para validação inválida"""
        state = {}  # State vazio
        
        assert should_execute_validation(state) == "validation_error"

if __name__ == "__main__":
    # Executa testes básicos
    pytest.main([__file__, "-v"])
