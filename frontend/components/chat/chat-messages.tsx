'use client'

import { useState, useEffect, useRef } from 'react'
import { chatAPI, runsAPI, Message, MessagesResponse, Run } from '@/lib/api'
import { ValidationModal } from './validation-modal'
import { Loading, LoadingDots } from '@/components/ui/loading'
import { formatDate, formatDuration, getStatusColor, getStatusText } from '@/lib/utils'
import { Bot, User, Database, Clock, BarChart3, Table, Send, CheckSquare } from 'lucide-react'
import toast from 'react-hot-toast'

interface ChatMessagesProps {
  sessionId: number
  agentId: number
  onCreateTable?: (sqlQuery: string) => void
  connectionType?: string
}

export function ChatMessages({ 
  sessionId, 
  agentId, 
  onCreateTable,
  connectionType 
}: ChatMessagesProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [message, setMessage] = useState('')
  const [sessionInfo, setSessionInfo] = useState<any>(null)
  const [hasMoreMessages, setHasMoreMessages] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [pollingRuns, setPollingRuns] = useState<Set<number>>(new Set())
  const [showValidationModal, setShowValidationModal] = useState(false)
  const [isInitialLoad, setIsInitialLoad] = useState(true)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (sessionId) {
      loadMessages()
    }
  }, [sessionId])

  useEffect(() => {
    // Polling para runs em execução
    if (pollingRuns.size > 0) {
      intervalRef.current = setInterval(checkRunStatus, 2000)
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [pollingRuns])

  useEffect(() => {
    // Só faz scroll automático no carregamento inicial ou quando enviando mensagem
    if (isInitialLoad || sending) {
      scrollToBottom()
    }
  }, [messages, isInitialLoad, sending])

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, 100)
  }

  const loadMessages = async (page: number = 1) => {
    try {
      setLoading(page === 1)
      if (page > 1) setLoadingMore(true)

      const response: MessagesResponse = await chatAPI.getMessages(sessionId, page, 50)

      if (page === 1) {
        setMessages(response.messages)
        setIsInitialLoad(true)
      } else {
        // Para páginas adicionais, adiciona no início (mensagens mais antigas)
        setMessages(prev => [...response.messages, ...prev])
        setIsInitialLoad(false)
      }

      setSessionInfo(response.session_info)
      setHasMoreMessages(response.pagination.has_next)
      setCurrentPage(page)

      // Identificar runs que ainda estão executando
      const runningRunIds = new Set<number>()
      for (const msg of response.messages) {
        if (msg.role === 'user' && msg.run_id) {
          try {
            const run = await runsAPI.get(msg.run_id)
            if (run.status === 'running' || run.status === 'queued') {
              runningRunIds.add(run.id)
            }
          } catch (error) {
            console.error(`Erro ao verificar run ${msg.run_id}:`, error)
          }
        }
      }
      setPollingRuns(runningRunIds)

    } catch (error) {
      console.error('Erro ao carregar mensagens:', error)
      toast.error('Erro ao carregar mensagens')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  const loadMoreMessages = async () => {
    if (!hasMoreMessages || loadingMore) return
    await loadMessages(currentPage + 1)
  }

  const checkRunStatus = async () => {
    const runIds = Array.from(pollingRuns)

    for (const runId of runIds) {
      try {
        const updatedRun = await runsAPI.get(runId)

        if (updatedRun.status === 'success' || updatedRun.status === 'failure' || updatedRun.status === 'failed') {
          // Remove do polling
          setPollingRuns(prev => {
            const newSet = new Set(prev)
            newSet.delete(runId)
            return newSet
          })

          // Recarregar mensagens para obter a resposta atualizada
          await loadMessages(1)
        }
      } catch (error) {
        console.error(`Erro ao verificar status do run ${runId}:`, error)
      }
    }
  }

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || sending) return

    setSending(true)
    const userMessage = message.trim()
    setMessage('')

    // Adicionar mensagem do usuário imediatamente ao estado
    const tempUserMessage: Message = {
      id: Date.now(), // ID temporário
      chat_session_id: sessionId,
      run_id: null,
      role: 'user',
      content: userMessage,
      sql_query: null,
      created_at: new Date().toISOString(),
      sequence_order: messages.length + 1,
      message_metadata: null
    }

    setMessages(prev => [...prev, tempUserMessage])
    setIsInitialLoad(false) // Para garantir scroll

    try {
      const newRun = await runsAPI.create(agentId, userMessage, sessionId)

      // Adicionar mensagem de loading do assistente
      const tempAssistantMessage: Message = {
        id: Date.now() + 1,
        chat_session_id: sessionId,
        run_id: newRun.id,
        role: 'assistant',
        content: '🤔 Pensando...',
        sql_query: null,
        created_at: new Date().toISOString(),
        sequence_order: messages.length + 2,
        message_metadata: { loading: true }
      }

      setMessages(prev => [...prev, tempAssistantMessage])

      // Adicionar ao polling se estiver executando
      if (newRun.status === 'running' || newRun.status === 'queued') {
        setPollingRuns(prev => new Set([...Array.from(prev), newRun.id]))
      }

      toast.success('Pergunta enviada!')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erro ao enviar pergunta'
      toast.error(errorMessage)

      // Remover mensagem temporária em caso de erro
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setSending(false)
    }
  }

  const parseResponse = (content: string) => {
    // Separar a resposta principal da query SQL
    const sqlQueryMatch = content.match(/\*\*Query SQL utilizada:\*\*\s*```sql\s*([\s\S]*?)\s*```/i)
    const sqlQuery = sqlQueryMatch ? sqlQueryMatch[1].trim() : null

    // Remover a seção SQL da resposta principal
    let mainResponse = content
    if (sqlQueryMatch) {
      mainResponse = content.replace(/---\s*\*\*Query SQL utilizada:\*\*[\s\S]*$/i, '').trim()
      mainResponse = mainResponse.replace(/⏱️\s*\*Processado em.*?\*/g, '').trim()
      mainResponse = mainResponse.replace(/💡\s*\*Você pode criar.*?\*/g, '').trim()
    }

    return { mainResponse, sqlQuery }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      {sessionInfo && (
        <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{sessionInfo.title}</h2>
              <p className="text-sm text-gray-500">{sessionInfo.total_messages} mensagens</p>
            </div>
            <button
              onClick={() => setShowValidationModal(true)}
              className="flex items-center px-3 py-2 text-sm rounded-lg transition-colors bg-blue-100 text-blue-700 border border-blue-200 hover:bg-blue-200"
            >
              <CheckSquare className="h-4 w-4 mr-2" />
              Validar Conversa
            </button>
          </div>
        </div>
      )}

      {/* Modal de Validação */}
      {sessionInfo && (
        <ValidationModal
          isOpen={showValidationModal}
          onClose={() => setShowValidationModal(false)}
          sessionId={sessionId}
          sessionTitle={sessionInfo.title}
        />
      )}

      {/* Messages */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {/* Load More Button */}
        {hasMoreMessages && (
          <div className="text-center py-3">
            <button
              onClick={loadMoreMessages}
              disabled={loadingMore}
              className="px-4 py-2 text-sm bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
            >
              {loadingMore ? (
                <div className="flex items-center">
                  <Loading size="sm" />
                  <span className="ml-2">Carregando...</span>
                </div>
              ) : (
                '↑ Carregar mensagens anteriores'
              )}
            </button>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="text-center py-12">
            <Bot className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">Comece uma conversa</h3>
            <p className="mt-2 text-gray-500">
              Faça uma pergunta sobre seus dados para começar.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="mb-6">
              {msg.role === 'user' ? (
                /* User Message */
                <div className="flex justify-end">
                  <div className="max-w-2xl">
                    <div className="flex items-start space-x-3">
                      <div className="flex-1">
                        <div className="bg-blue-600 text-white rounded-2xl rounded-tr-md px-4 py-3">
                          <p className="text-sm">{msg.content}</p>
                        </div>
                        <p className="text-xs text-gray-500 mt-1 text-right">
                          {formatDate(msg.created_at)}
                        </p>
                      </div>
                      <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <User className="h-4 w-4 text-blue-600" />
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                /* Assistant Message */
                <div className="flex justify-start">
                  <div className="max-w-4xl w-full">
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                        <Bot className="h-4 w-4 text-gray-600" />
                      </div>
                      <div className="flex-1">
                        {pollingRuns.has(msg.run_id) || msg.message_metadata?.loading ? (
                          <div className="bg-gray-50 rounded-2xl rounded-tl-md px-4 py-3">
                            <div className="flex items-center">
                              <LoadingDots />
                              <span className="ml-2 text-sm text-gray-500">Processando...</span>
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {(() => {
                              const { mainResponse, sqlQuery } = parseResponse(msg.content)
                              return (
                                <>
                                  {/* Response Text */}
                                  <div className="bg-gray-50 rounded-2xl rounded-tl-md px-4 py-3">
                                    <div className="text-gray-900 whitespace-pre-wrap text-sm">
                                      {mainResponse}
                                    </div>
                                  </div>

                                  {/* SQL Query */}
                                  {(sqlQuery || msg.sql_query) && (
                                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 w-full">
                                      <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center space-x-2">
                                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                          <Database className="h-4 w-4 text-blue-600 mr-1" />
                                          <span className="text-sm font-semibold text-blue-800">Query SQL Gerada</span>
                                        </div>
                                        {(connectionType === 'postgres' || connectionType === 'postgresql') && onCreateTable && (
                                          <button
                                            onClick={() => onCreateTable(sqlQuery || msg.sql_query || '')}
                                            className="flex items-center space-x-1 px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-md transition-colors"
                                            title="Criar tabela PostgreSQL com estes dados"
                                          >
                                            <Table className="h-3 w-3" />
                                            <span>Criar Tabela</span>
                                          </button>
                                        )}
                                      </div>
                                      <div className="bg-white border border-blue-200 rounded-md p-3 shadow-sm overflow-hidden">
                                        <pre className="text-sm text-gray-800 overflow-x-auto whitespace-pre-wrap break-words">
                                          <code className="language-sql">{sqlQuery || msg.sql_query}</code>
                                        </pre>
                                      </div>
                                    </div>
                                  )}
                                </>
                              )
                            })()}
                            <p className="text-xs text-gray-500 mt-2">
                              {formatDate(msg.created_at)}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 bg-white border-t border-gray-200 px-4 py-4">
        <form onSubmit={handleSend} className="flex space-x-3">
          <div className="flex-1">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Faça uma pergunta sobre seus dados..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              disabled={sending}
              autoFocus
            />
          </div>
          <button
            type="submit"
            disabled={sending || !message.trim()}
            className={`
              flex items-center justify-center px-6 py-3 rounded-lg font-medium transition-all
              ${sending || !message.trim()
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow-md'
              }
            `}
          >
            {sending ? (
              <Loading size="sm" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
