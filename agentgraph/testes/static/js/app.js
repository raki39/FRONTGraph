// Sistema de Testes Massivos - JavaScript
class TestManager {
    constructor() {
        this.sessionId = null;
        this.groups = [];
        this.isRunning = false;
        this.statusInterval = null;
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // Criar sessão
        document.getElementById('createSession').addEventListener('click', () => {
            this.createSession();
        });
        
        // Toggle Processing Agent
        document.getElementById('enableProcessing').addEventListener('change', (e) => {
            const processingDiv = document.getElementById('processingModelDiv');
            processingDiv.style.display = e.target.checked ? 'block' : 'none';
        });
        
        // Toggle método de validação
        document.getElementById('validationMethod').addEventListener('change', (e) => {
            const keywordDiv = document.getElementById('keywordDiv');
            keywordDiv.style.display = e.target.value === 'keyword' ? 'block' : 'none';
        });
        
        // Adicionar grupo
        document.getElementById('addGroup').addEventListener('click', () => {
            this.addGroup();
        });
        
        // Executar testes
        document.getElementById('runTests').addEventListener('click', () => {
            this.runTests();
        });
        
        // Download CSV
        document.getElementById('downloadCsv').addEventListener('click', () => {
            this.downloadCsv();
        });
    }
    
    async createSession() {
        const question = document.getElementById('testQuestion').value.trim();
        
        if (!question) {
            this.showAlert('Por favor, digite uma pergunta para o teste.', 'warning');
            return;
        }
        
        try {
            const response = await fetch('/api/create_test_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.sessionId = data.session_id;
                this.showSessionInfo(question);
                
                // Mostra configuração de grupo
                document.getElementById('groupConfig').style.display = 'block';
                document.getElementById('validationConfig').style.display = 'block';
                
                // Desabilita criação de nova sessão
                document.getElementById('createSession').disabled = true;
                document.getElementById('testQuestion').disabled = true;
                
            } else {
                this.showAlert(data.error, 'danger');
            }
        } catch (error) {
            this.showAlert('Erro ao criar sessão: ' + error.message, 'danger');
        }
    }
    
    showSessionInfo(question) {
        const sessionInfo = document.getElementById('sessionInfo');
        const sessionDetails = document.getElementById('sessionDetails');
        
        sessionDetails.innerHTML = `
            <strong>ID:</strong> ${this.sessionId}<br>
            <strong>Pergunta:</strong> ${question}<br>
            <strong>Criado em:</strong> ${new Date().toLocaleString()}
        `;
        
        sessionInfo.style.display = 'block';
    }
    
    async addGroup() {
        const sqlModel = document.getElementById('sqlModel').value;
        const processingEnabled = document.getElementById('enableProcessing').checked;
        const processingModel = processingEnabled ? document.getElementById('processingModel').value : null;
        const questionRefinementEnabled = document.getElementById('enableQuestionRefinement').checked;
        const iterations = parseInt(document.getElementById('iterations').value);

        if (iterations < 1 || iterations > 100) {
            this.showAlert('Número de iterações deve ser entre 1 e 100.', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/add_test_group', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    sql_model: sqlModel,
                    processing_enabled: processingEnabled,
                    processing_model: processingModel,
                    question_refinement_enabled: questionRefinementEnabled,
                    iterations: iterations
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.groups.push(data.group);
                this.updateGroupsList();
                
                // Reset form
                document.getElementById('iterations').value = 5;
                document.getElementById('enableProcessing').checked = false;
                document.getElementById('processingModelDiv').style.display = 'none';
                
            } else {
                this.showAlert(data.error, 'danger');
            }
        } catch (error) {
            this.showAlert('Erro ao adicionar grupo: ' + error.message, 'danger');
        }
    }
    
