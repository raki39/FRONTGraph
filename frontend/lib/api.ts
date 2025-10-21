import axios from 'axios'
import Cookies from 'js-cookie'
import toast from 'react-hot-toast'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

// Criar instância do axios
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para adicionar token automaticamente
api.interceptors.request.use((config) => {
  const token = Cookies.get('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor para tratar erros
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove('token')
      Cookies.remove('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Tipos
export interface User {
  id: number
  nome: string
  email: string
  empresa_id?: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Connection {
  id: number
  tipo: string
  db_uri?: string
  pg_dsn?: string
  created_at: string
}

export interface Agent {
  id: number
  nome: string
  connection_id: number
  selected_model: string
  top_k: number
  include_tables_key: string
  advanced_mode: boolean
  processing_enabled: boolean
  refinement_enabled: boolean
  single_table_mode: boolean
  selected_table?: string
  created_at: string
  connection?: Connection
}

export interface Run {
  id: number
  agent_id: number
  user_id: number
  question: string
  task_id?: string
  sql_used?: string
  result_data?: string
  status: string
  execution_ms?: number
  result_rows_count?: number
  error_type?: string
  created_at: string
  finished_at?: string
  chat_session_id?: number
}

export interface PaginationInfo {
  page: number
  per_page: number
  total_items: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface PaginatedRunsResponse {
  runs: Run[]
  pagination: PaginationInfo
}

export interface ChatSession {
  id: number
  user_id: number
  agent_id: number
  title: string
  created_at: string
  last_activity: string
  total_messages: number
  status: string
  context_summary?: string
  last_message?: string
}

export interface ChatSessionListItem {
  id: number
  title: string
  last_message?: string
  messages_count: number
  updated_at: string
  status: string
  agent_id: number
}

export interface ChatSessionListResponse {
  sessions: ChatSessionListItem[]
  pagination: PaginationInfo
}

export interface Message {
  id: number
  chat_session_id: number
  run_id: number
  role: 'user' | 'assistant'
  content: string
  sql_query?: string
  created_at: string
  sequence_order: number
  message_metadata?: any
}

export interface MessagesResponse {
  messages: Message[]
  pagination: PaginationInfo
  session_info: {
    id: number
    title: string
    total_messages: number
  }
}

// API Functions
export const authAPI = {
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)
    
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  register: async (nome: string, email: string, password: string): Promise<User> => {
    const response = await api.post('/auth/register', { nome, email, password })
    return response.data
  },

  me: async (): Promise<User> => {
    const response = await api.get('/users/me')
    return response.data
  }
}

export const connectionsAPI = {
  list: async (): Promise<Connection[]> => {
    const response = await api.get('/connections/')
    return response.data
  },

  update: async (id: number, data: { pg_dsn: string }): Promise<Connection> => {
    const response = await api.patch(`/connections/${id}`, data)
    return response.data
  },

  test: async (data: { tipo: string; pg_dsn: string }): Promise<{ valid: boolean; message: string; tipo: string }> => {
    const response = await api.post('/connections/test', data)
    return response.data
  },

  create: async (data: {
    tipo: string
    pg_dsn?: string
    dataset_id?: number
  }): Promise<Connection> => {
    const response = await api.post('/connections/', data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/connections/${id}`)
  }
}

export const agentsAPI = {
  list: async (): Promise<Agent[]> => {
    const response = await api.get('/agents/')
    return response.data
  },

  update: async (id: number, data: {
    selected_model?: string
    top_k?: number
    include_tables_key?: string
    advanced_mode?: boolean
    processing_enabled?: boolean
    refinement_enabled?: boolean
    single_table_mode?: boolean
    selected_table?: string
  }): Promise<Agent> => {
    const response = await api.patch(`/agents/${id}`, data)
    return response.data
  },

  create: async (data: {
    nome: string
    connection_id: number
    selected_model: string
    top_k?: number
    include_tables_key?: string
    advanced_mode?: boolean
    processing_enabled?: boolean
    refinement_enabled?: boolean
    single_table_mode?: boolean
    selected_table?: string
  }): Promise<Agent> => {
    const response = await api.post('/agents/', data)
    return response.data
  },

  get: async (id: number): Promise<Agent> => {
    const response = await api.get(`/agents/${id}`)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/agents/${id}`)
  }
}

export const runsAPI = {
  create: async (agentId: number, question: string, chatSessionId: number): Promise<Run> => {
    const response = await api.post(`/agents/${agentId}/run`, {
      question,
      chat_session_id: chatSessionId
    })
    return response.data
  },

  get: async (id: number): Promise<Run> => {
    const response = await api.get(`/runs/${id}`)
    return response.data
  },

  list: async (
    agentId?: number,
    page: number = 1,
    perPage: number = 10,
    chatSessionId?: number,
    status?: string
  ): Promise<PaginatedRunsResponse> => {
    console.log('🔄 runsAPI.list called with:', { agentId, page, perPage, chatSessionId, status })

    const url = agentId ? `/agents/${agentId}/runs` : '/runs/'
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString()
    })

    if (chatSessionId) {
      params.append('chat_session_id', chatSessionId.toString())
    }

    if (status) {
      params.append('status', status)
    }

    if (agentId && !url.includes('/agents/')) {
      params.append('agent_id', agentId.toString())
    }

    const finalUrl = `${url}?${params.toString()}`
    console.log('📡 Making request to:', finalUrl)

    const response = await api.get(finalUrl)
    console.log('✅ Response received:', response.data)
    return response.data
  },

  // Método auxiliar para buscar todas as runs (compatibilidade)
  listAll: async (agentId?: number): Promise<Run[]> => {
    console.log('🔄 runsAPI.listAll started for agentId:', agentId)
    const allRuns: Run[] = []
    let page = 1
    let hasNext = true

    while (hasNext) {
      console.log(`📄 Fetching page ${page} for agentId ${agentId}`)
      const response = await runsAPI.list(agentId, page, 100) // 100 itens por página
      console.log(`✅ Page ${page} fetched:`, response.runs.length, 'runs, hasNext:', response.pagination.has_next)
      allRuns.push(...response.runs)
      hasNext = response.pagination.has_next
      page++

      // Proteção contra loop infinito
      if (page > 100) {
        console.warn('⚠️ Breaking loop - too many pages')
        break
      }
    }

    console.log('🏁 runsAPI.listAll finished, total runs:', allRuns.length)
    return allRuns
  }
}

export const chatAPI = {
  // Listar sessões de chat com paginação e filtros
  listSessions: async (
    page: number = 1,
    perPage: number = 20,
    agentId?: number,
    status: string = 'active',
    search?: string,
    minMessages?: number
  ): Promise<ChatSessionListResponse> => {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
      status
    })

    if (agentId) params.append('agent_id', agentId.toString())
    if (search) params.append('search', search)
    if (minMessages) params.append('min_messages', minMessages.toString())

    const response = await api.get(`/chat-sessions/?${params.toString()}`)
    return response.data
  },

  // Criar nova sessão de chat
  createSession: async (agentId: number, title?: string): Promise<ChatSession> => {
    const response = await api.post('/chat-sessions/', {
      agent_id: agentId,
      title
    })
    return response.data
  },

  // Obter detalhes de uma sessão específica
  getSession: async (sessionId: number): Promise<ChatSession> => {
    const response = await api.get(`/chat-sessions/${sessionId}`)
    return response.data
  },

  // Obter mensagens de uma sessão com paginação
  getMessages: async (
    sessionId: number,
    page: number = 1,
    perPage: number = 50
  ): Promise<MessagesResponse> => {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString()
    })

    const response = await api.get(`/chat-sessions/${sessionId}/messages?${params.toString()}`)
    return response.data
  },

  // Atualizar sessão (título, status)
  updateSession: async (
    sessionId: number,
    data: { title?: string; status?: string }
  ): Promise<ChatSession> => {
    const response = await api.put(`/chat-sessions/${sessionId}`, data)
    return response.data
  },

  // Deletar sessão
  deleteSession: async (sessionId: number): Promise<void> => {
    await api.delete(`/chat-sessions/${sessionId}`)
  },

  // Obter runs de uma sessão específica
  getSessionRuns: async (
    sessionId: number,
    page: number = 1,
    perPage: number = 20
  ): Promise<PaginatedRunsResponse> => {
    const response = await api.get(`/chat-sessions/${sessionId}/runs?page=${page}&per_page=${perPage}`)
    return response.data
  }
}

