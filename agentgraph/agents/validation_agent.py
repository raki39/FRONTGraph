"""
Agente especializado em validação de queries SQL e respostas do AgentSQL
"""
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)

class ValidationAgentManager:
    """Agente especializado em validação de queries SQL"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.llm = self._initialize_llm()
        logger.info(f"[VALIDATION_AGENT] Inicializado com modelo: {model}")
    
    def _initialize_llm(self):
        """Inicializa LLM baseado no modelo selecionado"""
        try:
            if "gpt" in self.model.lower():
                return ChatOpenAI(model=self.model, temperature=0.1)
            elif "claude" in self.model.lower():
                return ChatAnthropic(model=self.model, temperature=0.1)
            else:
                logger.warning(f"Modelo {self.model} não reconhecido, usando GPT-4o-mini")
                return ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        except Exception as e:
            logger.error(f"Erro ao inicializar LLM: {e}")
            # Fallback para GPT-4o-mini
            return ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    
    async def validate_individual(
        self, 
        question: str, 
        sql_query: str, 
        response: str,
        auto_improve: bool = False
    ) -> Dict[str, Any]:
        """
        Valida pergunta, query e resposta individual
        
        Args:
            question: Pergunta do usuário
            sql_query: Query SQL gerada
            response: Resposta do AgentSQL
            auto_improve: Se deve gerar pergunta melhorada
            
        Returns:
            Dicionário com scores e análises
        """
        logger.info("[VALIDATION_AGENT] Iniciando validação individual")
        
        try:
            prompt = self._build_individual_validation_prompt(
                question, sql_query, response, auto_improve
            )

            response_obj = await self.llm.ainvoke(prompt)
            logger.info(f"[VALIDATION_AGENT] Resposta bruta da LLM: {response_obj.content[:500]}...")

            result = self._parse_validation_response(response_obj.content)

            logger.info(f"[VALIDATION_AGENT] Validação concluída - Score geral: {result.get('overall_score', 'N/A')}")
            logger.info(f"[VALIDATION_AGENT] Suggestions: {result.get('suggestions', 'N/A')}")
            logger.info(f"[VALIDATION_AGENT] Observations: {result.get('observations', 'N/A')}")
            logger.info(f"[VALIDATION_AGENT] Improved Question: {result.get('improved_question', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"[VALIDATION_AGENT] Erro na validação individual: {e}")
            return self._get_fallback_result("individual")
    
    async def validate_comparative(
        self,
        current_run: Dict[str, str],
        compared_runs: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Compara run atual com runs selecionadas

        Args:
            current_run: Run atual com question, sql_query, response
            compared_runs: Lista de runs para comparação

        Returns:
            Dicionário com análise comparativa
        """
        logger.info(f"[VALIDATION_AGENT] Iniciando validação comparativa com {len(compared_runs)} runs")

        try:
            # Extrai IDs reais das runs ANTES de chamar a LLM
            compared_run_ids = []
            for run in compared_runs:
                run_id = run.get('run_id', run.get('id', 'unknown'))
                compared_run_ids.append(str(run_id))

            logger.info(f"[VALIDATION_AGENT] IDs das runs para comparação: {compared_run_ids}")

            prompt = self._build_comparative_validation_prompt(current_run, compared_runs)

            response_obj = await self.llm.ainvoke(prompt)
            logger.info(f"[VALIDATION_AGENT] Resposta bruta da LLM (comparativa): {response_obj.content[:500]}...")

            result = self._parse_validation_response(response_obj.content)

            # FORÇA a inclusão dos IDs reais (não deixa a LLM decidir)
            result["compared_run_ids"] = compared_run_ids

            logger.info(f"[VALIDATION_AGENT] Comparação concluída - Score consistência: {result.get('consistency_score', 'N/A')}")
            logger.info(f"[VALIDATION_AGENT] IDs reais incluídos: {compared_run_ids}")

            return result

        except Exception as e:
            logger.error(f"[VALIDATION_AGENT] Erro na validação comparativa: {e}")
            return self._get_fallback_result("comparative")
    
    def _build_individual_validation_prompt(
        self,
        question: str,
        sql_query: str,
        response: str,
        auto_improve: bool
    ) -> str:
        """Constrói prompt para validação individual"""

        base_prompt = f"""
Você é um especialista em análise crítica de qualidade de perguntas SQL e validação de respostas.

PERGUNTA DO USUÁRIO: {question}
QUERY SQL GERADA: {sql_query}
RESPOSTA FORNECIDA: {response}

TAREFA: Analise CRITICAMENTE a pergunta, query e resposta. Identifique PROBLEMAS REAIS, não apenas elogie.

ANÁLISE DETALHADA:

1. CLAREZA E ESPECIFICIDADE DA PERGUNTA (0-1):
   Procure por:
   - Termos vagos: "último", "recente", "melhor", "total", "principal"
   - Falta de período temporal específico
   - Falta de escopo definido (todos os registros? apenas ativos?)
   - Ambiguidades que podem gerar múltiplas interpretações
   - Métricas não especificadas

2. CORREÇÃO E LÓGICA DA QUERY (0-1):
   Procure por:
   - Sintaxe SQL correta
   - Lógica que realmente responde à pergunta
   - Filtros apropriados
   - Agregações corretas

3. PRECISÃO E CLAREZA DA RESPOSTA (0-1):
   Procure por:
   - Resposta realmente responde à pergunta?
   - Dados fazem sentido?
   - Formatação clara?
   - Explicação adequada?

FORMATO DE RESPOSTA (JSON válido):
{{
    "question_clarity_score": 0.7,
    "query_correctness_score": 0.8,
    "response_accuracy_score": 0.75,
    "overall_score": 0.75,
    "issues_found": [
        "Pergunta usa termo vago 'último mês' - não especifica se é calendário ou últimos 30 dias",
        "Não define se inclui registros inativos ou deletados",
        "Falta especificação de unidade monetária ou formato de resposta esperado"
    ],
    "observations": "A pergunta é genérica e pode gerar interpretações diferentes. A query parece estar correta sintaticamente, mas sem saber a intenção exata, é difícil validar se está 100% correta. A resposta apresenta números, mas sem contexto claro.",
    "suggestions": "1. Especifique o período exato: 'vendas do mês de outubro de 2024' em vez de 'último mês'. 2. Defina o escopo: 'produtos ativos' ou 'todos os produtos'. 3. Clarifique a métrica: 'valor total em reais' ou 'quantidade de itens vendidos'. 4. Sempre inclua contexto temporal e de escopo nas perguntas.",
    "improved_question": "Qual foi o valor total em reais de vendas de produtos ativos durante o mês de outubro de 2024?"
}}

REGRAS IMPORTANTES:
- "issues_found": Lista de problemas REAIS encontrados (não elogios)
- "observations": Análise crítica do que foi encontrado
- "suggestions": Texto descritivo com melhorias específicas e acionáveis
- "improved_question": Versão melhorada que resolve os problemas identificados
- Todos os scores entre 0 e 1
- overall_score = média dos 3 scores
- SER CRÍTICO E HONESTO, não apenas dar notas altas
"""

        return base_prompt
    
    def _build_comparative_validation_prompt(
        self,
        current_run: Dict[str, str],
        compared_runs: List[Dict[str, str]]
    ) -> str:
        """Constrói prompt para validação comparativa"""

        comparisons = []
        for i, run in enumerate(compared_runs, 1):
            run_id = run.get('run_id', f'run_{i}')
            comparisons.append(f"""
INTERAÇÃO {i} (ID: {run_id}):
PERGUNTA: {run['question']}
QUERY: {run['sql_query']}
RESPOSTA: {run['response']}
""")

        prompt = f"""
Você é um especialista em análise de consistência e qualidade de perguntas SQL.

TAREFA: Compare a interação ATUAL com as ANTERIORES. Identifique diferenças, inconsistências e padrões problemáticos.

INTERAÇÃO ATUAL:
PERGUNTA: {current_run['question']}
QUERY GERADA: {current_run['sql_query']}
RESPOSTA: {current_run['response']}

INTERAÇÕES ANTERIORES PARA COMPARAÇÃO:
{''.join(comparisons)}

ANÁLISE COMPARATIVA DETALHADA:

1. COMPARAÇÃO DE PERGUNTAS:
   - As perguntas são similares ou diferentes?
   - Se similares, usam a mesma terminologia?
   - Há inconsistência em como termos são usados?
   - Algumas perguntas são mais específicas que outras?

2. COMPARAÇÃO DE RESPOSTAS:
   - Para perguntas similares, as respostas são consistentes?
   - Os valores/dados fazem sentido comparados?
   - Há discrepâncias que não podem ser explicadas?
   - A formatação é consistente?

3. PADRÕES E PROBLEMAS RECORRENTES:
   - Que problemas se repetem nas perguntas?
   - Qual é o padrão de ambiguidade?
   - Como as perguntas deveriam ser padronizadas?

FORMATO DE RESPOSTA (JSON válido):
{{
    "consistency_score": 0.6,
    "inconsistencies_found": [
        "Pergunta 1 usa 'último mês' enquanto Pergunta 2 usa 'mês passado' - mesma intenção mas terminologia inconsistente",
        "Pergunta 1 não especifica se inclui produtos inativos, Pergunta 2 também não - padrão de falta de escopo",
        "Resposta 1 mostra valor em reais, Resposta 2 mostra em centavos - inconsistência de formatação"
    ],
    "observations": "As perguntas são similares em intenção mas usam terminologia diferente. Ambas carecem de especificidade temporal e de escopo. As respostas têm formatos diferentes, o que pode confundir o usuário. Há um padrão claro de falta de contexto nas perguntas.",
    "suggestions": "1. Padronize a terminologia: use sempre 'mês de [mês] de [ano]' em vez de 'último mês' ou 'mês passado'. 2. Sempre especifique o escopo: 'produtos ativos' ou 'todos os produtos'. 3. Mantenha formato consistente nas respostas: sempre em reais com 2 casas decimais. 4. Crie um template de pergunta padrão para evitar ambiguidades.",
    "improved_question": "Qual foi o valor total em reais de vendas de produtos ativos durante o mês de outubro de 2024?"
}}

REGRAS IMPORTANTES:
- "consistency_score": 0-1, baseado em quão consistentes são as interações
- "inconsistencies_found": Lista de diferenças e problemas REAIS encontrados
- "observations": Análise crítica dos padrões encontrados
- "suggestions": Texto descritivo com melhorias específicas para padronizar
- "improved_question": Versão padronizada que resolve os problemas identificados
- SER CRÍTICO: se há inconsistências, dar score baixo
- NÃO inclua "compared_run_ids" na resposta
"""

        return prompt
    
    def _parse_validation_response(self, response_content: str) -> Dict[str, Any]:
        """Parse da resposta do LLM para JSON"""
        try:
            # Tenta extrair JSON da resposta
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_content[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Valida campos obrigatórios
                if isinstance(result, dict):
                    return result
            
            raise ValueError("JSON não encontrado ou inválido")
            
        except Exception as e:
            logger.error(f"[VALIDATION_AGENT] Erro ao fazer parse da resposta: {e}")
            logger.debug(f"Resposta original: {response_content}")
            return self._get_fallback_result()
    
    def _get_fallback_result(self, validation_type: str = "individual") -> Dict[str, Any]:
        """Resultado fallback em caso de erro"""
        base_result = {
            "issues_found": ["Erro na análise - tente novamente"],
            "suggestions": ["Verifique a conexão e tente novamente"],
            "improved_question": None
        }
        
        if validation_type == "individual":
            base_result.update({
                "question_clarity_score": 0.5,
                "query_correctness_score": 0.5,
                "response_accuracy_score": 0.5,
                "overall_score": 0.5
            })
        else:  # comparative
            base_result.update({
                "consistency_score": 0.5,
                "inconsistencies_found": ["Erro na análise comparativa"],
                "compared_run_ids": []  # Lista vazia em caso de erro
            })
        
        return base_result