    updateGroupsList() {
        const groupsList = document.getElementById('groupsList');
        
        if (this.groups.length === 0) {
            groupsList.innerHTML = '<p class="text-muted">Nenhum grupo configurado ainda.</p>';
            return;
        }
        
        let html = '';
        this.groups.forEach(group => {
            html += `
                <div class="test-group-card">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6><i class="fas fa-cog"></i> Grupo ${group.id}</h6>
                            <small class="text-muted">
                                <strong>SQL:</strong> ${group.sql_model_name}<br>
                                <strong>Processing:</strong> ${group.processing_enabled ? group.processing_model_name : 'Desativado'}<br>
                                <strong>Question Refinement:</strong> ${group.question_refinement_enabled ? 'Ativo (GPT-4o)' : 'Desativado'}<br>
                                <strong>Iterações:</strong> ${group.iterations}
                            </small>
                        </div>
                        <div class="text-end">
                            <span class="badge bg-primary">${group.iterations} testes</span>
                        </div>
                    </div>
                </div>
            `;
        });
        
        groupsList.innerHTML = html;
    }
    
    async runTests() {
        if (this.groups.length === 0) {
            this.showAlert('Adicione pelo menos um grupo de teste.', 'warning');
            return;
        }
        
        const validationMethod = document.getElementById('validationMethod').value;
        const expectedContent = document.getElementById('expectedContent').value;
        
        if (validationMethod === 'keyword' && !expectedContent.trim()) {
            this.showAlert('Digite o conteúdo esperado para validação por palavra-chave.', 'warning');
            return;
        }
        
        try {
            const response = await fetch('/api/run_tests', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    validation_method: validationMethod,
                    expected_content: expectedContent
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.isRunning = true;
                this.updateStatus('running');
                this.showProgressContainer();
                this.startStatusPolling();
                
                // Desabilita controles
                document.getElementById('addGroup').disabled = true;
                document.getElementById('runTests').disabled = true;
                
            } else {
                this.showAlert(data.error, 'danger');
            }
        } catch (error) {
            this.showAlert('Erro ao executar testes: ' + error.message, 'danger');
        }
    }
    
    showProgressContainer() {
        document.getElementById('progressContainer').style.display = 'block';
    }
    
    startStatusPolling() {
        this.statusInterval = setInterval(() => {
            this.checkTestStatus();
        }, 2000); // Verifica a cada 2 segundos
    }
    
    async checkTestStatus() {
        try {
            const response = await fetch('/api/test_status');
            const data = await response.json();

            if (data.success) {
                const status = data.status;

                // Atualiza progresso
                this.updateProgress(status);

                // Log para debug
                console.log('Status atual:', status.status, 'Progresso:', status.progress);

                // Verifica se terminou
                if (status.status === 'completed') {
                    this.isRunning = false;
                    this.updateStatus('completed');
                    clearInterval(this.statusInterval);
                    this.statusInterval = null;

                    console.log('✅ Testes concluídos, carregando resultados...');
                    await this.loadResults();
                    this.showAlert('Testes concluídos com sucesso!', 'success');

                    // Reabilita controles
                    document.getElementById('addGroup').disabled = false;
                    document.getElementById('runTests').disabled = false;

                } else if (status.status === 'error') {
                    this.isRunning = false;
                    this.updateStatus('error');
                    clearInterval(this.statusInterval);
                    this.statusInterval = null;
                    this.showAlert('Erro durante execução dos testes.', 'danger');

                    // Reabilita controles
                    document.getElementById('addGroup').disabled = false;
                    document.getElementById('runTests').disabled = false;
                }
            } else {
                console.error('Erro na resposta do status:', data.error);
            }
        } catch (error) {
            console.error('Erro ao verificar status:', error);
            // Para o polling em caso de erro persistente
            if (this.statusInterval) {
                clearInterval(this.statusInterval);
                this.statusInterval = null;
                this.showAlert('Erro de comunicação com o servidor.', 'danger');
            }
        }
    }
    
    updateProgress(status) {
        const progressBar = document.getElementById('progressBar');
        const completedTests = document.getElementById('completedTests');
        const totalTests = document.getElementById('totalTests');
        const currentGroup = document.getElementById('currentGroup');
        const estimatedTime = document.getElementById('estimatedTime');

        progressBar.style.width = status.progress + '%';
        progressBar.textContent = Math.round(status.progress) + '%';

        completedTests.textContent = status.completed_tests;
        totalTests.textContent = status.total_tests;
        currentGroup.textContent = status.current_group || '-';

        if (status.estimated_remaining) {
            const minutes = Math.floor(status.estimated_remaining / 60);
            const seconds = Math.floor(status.estimated_remaining % 60);
            estimatedTime.textContent = `${minutes}m ${seconds}s`;
        } else {
            estimatedTime.textContent = '-';
        }

        // Atualiza informações de testes em execução
        this.updateRunningTests(status);
    }

