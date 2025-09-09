#!/usr/bin/env python3
"""
Sistema de Testes Massivos para AgentGraph
Interface HTML isolada para testes de consistência e performance
"""
import os
import sys
import asyncio
import logging
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import json

# Adiciona o diretório pai ao path para importar módulos do AgentGraph
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testes.test_runner import MassiveTestRunner
from testes.test_validator import TestValidator
from testes.report_generator import ReportGenerator
from utils.config import AVAILABLE_MODELS

# Configuração do Flask
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Instância global do test runner
test_runner = None
current_test_session = None

@app.route('/')
def index():
    """Página principal do sistema de testes"""
    return render_template('index.html', 
                         available_models=AVAILABLE_MODELS)

@app.route('/api/models')
def get_models():
    """Retorna modelos disponíveis"""
    return jsonify({
        'success': True,
        'models': AVAILABLE_MODELS
    })

@app.route('/api/create_test_session', methods=['POST'])
def create_test_session():
    """Cria nova sessão de teste"""
    global current_test_session
    
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'success': False,
                'error': 'Pergunta é obrigatória'
            })
        
        # Cria nova sessão
        current_test_session = {
            'id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'question': question,
            'groups': [],
            'created_at': datetime.now().isoformat(),
            'status': 'created'
        }
        
        logging.info(f"Nova sessão de teste criada: {current_test_session['id']}")
        
        return jsonify({
            'success': True,
            'session_id': current_test_session['id'],
            'message': 'Sessão de teste criada com sucesso'
        })
        
    except Exception as e:
        logging.error(f"Erro ao criar sessão de teste: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/add_test_group', methods=['POST'])
def add_test_group():
    """Adiciona grupo de teste à sessão atual"""
    global current_test_session
    
    try:
        if not current_test_session:
            return jsonify({
                'success': False,
                'error': 'Nenhuma sessão de teste ativa'
            })
        
        data = request.json
        
        # Validação dos dados
        required_fields = ['sql_model', 'iterations']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field}'
                })
        
        sql_model = data['sql_model']
        iterations = int(data['iterations'])
        processing_enabled = data.get('processing_enabled', False)
        processing_model = data.get('processing_model', None)
        question_refinement_enabled = data.get('question_refinement_enabled', False)
        
        # Validações
        if sql_model not in AVAILABLE_MODELS.values():
            return jsonify({
                'success': False,
                'error': 'Modelo SQL inválido'
            })
        
        if iterations < 1 or iterations > 100:
            return jsonify({
                'success': False,
                'error': 'Número de iterações deve ser entre 1 e 100'
            })
        
        if processing_enabled and processing_model not in AVAILABLE_MODELS.values():
            return jsonify({
                'success': False,
                'error': 'Modelo de processamento inválido'
            })
        
        # Cria grupo
        group = {
            'id': len(current_test_session['groups']) + 1,
            'sql_model': sql_model,
            'sql_model_name': next(k for k, v in AVAILABLE_MODELS.items() if v == sql_model),
            'processing_enabled': processing_enabled,
            'processing_model': processing_model,
            'processing_model_name': next((k for k, v in AVAILABLE_MODELS.items() if v == processing_model), None) if processing_model else None,
            'question_refinement_enabled': question_refinement_enabled,
            'iterations': iterations,
            'created_at': datetime.now().isoformat()
        }
        
        current_test_session['groups'].append(group)
        
        logging.info(f"Grupo adicionado à sessão {current_test_session['id']}: {group}")
        
        return jsonify({
            'success': True,
            'group': group,
            'total_groups': len(current_test_session['groups']),
            'message': 'Grupo adicionado com sucesso'
        })
        
    except Exception as e:
        logging.error(f"Erro ao adicionar grupo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/get_session_info')
def get_session_info():
    """Retorna informações da sessão atual"""
    global current_test_session
    
    if not current_test_session:
        return jsonify({
            'success': False,
            'error': 'Nenhuma sessão ativa'
        })
    
    return jsonify({
        'success': True,
        'session': current_test_session
    })

@app.route('/api/run_tests', methods=['POST'])
def run_tests():
    """Executa os testes da sessão atual"""
    global test_runner, current_test_session
    
    try:
        if not current_test_session:
            return jsonify({
                'success': False,
                'error': 'Nenhuma sessão de teste ativa'
            })
        
        if not current_test_session['groups']:
            return jsonify({
                'success': False,
                'error': 'Nenhum grupo de teste configurado'
            })
        
        data = request.json
        validation_method = data.get('validation_method', 'llm')
        expected_content = data.get('expected_content', '') if validation_method == 'keyword' else None
        
        # Atualiza status
        current_test_session['status'] = 'running'
        current_test_session['started_at'] = datetime.now().isoformat()
        
        # Cria test runner
        test_runner = MassiveTestRunner(max_workers=5)  # Paralelismo de 5 workers

        # Executa testes de forma assíncrona
        def run_async_tests():
            print(f"\n🚀 INICIANDO EXECUÇÃO DE TESTES - {datetime.now().strftime('%H:%M:%S')}")
            print(f"📊 Sessão: {current_test_session['id']}")
            print(f"❓ Pergunta: {current_test_session['question']}")
            print(f"👥 Grupos: {len(current_test_session['groups'])}")
            print(f"🔢 Total de testes: {sum(g['iterations'] for g in current_test_session['groups'])}")
            print("=" * 60)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    test_runner.run_test_session(
                        current_test_session,
                        validation_method,
                        expected_content
                    )
                )
                # Marca como concluído após execução
                current_test_session['status'] = 'completed'
                current_test_session['completed_at'] = datetime.now().isoformat()

                print(f"\n🎉 TESTES CONCLUÍDOS COM SUCESSO - {datetime.now().strftime('%H:%M:%S')}")
                print(f"✅ Sessão: {current_test_session['id']}")
                print("=" * 60)

                logging.info(f"✅ Testes concluídos com sucesso: {current_test_session['id']}")
                return result
            except Exception as e:
                current_test_session['status'] = 'error'
                current_test_session['error'] = str(e)

                print(f"\n❌ ERRO NA EXECUÇÃO DOS TESTES - {datetime.now().strftime('%H:%M:%S')}")
                print(f"💥 Erro: {e}")
                print("=" * 60)

                logging.error(f"❌ Erro na execução dos testes: {e}")
                raise
            finally:
                loop.close()

        # Inicia execução em thread separada
        import threading
        test_thread = threading.Thread(target=run_async_tests)
        test_thread.daemon = False  # Não daemon para garantir conclusão
        test_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Testes iniciados com sucesso',
            'session_id': current_test_session['id']
        })
        
    except Exception as e:
        logging.error(f"Erro ao executar testes: {e}")
        current_test_session['status'] = 'error'
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/test_status')
def get_test_status():
    """Retorna status atual dos testes"""
    global test_runner, current_test_session

    if not current_test_session:
        return jsonify({
            'success': False,
            'error': 'Nenhuma sessão ativa'
        })

    status_info = {
        'session_id': current_test_session['id'],
        'status': current_test_session.get('status', 'unknown'),
        'progress': 0,
        'current_group': None,
        'completed_tests': 0,
        'total_tests': sum(group['iterations'] for group in current_test_session['groups']),
        'estimated_remaining': None
    }

    if test_runner:
        try:
            runner_status = test_runner.get_status()
            status_info.update(runner_status)

            # Se o runner indica que terminou, atualiza a sessão
            if runner_status.get('current_status') == 'completed' and current_test_session.get('status') != 'completed':
                current_test_session['status'] = 'completed'
                current_test_session['completed_at'] = datetime.now().isoformat()
                logging.info(f"🎉 Sessão {current_test_session['id']} marcada como concluída")

        except Exception as e:
            logging.error(f"Erro ao obter status do runner: {e}")
            status_info['error'] = str(e)

    # Adiciona informações de testes em execução
    if test_runner:
        status_info['running_tests'] = runner_status.get('running_tests_details', [])
        status_info['running_tests_count'] = runner_status.get('running_tests_count', 0)
        status_info['current_test'] = runner_status.get('current_test')
        status_info['cancelled_tests'] = len(runner_status.get('cancelled_tests', []))
        status_info['timeout_tests'] = len(runner_status.get('timeout_tests', []))

    return jsonify({
        'success': True,
        'status': status_info
    })

