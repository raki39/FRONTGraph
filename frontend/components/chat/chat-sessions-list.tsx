'use client'

import { useState, useEffect } from 'react'
import { chatAPI, ChatSessionListItem, PaginationInfo } from '@/lib/api'
import { Loading } from '@/components/ui/loading'
import { SimplePagination } from '@/components/ui/pagination'
import { formatDate } from '@/lib/utils'
import { MessageSquare, Plus, Search, Filter } from 'lucide-react'
import toast from 'react-hot-toast'

interface ChatSessionsListProps {
  agentId?: number
  onSessionSelect: (sessionId: number) => void
  onCreateSession: () => void
  selectedSessionId?: number
}

export function ChatSessionsList({ 
  agentId, 
  onSessionSelect, 
  onCreateSession,
  selectedSessionId 
}: ChatSessionsListProps) {
  const [sessions, setSessions] = useState<ChatSessionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [pagination, setPagination] = useState<PaginationInfo | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<'active' | 'archived'>('active')

  useEffect(() => {
    loadSessions()
  }, [agentId, currentPage, searchTerm, statusFilter])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const response = await chatAPI.listSessions(
        currentPage,
        20, // 20 sessões por página
        agentId,
        statusFilter,
        searchTerm || undefined
      )
      
      setSessions(response.sessions)
      setPagination(response.pagination)
    } catch (error) {
      console.error('Erro ao carregar sessões:', error)
      toast.error('Erro ao carregar sessões de chat')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setCurrentPage(1)
    loadSessions()
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  if (loading && sessions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Conversas</h2>
          <button
            onClick={onCreateSession}
            className="btn-primary flex items-center px-3 py-2 text-sm"
          >
            <Plus className="h-4 w-4 mr-1" />
            Nova Conversa
          </button>
        </div>

        {/* Search and Filters */}
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar conversas..."
              className="input-field pl-10"
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as 'active' | 'archived')}
              className="input-field text-sm"
            >
              <option value="active">Ativas</option>
              <option value="archived">Arquivadas</option>
            </select>
          </div>
        </form>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="text-center py-12">
            <MessageSquare className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">
              {searchTerm ? 'Nenhuma conversa encontrada' : 'Nenhuma conversa ainda'}
            </h3>
            <p className="mt-2 text-gray-500">
              {searchTerm 
                ? 'Tente ajustar os filtros de busca'
                : 'Crie uma nova conversa para começar'
              }
            </p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => onSessionSelect(session.id)}
                className={`
                  p-3 rounded-lg cursor-pointer transition-colors
                  ${selectedSessionId === session.id 
                    ? 'bg-blue-50 border border-blue-200' 
                    : 'hover:bg-gray-50 border border-transparent'
                  }
                `}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 truncate">
                      {session.title}
                    </h4>
                    {session.last_message && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                        {session.last_message}
                      </p>
                    )}
                    <div className="flex items-center space-x-3 mt-2 text-xs text-gray-400">
                      <span>{session.messages_count} mensagens</span>
                      <span>{formatDate(session.updated_at)}</span>
                    </div>
                  </div>
                  <div className="flex-shrink-0 ml-2">
                    <div className={`
                      w-2 h-2 rounded-full
                      ${session.status === 'active' ? 'bg-green-400' : 'bg-gray-400'}
                    `} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex-shrink-0 p-4 border-t border-gray-200">
          <SimplePagination
            pagination={pagination}
            onPageChange={handlePageChange}
          />
        </div>
      )}
    </div>
  )
}
