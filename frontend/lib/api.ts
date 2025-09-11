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

export interface ChatSession {
  id: number
  user_id: number
  agent_id: number
  title: string
  created_at: string
  updated_at: string
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
  create: async (agentId: number, question: string, chatSessionId?: number): Promise<Run> => {
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

  list: async (agentId?: number): Promise<Run[]> => {
    const url = agentId ? `/agents/${agentId}/runs` : '/runs/'
    const response = await api.get(url)
    return response.data
  }
}

export const chatAPI = {
  getSessions: async (agentId: number): Promise<ChatSession[]> => {
    const response = await api.get(`/agents/${agentId}/chat-sessions`)
    return response.data
  },

  createSession: async (agentId: number, title: string): Promise<ChatSession> => {
    const response = await api.post(`/agents/${agentId}/chat-sessions`, { title })
    return response.data
  },

  getMessages: async (sessionId: number): Promise<Run[]> => {
    const response = await api.get(`/chat-sessions/${sessionId}/messages`)
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