@app.route('/api/cancel_test', methods=['POST'])
def cancel_current_test():
    """Cancela o teste atual ou específico"""
    global test_runner

    if not test_runner:
        return jsonify({
            'success': False,
            'error': 'Nenhum teste em execução'
        })

    try:
        data = request.get_json() or {}
        thread_id = data.get('thread_id')  # Opcional - cancela teste específico

        cancelled = test_runner.cancel_current_test(thread_id)

        if cancelled:
            return jsonify({
                'success': True,
                'message': f'Teste {"específico" if thread_id else "atual"} cancelado com sucesso',
                'cancelled_test': thread_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Nenhum teste encontrado para cancelar'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao cancelar teste: {str(e)}'
        })

@app.route('/api/cancel_all_tests', methods=['POST'])
def cancel_all_tests():
    """Cancela todos os testes em execução"""
    global test_runner

    if not test_runner:
        return jsonify({
            'success': False,
            'error': 'Nenhum teste em execução'
        })

    try:
        cancelled_count = test_runner.cancel_all_tests()

        return jsonify({
            'success': True,
            'message': f'{cancelled_count} testes cancelados',
            'cancelled_count': cancelled_count
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao cancelar testes: {str(e)}'
        })

@app.route('/api/skip_stuck_tests', methods=['POST'])
def skip_stuck_tests():
    """Marca testes travados para cancelamento"""
    global test_runner

    if not test_runner:
        return jsonify({
            'success': False,
            'error': 'Nenhum teste em execução'
        })

    try:
        data = request.get_json() or {}
        max_duration = data.get('max_duration', 120)  # 2 minutos padrão

        stuck_count = test_runner.skip_stuck_tests(max_duration)

        return jsonify({
            'success': True,
            'message': f'{stuck_count} testes travados marcados para cancelamento',
            'stuck_count': stuck_count,
            'max_duration': max_duration
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao marcar testes travados: {str(e)}'
        })

