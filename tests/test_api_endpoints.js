#!/usr/bin/env node

/**
 * Script para testar todos os endpoints da AgentAPI
 * 
 * Requisitos: npm install axios form-data
 * Uso: node test_api_endpoints.js [BASE_URL]
 */

const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class APITester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.token = null;
        this.userData = null;
        
        // Configurar axios
        this.client = axios.create({
            baseURL: baseUrl,
            timeout: 30000,
        });
        
        // Interceptor para adicionar token automaticamente
        this.client.interceptors.request.use((config) => {
            if (this.token) {
                config.headers.Authorization = `Bearer ${this.token}`;
            }
            return config;
        });
        
        // Interceptor para log de respostas
        this.client.interceptors.response.use(
            (response) => {
                this.log(`✅ ${response.status} - ${response.config.method.toUpperCase()} ${response.config.url}`);
                return response;
            },
            (error) => {
                const status = error.response?.status || 'ERR';
                const message = error.response?.data?.detail || error.message;
                this.log(`❌ ${status} - ${error.config.method.toUpperCase()} ${error.config.url}: ${message}`, 'ERROR');
                throw error;
            }
        );
    }
    
    log(message, level = 'INFO') {
        const timestamp = new Date().toLocaleTimeString();
        const prefix = level === 'ERROR' ? '❌' : level === 'WARN' ? '⚠️' : 'ℹ️';
        console.log(`[${timestamp}] ${prefix} ${message}`);
    }
    
    async testRegister() {
        this.log('=== TESTANDO REGISTRO ===');
        
        const userData = {
            nome: 'Teste User',
            email: `teste_${Date.now()}@example.com`,
            password: 'senha123'
        };
        
        try {
            const response = await this.client.post('/auth/register', userData);
            this.userData = response.data;
            this.log(`Usuário criado: ${this.userData.nome} (${this.userData.email})`);
            return true;
        } catch (error) {
            return false;
        }
    }
    
    async testLogin() {
        this.log('=== TESTANDO LOGIN ===');
        
        if (!this.userData) {
            this.log('Erro: Usuário não foi criado', 'ERROR');
            return false;
        }
        
        const loginData = new URLSearchParams({
            username: this.userData.email,
            password: 'senha123'
        });
        
        try {
            const response = await this.client.post('/auth/login', loginData, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });
            
            this.token = response.data.access_token;
            this.log(`Login realizado. Token: ${this.token.substring(0, 20)}...`);
            return true;
        } catch (error) {
            return false;
        }
    }
    
    async testMe() {
        this.log('=== TESTANDO /auth/me ===');
        
        try {
            const response = await this.client.get('/auth/me');
            this.log(`Usuário atual: ${response.data.nome}`);
            return true;
        } catch (error) {
            return false;
        }
    }
    
    async testUploadDataset() {
        this.log('=== TESTANDO UPLOAD DATASET ===');
        
        // Criar CSV de teste
        const csvContent = `id,produto,valor,data
1,Produto A,100.50,2024-01-01
2,Produto B,200.75,2024-01-02
3,Produto C,150.25,2024-01-03
4,Produto D,300.00,2024-01-04
5,Produto E,75.25,2024-01-05`;
        
        const fileName = 'test_data.csv';
        fs.writeFileSync(fileName, csvContent);
        
        try {
            const formData = new FormData();
            formData.append('file', fs.createReadStream(fileName));
            formData.append('nome', 'Dataset de Teste');
            
            const response = await this.client.post('/datasets/upload', formData, {
                headers: formData.getHeaders()
            });
            
            const dataset = response.data;
            this.log(`Dataset criado: ID ${dataset.id}`);
            
            // Limpar arquivo temporário
            fs.unlinkSync(fileName);
            
            return dataset.id;
        } catch (error) {
            // Limpar arquivo em caso de erro
            if (fs.existsSync(fileName)) {
                fs.unlinkSync(fileName);
            }
            return null;
        }
    }
    
    async testCreateConnection(datasetId) {
        this.log('=== TESTANDO CRIAÇÃO CONEXÃO ===');
        
        const connectionData = {
            tipo: 'sqlite',
            dataset_id: datasetId
        };
        
        try {
            const response = await this.client.post('/connections/', connectionData);
            const connection = response.data;
            this.log(`Conexão criada: ID ${connection.id}`);
            return connection.id;
        } catch (error) {
            return null;
        }
    }
    
    async testCreateAgent(connectionId) {
        this.log('=== TESTANDO CRIAÇÃO AGENTE ===');
        
        const agentData = {
            nome: 'Agente de Teste',
            connection_id: connectionId,
            selected_model: 'gpt-3.5-turbo',
            top_k: 10,
            include_tables_key: '*',
            advanced_mode: false,
            processing_enabled: true,
            refinement_enabled: false,
            single_table_mode: false
        };
        
        try {
            const response = await this.client.post('/agents/', agentData);
            const agent = response.data;
            this.log(`Agente criado: ID ${agent.id}`);
            return agent.id;
        } catch (error) {
            return null;
        }
    }
    
    async testListAgents() {
        this.log('=== TESTANDO LISTAGEM AGENTES ===');
        
        try {
            const response = await this.client.get('/agents/');
            const agents = response.data;
            this.log(`Encontrados ${agents.length} agentes`);
            return true;
        } catch (error) {
            return false;
        }
    }
    
    async testRunAgent(agentId) {
        this.log('=== TESTANDO EXECUÇÃO AGENTE ===');
        
        const runData = {
            question: 'Qual é o valor total dos produtos?'
        };
        
        try {
            const response = await this.client.post(`/agents/${agentId}/run`, runData);
            const run = response.data;
            this.log(`Run criada: ID ${run.id}, Status: ${run.status}`);
            return run.id;
        } catch (error) {
            return null;
        }
    }
    
    async testGetRunResult(runId, maxAttempts = 30) {
        this.log('=== TESTANDO CONSULTA RESULTADO ===');
        
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                const response = await this.client.get(`/runs/${runId}`);
                const run = response.data;
                const status = run.status;
                
                this.log(`Tentativa ${attempt}: Status = ${status}`);
                
                if (status === 'success') {
                    this.log('✅ Execução concluída com sucesso!');
                    if (run.result_data) {
                        this.log(`Resposta: ${run.result_data.substring(0, 100)}...`);
                    }
                    if (run.sql_used) {
                        this.log(`SQL: ${run.sql_used}`);
                    }
                    return true;
                } else if (status === 'failure') {
                    this.log(`❌ Execução falhou: ${run.error_type || 'Erro desconhecido'}`, 'ERROR');
                    return false;
                } else if (['queued', 'running'].includes(status)) {
                    this.log(`⏳ Aguardando... (tentativa ${attempt}/${maxAttempts})`);
                    await new Promise(resolve => setTimeout(resolve, 2000));
                } else {
                    this.log(`Status desconhecido: ${status}`, 'ERROR');
                    return false;
                }
            } catch (error) {
                return false;
            }
        }
        
        this.log('❌ Timeout: Execução não finalizou no tempo esperado', 'ERROR');
        return false;
    }
    
    async testListRuns() {
        this.log('=== TESTANDO LISTAGEM RUNS ===');
        
        try {
            const response = await this.client.get('/runs/');
            const runs = response.data;
            this.log(`Encontradas ${runs.length} execuções`);
            return true;
        } catch (error) {
            return false;
        }
    }
    
    async runAllTests() {
        this.log('🚀 INICIANDO TESTES DA API');
        
        try {
            // 1. Registro
            if (!await this.testRegister()) return false;
            
            // 2. Login
            if (!await this.testLogin()) return false;
            
            // 3. Me
            if (!await this.testMe()) return false;
            
            // 4. Upload dataset
            const datasetId = await this.testUploadDataset();
            if (!datasetId) return false;
            
            // 5. Criar conexão
            const connectionId = await this.testCreateConnection(datasetId);
            if (!connectionId) return false;
            
            // 6. Criar agente
            const agentId = await this.testCreateAgent(connectionId);
            if (!agentId) return false;
            
            // 7. Listar agentes
            if (!await this.testListAgents()) return false;
            
            // 8. Executar agente
            const runId = await this.testRunAgent(agentId);
            if (!runId) return false;
            
            // 9. Consultar resultado
            if (!await this.testGetRunResult(runId)) return false;
            
            // 10. Listar runs
            if (!await this.testListRuns()) return false;
            
            this.log('🎉 TODOS OS TESTES PASSARAM!');
            return true;
        } catch (error) {
            this.log(`Erro inesperado: ${error.message}`, 'ERROR');
            return false;
        }
    }
}

async function main() {
    const baseUrl = process.argv[2] || 'http://localhost:8000';
    
    console.log('='.repeat(60));
    console.log('🧪 TESTE COMPLETO DA AGENTAPI (Node.js)');
    console.log('='.repeat(60));
    console.log(`Base URL: ${baseUrl}`);
    console.log('');
    
    const tester = new APITester(baseUrl);
    const success = await tester.runAllTests();
    
    console.log('');
    console.log('='.repeat(60));
    if (success) {
        console.log('✅ TODOS OS TESTES PASSARAM!');
        console.log('A API está funcionando corretamente.');
    } else {
        console.log('❌ ALGUNS TESTES FALHARAM!');
        console.log('Verifique os logs acima para detalhes.');
    }
    console.log('='.repeat(60));
    
    process.exit(success ? 0 : 1);
}

// Verificar dependências
try {
    require('axios');
    require('form-data');
} catch (error) {
    console.error('❌ Dependências não encontradas!');
    console.error('Execute: npm install axios form-data');
    process.exit(1);
}

if (require.main === module) {
    main().catch(console.error);
}