export const tablesAPI = {
  create: async (data: {
    table_name: string
    sql_query: string
    agent_id: number
  }): Promise<{
    success: boolean
    message: string
    records_count?: number
  }> => {
    const response = await api.post('/tables/create', data)
    return response.data
  }
}

export const validationAPI = {
  validateRun: async (runId: number, validationType: string = 'individual', validationModel: string = 'gpt-4o-mini'): Promise<any> => {
    const response = await api.post(`/validation/runs/${runId}/validate`, {
      validation_type: validationType,
      validation_model: validationModel
    })
    return response.data
  },

  getRunValidations: async (runId: number): Promise<any> => {
    const response = await api.get(`/validation/runs/${runId}/validations`)
    return response.data
  },

  getValidationStats: async (): Promise<any> => {
    const response = await api.get('/validation/validations/stats')
    return response.data
  },

  // Novos endpoints para chat sessions
  validateChatSession: async (sessionId: number, validationType: string = 'individual', validationModel: string = 'gpt-4o-mini', numRunsToCompare?: number): Promise<any> => {
    const payload: any = {
      validation_type: validationType,
      validation_model: validationModel
    }

    if (numRunsToCompare) {
      payload.num_runs_to_compare = numRunsToCompare
    }

    const response = await api.post(`/validation/chat-sessions/${sessionId}/validate`, payload)
    return response.data
  },

  getChatSessionValidations: async (sessionId: number): Promise<any> => {
    const response = await api.get(`/validation/chat-sessions/${sessionId}/validations`)
    return response.data
  }
}