@app.route('/api/test_results')
def get_test_results():
    """Retorna resultados dos testes"""
    global test_runner, current_test_session

    if not test_runner:
        return jsonify({
            'success': False,
            'error': 'Nenhum teste executado'
        })

    if not current_test_session:
        return jsonify({
            'success': False,
            'error': 'Nenhuma sessão ativa'
        })

    try:
        results = test_runner.get_results()

        # Verifica se há resultados válidos
        if not results or not results.get('group_results'):
            return jsonify({
                'success': False,
                'error': 'Resultados ainda não disponíveis'
            })

        logging.info(f"📊 Enviando resultados: {len(results.get('group_results', []))} grupos, {len(results.get('individual_results', []))} testes individuais")

        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logging.error(f"Erro ao obter resultados: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/download_csv')
def download_csv():
    """Gera e baixa relatório CSV"""
    global test_runner
    
    if not test_runner:
        return jsonify({
            'success': False,
            'error': 'Nenhum teste executado'
        })
    
    try:
        # Gera relatório
        report_generator = ReportGenerator()
        csv_path = report_generator.generate_csv_report(test_runner.get_results())
        
        return send_file(
            csv_path,
            as_attachment=True,
            download_name=f'teste_agentgraph_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        logging.error(f"Erro ao gerar CSV: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    print("🧪 Sistema de Testes Massivos - AgentGraph")
    print("=" * 50)
    print("🌐 Acesse: http://localhost:5001")
    print("📊 Interface de testes disponível")
    print("=" * 50)
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        threaded=True
    )