    updateRunningTests(status) {
        const currentTestDetails = document.getElementById('currentTestDetails');
        const runningTestsCount = document.getElementById('runningTestsCount');
        const runningTestsList = document.getElementById('runningTestsList');
        const runningTestsContainer = document.getElementById('runningTestsContainer');

        // Atualiza contador
        const runningCount = status.running_tests_count || 0;
        runningTestsCount.textContent = runningCount;
        runningTestsCount.className = runningCount > 0 ? 'badge bg-primary' : 'badge bg-secondary';

        // Atualiza teste atual
        if (status.current_test) {
            currentTestDetails.innerHTML = `
                <span class="badge bg-info">${status.current_test}</span>
                <small class="text-muted d-block">Teste em execução</small>
            `;
        } else {
            currentTestDetails.innerHTML = '<span class="text-muted">Nenhum teste em execução</span>';
        }

        // Atualiza lista de testes em execução
        if (runningCount > 0 && status.running_tests) {
            runningTestsList.style.display = 'block';
            runningTestsContainer.innerHTML = '';

            status.running_tests.forEach(test => {
                const duration = Math.floor((Date.now() / 1000) - test.start_time);
                const minutes = Math.floor(duration / 60);
                const seconds = duration % 60;

                const testElement = document.createElement('div');
                testElement.className = 'list-group-item d-flex justify-content-between align-items-center';
                testElement.innerHTML = `
                    <div>
                        <strong>Grupo ${test.group_id}</strong> - Iteração ${test.iteration}
                    </div>
                    <div class="text-end">
                        <span class="badge bg-warning">${minutes}m ${seconds}s</span>
                        <button class="btn btn-sm btn-outline-danger ms-2" onclick="testManager.cancelSpecificTest('${test.thread_id}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                runningTestsContainer.appendChild(testElement);
            });
        } else {
            runningTestsList.style.display = 'none';
        }

        // Habilita/desabilita botões
        const hasRunningTests = runningCount > 0;
        document.getElementById('cancelCurrentBtn').disabled = !hasRunningTests;
        document.getElementById('cancelAllBtn').disabled = !hasRunningTests;
        document.getElementById('skipStuckBtn').disabled = !hasRunningTests;
    }

    async cancelCurrentTest() {
        try {
            const response = await fetch('/api/cancel_test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showAlert(data.message, 'success');
            } else {
                this.showAlert(data.error, 'danger');
            }
        } catch (error) {
            this.showAlert('Erro ao cancelar teste: ' + error.message, 'danger');
        }
    }

    async cancelSpecificTest(threadId) {
        try {
            const response = await fetch('/api/cancel_test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ thread_id: threadId })
            });

            const data = await response.json();

            if (data.success) {
                this.showAlert(data.message, 'success');
            } else {
                this.showAlert(data.error, 'danger');
            }
        } catch (error) {
            this.showAlert('Erro ao cancelar teste específico: ' + error.message, 'danger');
        }
    }

    async cancelAllTests() {
        if (!confirm('Tem certeza que deseja cancelar TODOS os testes em execução?')) {
            return;
        }

        try {
            const response = await fetch('/api/cancel_all_tests', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showAlert(data.message, 'warning');
            } else {
                this.showAlert(data.error, 'danger');
            }
        } catch (error) {
            this.showAlert('Erro ao cancelar todos os testes: ' + error.message, 'danger');
        }
    }

    async skipStuckTests() {
        try {
            const response = await fetch('/api/skip_stuck_tests', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ max_duration: 120 })
            });

            const data = await response.json();

            if (data.success) {
                this.showAlert(data.message, 'info');
            } else {
                this.showAlert(data.error, 'danger');
            }
        } catch (error) {
            this.showAlert('Erro ao pular testes travados: ' + error.message, 'danger');
        }
    }
    
    async loadResults() {
        try {
            console.log('🔄 Carregando resultados...');
            const response = await fetch('/api/test_results');
            const data = await response.json();

            console.log('📊 Resposta dos resultados:', data);

            if (data.success) {
                console.log('✅ Resultados carregados, exibindo...');
                this.displayResults(data.results);
                document.getElementById('resultsContainer').style.display = 'block';
                console.log('✅ Interface de resultados exibida');
            } else {
                console.error('❌ Erro nos resultados:', data.error);
                this.showAlert('Erro ao carregar resultados: ' + data.error, 'danger');
            }
        } catch (error) {
            console.error('❌ Erro ao carregar resultados:', error);
            this.showAlert('Erro ao carregar resultados: ' + error.message, 'danger');
        }
    }
    
    displayResults(results) {
        this.displaySummary(results.summary);
        this.displayGroupResults(results.group_results);
        this.displayIndividualResults(results.individual_results);
    }
    
    displaySummary(summary) {
        const summaryContent = document.getElementById('summaryContent');
        
        summaryContent.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${summary.total_tests}</div>
                        <div class="metric-label">Total de Testes</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${summary.overall_success_rate}%</div>
                        <div class="metric-label">Taxa de Sucesso</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${summary.overall_validation_rate}%</div>
                        <div class="metric-label">Taxa de Validação</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${summary.avg_response_consistency}%</div>
                        <div class="metric-label">Consistência Média</div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-6">
                    <h6>🏆 Melhor Grupo (Validação)</h6>
                    <div class="card">
                        <div class="card-body">
                            <strong>Grupo ${summary.best_performing_group.group_id}</strong><br>
                            <small>
                                ${summary.best_performing_group.group_config.sql_model_name}<br>
                                Processing: ${summary.best_performing_group.group_config.processing_enabled ? 'Ativo' : 'Inativo'}<br>
                                Taxa: ${summary.best_performing_group.validation_rate}%
                            </small>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6>🎯 Grupo Mais Consistente</h6>
                    <div class="card">
                        <div class="card-body">
                            <strong>Grupo ${summary.most_consistent_group.group_id}</strong><br>
                            <small>
                                ${summary.most_consistent_group.group_config.sql_model_name}<br>
                                Processing: ${summary.most_consistent_group.group_config.processing_enabled ? 'Ativo' : 'Inativo'}<br>
                                Consistência: ${summary.most_consistent_group.validation_consistency}%
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    displayGroupResults(groupResults) {
        const groupsContent = document.getElementById('groupsContent');
        
        let html = '<div class="table-responsive"><table class="table table-striped"><thead><tr>';
        html += '<th>Grupo</th><th>Modelo SQL</th><th>Processing</th><th>Testes</th>';
        html += '<th>Sucesso</th><th>Validação</th><th>Consistência</th><th>Tempo Médio</th>';
        html += '</tr></thead><tbody>';
        
        groupResults.forEach(group => {
            const config = group.group_config;
            html += `
                <tr>
                    <td><strong>${group.group_id}</strong></td>
                    <td>${config.sql_model_name}</td>
                    <td>${config.processing_enabled ? config.processing_model_name : 'Não'}</td>
                    <td>${group.total_tests}</td>
                    <td><span class="badge bg-${group.success_rate >= 80 ? 'success' : group.success_rate >= 60 ? 'warning' : 'danger'}">${group.success_rate}%</span></td>
                    <td><span class="badge bg-${group.validation_rate >= 80 ? 'success' : group.validation_rate >= 60 ? 'warning' : 'danger'}">${group.validation_rate}%</span></td>
                    <td>${group.validation_consistency}%</td>
                    <td>${group.avg_execution_time}s</td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        groupsContent.innerHTML = html;
    }
    
    displayIndividualResults(individualResults) {
        const individualContent = document.getElementById('individualContent');
        
        let html = '<div class="table-responsive"><table class="table table-sm"><thead><tr>';
        html += '<th>Grupo</th><th>Iter.</th><th>Modelo SQL</th><th>Processing</th><th>QR</th><th>Sucesso</th><th>Validação</th><th>Tempo</th><th>Ações</th>';
        html += '</tr></thead><tbody>';

        individualResults.slice(0, 100).forEach((result, index) => { // Limita a 100 para performance
            const validation = result.validation || {};
            const processingBadge = result.processing_enabled
                ? `<span class="badge bg-info" title="${result.processing_model || 'N/A'}">Sim</span>`
                : '<span class="badge bg-secondary">Não</span>';

            const qrBadge = result.question_refinement_enabled
                ? '<span class="badge bg-warning" title="Question Refinement ativo">QR</span>'
                : '<span class="badge bg-secondary">-</span>';

            html += `
                <tr>
                    <td><strong>${result.group_id}</strong></td>
                    <td>${result.iteration}</td>
                    <td><small class="text-primary">${result.sql_model}</small></td>
                    <td>${processingBadge}</td>
                    <td>${qrBadge}</td>
                    <td><span class="badge bg-${result.success ? 'success' : 'danger'}">${result.success ? 'Sim' : 'Não'}</span></td>
                    <td><span class="badge bg-${validation.valid ? 'success' : 'danger'}">${validation.score || 0}%</span></td>
                    <td><small>${result.execution_time}s</small></td>
                    <td><button class="btn btn-sm btn-outline-primary" onclick="testManager.showResultDetails(${index})">
                        <i class="fas fa-eye"></i> Detalhes
                    </button></td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        
        if (individualResults.length > 100) {
            html += `<p class="text-muted mt-2">Mostrando primeiros 100 de ${individualResults.length} resultados. Baixe o CSV para ver todos.</p>`;
        }
        
        individualContent.innerHTML = html;
        
        // Armazena resultados para detalhes
        this.individualResults = individualResults;
    }
    
    showResultDetails(index) {
        const result = this.individualResults[index];
        const validation = result.validation || {};
        
        // Determina qual pergunta mostrar
        const questionToShow = result.question_refinement_enabled && result.refined_question
            ? result.refined_question
            : (result.original_question || result.question || 'N/A');

        const isRefined = result.question_refinement_enabled && result.question_refinement_applied;

        const modal = `
            <div class="modal fade" id="resultModal" tabindex="-1">
                <div class="modal-dialog" style="max-width: 1200px; margin: 2rem auto;">
                    <div class="modal-content" style="max-height: 85vh; overflow: hidden;">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-microscope"></i>
                                Análise Detalhada - Grupo ${result.group_id}, Iteração ${result.iteration}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                        </div>
                        <div class="modal-body" style="padding: 1.5rem;">
                            <!-- Pergunta do Teste -->
                            <div class="card mb-3">
                                <div class="card-header">
                                    <h6 class="mb-0">
                                        <i class="fas fa-question-circle"></i>
                                        Pergunta ${isRefined ? 'Refinada' : 'Original'}
                                        ${isRefined ? '<span class="badge bg-warning ms-2">Refinada por GPT-4o</span>' : ''}
                                    </h6>
                                </div>
                                <div class="card-body" style="padding: 1rem;">
                                    <div class="question-text" style="font-size: 1.1em; line-height: 1.4; color: #2c3e50;">
                                        "${questionToShow}"
                                    </div>
                                    ${isRefined && result.original_question ? `
                                        <hr style="margin: 1rem 0;">
                                        <small class="text-muted">Pergunta original:</small>
                                        <div class="small text-muted" style="font-style: italic;">
                                            "${result.original_question}"
                                        </div>
                                        ${result.question_refinement_changes && result.question_refinement_changes.length > 0 ? `
                                            <small class="text-muted mt-2 d-block">Mudanças aplicadas:</small>
                                            <div class="small text-info">
                                                ${result.question_refinement_changes.join(', ')}
                                            </div>
                                        ` : ''}
                                    ` : ''}
                                </div>
                            </div>

                            <!-- Configuração em Cards -->
                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <div class="card h-100">
                                        <div class="card-header">
                                            <h6 class="mb-0"><i class="fas fa-cog"></i> Configuração do Teste</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="row">
                                                <div class="col-6">
                                                    <small class="text-muted">Modelo SQL</small>
                                                    <div class="fw-bold text-primary">${result.sql_model}</div>
                                                </div>
                                                <div class="col-6">
                                                    <small class="text-muted">Processing Agent</small>
                                                    <div class="fw-bold ${result.processing_enabled ? 'text-info' : 'text-secondary'}">
                                                        ${result.processing_enabled ? result.processing_model : 'Desativado'}
                                                    </div>
                                                </div>
                                                <div class="col-6">
                                                    <small class="text-muted">Question Refinement</small>
                                                    <div class="fw-bold ${result.question_refinement_enabled ? 'text-warning' : 'text-secondary'}">
                                                        ${result.question_refinement_enabled ? 'GPT-4o' : 'Desativado'}
                                                    </div>
                                                </div>
                                            </div>
                                            <hr class="my-2">
                                            <div class="row">
                                                <div class="col-6">
                                                    <small class="text-muted">Tempo de Execução</small>
                                                    <div class="fw-bold">${result.execution_time}s</div>
                                                </div>
                                                <div class="col-6">
                                                    <small class="text-muted">Status</small>
                                                    <div><span class="badge ${this.getStatusBadgeClass(result.status)}">${result.status || 'Concluído'}</span></div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card h-100">
                                        <div class="card-header">
                                            <h6 class="mb-0"><i class="fas fa-check-circle"></i> Resultado da Validação</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="text-center mb-3">
                                                <div class="display-6 fw-bold ${validation.valid ? 'text-success' : 'text-danger'}">
                                                    ${validation.score || 0}%
                                                </div>
                                                <small class="text-muted">Pontuação de Validação</small>
                                            </div>
                                            <div class="text-center">
                                                <span class="badge ${validation.valid ? 'bg-success' : 'bg-danger'} fs-6">
                                                    ${validation.valid ? '✓ Válida' : '✗ Inválida'}
                                                </span>
                                            </div>
                                            ${validation.reason ? `
                                                <hr class="my-2">
                                                <small class="text-muted">Razão:</small>
                                                <div class="small">${validation.reason}</div>
                                            ` : ''}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Query SQL -->
                            <div class="card mb-3">
                                <div class="card-header">
                                    <h6 class="mb-0"><i class="fas fa-database"></i> Query SQL Gerada</h6>
                                </div>
                                <div class="card-body">
                                    <div class="modal-code-block">${this.formatSqlQuery(result.sql_query) || '<em class="text-muted">Nenhuma query SQL gerada</em>'}</div>
                                </div>
                            </div>

                            <!-- Resposta -->
                            <div class="card mb-3">
                                <div class="card-header">
                                    <h6 class="mb-0"><i class="fas fa-reply"></i> Resposta do Sistema</h6>
                                </div>
                                <div class="card-body">
                                    <div class="modal-response-block">${this.formatResponse(result.response) || '<em class="text-muted">Nenhuma resposta gerada</em>'}</div>
                                </div>
                            </div>

                            ${result.error ? `
                                <div class="card">
                                    <div class="card-header">
                                        <h6 class="mb-0"><i class="fas fa-exclamation-triangle"></i> Erro Detectado</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="alert alert-danger mb-0">${result.error}</div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times"></i> Fechar
                            </button>
                            <button type="button" class="btn btn-primary" onclick="testManager.copyTestDetails(${JSON.stringify(result).replace(/"/g, '&quot;')})">
                                <i class="fas fa-copy"></i> Copiar Detalhes
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove modal anterior se existir
        const existingModal = document.getElementById('resultModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Adiciona novo modal
        document.body.insertAdjacentHTML('beforeend', modal);
        
        // Mostra modal
        const modalElement = new bootstrap.Modal(document.getElementById('resultModal'));
        modalElement.show();
    }

    getStatusBadgeClass(status) {
        switch(status?.toLowerCase()) {
            case 'sucesso':
            case 'success':
                return 'bg-success';
            case 'erro':
            case 'error':
                return 'bg-danger';
            case 'cancelado':
            case 'cancelled':
                return 'bg-warning';
            case 'timeout':
                return 'bg-secondary';
            default:
                return 'bg-primary';
        }
    }

    formatSqlQuery(query) {
        if (!query) return null;

        // Remove espaços extras e formata SQL básico
        return query
            .replace(/\s+/g, ' ')
            .replace(/SELECT/gi, 'SELECT')
            .replace(/FROM/gi, '\nFROM')
            .replace(/WHERE/gi, '\nWHERE')
            .replace(/GROUP BY/gi, '\nGROUP BY')
            .replace(/ORDER BY/gi, '\nORDER BY')
            .replace(/HAVING/gi, '\nHAVING')
            .replace(/LIMIT/gi, '\nLIMIT')
            .trim();
    }

    formatResponse(response) {
        if (!response) return null;

        // Se for um número simples, formata melhor
        if (/^\d+$/.test(response.trim())) {
            return `<span class="display-6 text-primary fw-bold">${response}</span>`;
        }

        // Se for JSON, tenta formatar
        try {
            const parsed = JSON.parse(response);
            return `<pre class="json-formatted">${JSON.stringify(parsed, null, 2)}</pre>`;
        } catch (e) {
            // Retorna como texto normal
            return response;
        }
    }

    copyTestDetails(result) {
        const details = `
DETALHES DO TESTE
================
Grupo: ${result.group_id}
Iteração: ${result.iteration}
Modelo SQL: ${result.sql_model}
Processing Agent: ${result.processing_enabled ? result.processing_model : 'Desativado'}
Question Refinement: ${result.question_refinement_enabled ? 'Ativo (GPT-4o)' : 'Desativado'}
Tempo: ${result.execution_time}s
Status: ${result.status || 'Concluído'}

QUERY SQL:
${result.sql_query || 'N/A'}

RESPOSTA:
${result.response || 'N/A'}

VALIDAÇÃO:
Válida: ${result.validation?.valid ? 'Sim' : 'Não'}
Pontuação: ${result.validation?.score || 0}%
Razão: ${result.validation?.reason || 'N/A'}

${result.error ? `ERRO:\n${result.error}` : ''}
        `.trim();

        navigator.clipboard.writeText(details).then(() => {
            this.showAlert('Detalhes copiados para a área de transferência!', 'success');
        }).catch(() => {
            this.showAlert('Erro ao copiar detalhes', 'danger');
        });
    }

    async downloadCsv() {
        try {
            const response = await fetch('/api/download_csv');
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `teste_agentgraph_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showAlert('Relatório baixado com sucesso!', 'success');
            } else {
                this.showAlert('Erro ao baixar relatório.', 'danger');
            }
        } catch (error) {
            this.showAlert('Erro ao baixar relatório: ' + error.message, 'danger');
        }
    }
    
    updateStatus(status) {
        const statusElement = document.getElementById('sessionStatus');
        statusElement.className = `status-badge status-${status}`;
        
        const statusText = {
            'idle': 'Aguardando',
            'running': 'Executando',
            'completed': 'Concluído',
            'error': 'Erro'
        };
        
        const statusIcon = {
            'idle': 'circle',
            'running': 'spinner fa-spin',
            'completed': 'check-circle',
            'error': 'exclamation-circle'
        };
        
        statusElement.innerHTML = `<i class="fas fa-${statusIcon[status]}"></i> ${statusText[status]}`;
    }
    
    showAlert(message, type) {
        // Remove alertas anteriores
        const existingAlerts = document.querySelectorAll('.alert-dismissible');
        existingAlerts.forEach(alert => alert.remove());
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.querySelector('.container-fluid').insertBefore(alert, document.querySelector('.row'));
        
        // Remove automaticamente após 5 segundos
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
}

// Inicializa o sistema
const testManager = new TestManager();

// Funções globais para os botões HTML
function cancelCurrentTest() {
    testManager.cancelCurrentTest();
}

function cancelAllTests() {
    testManager.cancelAllTests();
}

function skipStuckTests() {
    testManager.skipStuckTests();
}
