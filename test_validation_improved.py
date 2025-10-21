#!/usr/bin/env python3
"""
Teste rápido da validação melhorada
"""

import asyncio
import json
from agentgraph.agents.validation_agent import ValidationAgentManager

async def test_individual_validation():
    """Testa validação individual"""
    print("\n" + "="*80)
    print("TESTE 1: VALIDAÇÃO INDIVIDUAL")
    print("="*80)
    
    agent = ValidationAgentManager(model="gpt-4o-mini")
    
    question = "Qual foi o último mês de vendas?"
    sql_query = "SELECT SUM(amount) FROM sales WHERE MONTH(date) = MONTH(NOW())"
    response = "O total foi R$ 50.000"
    
    print(f"\n📝 Pergunta: {question}")
    print(f"🔍 Query: {sql_query}")
    print(f"📊 Resposta: {response}")
    
    result = await agent.validate_individual(question, sql_query, response, auto_improve=True)
    
    print("\n✅ Resultado da Validação Individual:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result

async def test_comparative_validation():
    """Testa validação comparativa"""
    print("\n" + "="*80)
    print("TESTE 2: VALIDAÇÃO COMPARATIVA")
    print("="*80)
    
    agent = ValidationAgentManager(model="gpt-4o-mini")
    
    current_run = {
        "question": "Qual foi o último mês de vendas?",
        "sql_query": "SELECT SUM(amount) FROM sales WHERE MONTH(date) = MONTH(NOW())",
        "response": "O total foi R$ 50.000"
    }
    
    compared_runs = [
        {
            "run_id": 1,
            "question": "Qual foi o mês passado de vendas?",
            "sql_query": "SELECT SUM(amount) FROM sales WHERE MONTH(date) = MONTH(NOW() - INTERVAL 1 MONTH)",
            "response": "O total foi R$ 45.000"
        },
        {
            "run_id": 2,
            "question": "Qual foi o total de vendas recentemente?",
            "sql_query": "SELECT SUM(amount) FROM sales WHERE date >= NOW() - INTERVAL 30 DAY",
            "response": "O total foi R$ 52.000"
        }
    ]
    
    print(f"\n📝 Pergunta Atual: {current_run['question']}")
    print(f"📝 Perguntas para Comparação:")
    for run in compared_runs:
        print(f"   - {run['question']}")
    
    result = await agent.validate_comparative(current_run, compared_runs)
    
    print("\n✅ Resultado da Validação Comparativa:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result

async def main():
    """Executa testes"""
    print("\n🚀 Iniciando testes de validação melhorada...")
    
    try:
        individual_result = await test_individual_validation()
        comparative_result = await test_comparative_validation()
        
        print("\n" + "="*80)
        print("✅ TESTES CONCLUÍDOS COM SUCESSO!")
        print("="*80)
        
        # Verificar se os campos esperados estão presentes
        print("\n📋 Verificação de Campos:")
        
        print("\nValidação Individual:")
        for field in ["question_clarity_score", "query_correctness_score", "response_accuracy_score", 
                      "overall_score", "issues_found", "observations", "suggestions", "improved_question"]:
            present = field in individual_result
            print(f"  {'✓' if present else '✗'} {field}")
        
        print("\nValidação Comparativa:")
        for field in ["consistency_score", "inconsistencies_found", "observations", "suggestions", "improved_question"]:
            present = field in comparative_result
            print(f"  {'✓' if present else '✗'} {field}")
            
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

