'use client'

import { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'next/navigation'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { agentsAPI, runsAPI, Agent, Run } from '@/lib/api'
import { Loading, LoadingDots } from '@/components/ui/loading'
import { CreateTableModal } from '@/components/ui/create-table-modal'
import { formatDate, formatDuration, getStatusColor, getStatusText, formatJSON } from '@/lib/utils'
import { Send, Bot, User, Database, Clock, BarChart3, Table } from 'lucide-react'
import toast from 'react-hot-toast'

export default function ChatPage() {
  const searchParams = useSearchParams()
  const agentId = searchParams.get('agent')
  
  const [agent, setAgent] = useState<Agent | null>(null)
  const [messages, setMessages] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [message, setMessage] = useState('')
  const [pollingRuns, setPollingRuns] = useState<Set<number>>(new Set())
  const [isCreateTableModalOpen, setIsCreateTableModalOpen] = useState(false)
  const [selectedSqlQuery, setSelectedSqlQuery] = useState('')
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const parseResponse = (response: string) => {
    // Separar a resposta principal da query SQL
    const sqlQueryMatch = response.match(/\*\*Query SQL utilizada:\*\*\s*```sql\s*([\s\S]*?)\s*```/i)
    const sqlQuery = sqlQueryMatch ? sqlQueryMatch[1].trim() : null

    // Remover a seção SQL da resposta principal
    let mainResponse = response
    if (sqlQueryMatch) {
      mainResponse = response.replace(/---\s*\*\*Query SQL utilizada:\*\*[\s\S]*$/i, '').trim()
      // Remover também linhas de tempo de processamento se existirem
      mainResponse = mainResponse.replace(/⏱️\s*\*Processado em.*?\*/g, '').trim()
      // Remover linha sobre criar tabela se existir
      mainResponse = mainResponse.replace(/💡\s*\*Você pode criar.*?\*/g, '').trim()
    }

    return { mainResponse, sqlQuery }
  }

  const handleCreateTable = (sqlQuery: string) => {
    setSelectedSqlQuery(sqlQuery)
    setIsCreateTableModalOpen(true)
  }

  useEffect(() => {
    if (agentId) {
      loadAgent()
      loadMessages()
    }
  }, [agentId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadAgent = async () => {
    try {
      const agentData = await agentsAPI.get(parseInt(agentId!))
      setAgent(agentData)
    } catch (error) {
      console.error('Erro ao carregar agente:', error)
      toast.error('Erro ao carregar agente')
    }
  }

  const loadMessages = async () => {
    try {
      const runs = await runsAPI.list(parseInt(agentId!))
      setMessages(runs.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()))
      
      // Identificar runs que ainda estão executando
      const runningRuns = runs.filter(run => run.status === 'running' || run.status === 'queued')
      setPollingRuns(new Set(runningRuns.map(run => run.id)))
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error)
      toast.error('Erro ao carregar mensagens')
    } finally {
      setLoading(false)
    }
  }

  const checkRunStatus = async () => {
    const runIds = Array.from(pollingRuns)
    
    for (const runId of runIds) {
      try {
        const updatedRun = await runsAPI.get(runId)
        
        if (updatedRun.status === 'success' || updatedRun.status === 'failure' || updatedRun.status === 'failed') {
          console.log('🔍 Run finalizada:', {
            id: updatedRun.id,
            status: updatedRun.status,
            result_data: updatedRun.result_data,
            sql_used: updatedRun.sql_used
          })

          // Remove do polling
          setPollingRuns(prev => {
            const newSet = new Set(prev)
            newSet.delete(runId)
            return newSet
          })

          // Atualiza a mensagem
          setMessages(prev => prev.map(msg =>
            msg.id === runId ? updatedRun : msg
          ))
        }
      } catch (error) {
        console.error(`Erro ao verificar status do run ${runId}:`, error)
      }
    }
  }

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || !agentId || sending) return

    setSending(true)
    const userMessage = message.trim()
    setMessage('')

    try {
      const newRun = await runsAPI.create(parseInt(agentId), userMessage)
      
      // Adiciona a nova mensagem
      setMessages(prev => [...prev, newRun])
      
      // Adiciona ao polling se estiver executando
      if (newRun.status === 'running' || newRun.status === 'queued') {
        setPollingRuns(prev => new Set([...Array.from(prev), newRun.id]))
      }
      
      toast.success('Pergunta enviada!')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Erro ao enviar pergunta'
      toast.error(errorMessage)
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loading size="lg" />
        </div>
      </DashboardLayout>
    )
  }

  if (!agent) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <Bot className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">Agente não encontrado</h3>
          <p className="mt-2 text-gray-500">
            Selecione um agente válido para começar a conversar.
          </p>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="flex flex-col h-[calc(100vh-8rem)]">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-gray-200 pb-4 mb-4">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Bot className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-3">
              <h1 className="text-xl font-semibold text-gray-900">{agent.nome}</h1>
              <p className="text-sm text-gray-500">
                {agent.selected_model} • PostgreSQL #{agent.connection_id}
              </p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 mb-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <Bot className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">Comece uma conversa</h3>
              <p className="mt-2 text-gray-500">
                Faça uma pergunta sobre seus dados para começar.
              </p>
            </div>
          ) : (
            messages.map((run) => (
              <div key={run.id} className="space-y-4">
                {/* User Message */}
                <div className="flex justify-end">
                  <div className="chat-message user max-w-3xl">
                    <div className="flex items-start">
                      <div className="flex-1">
                        <p className="text-gray-900">{run.question}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {formatDate(run.created_at)}
                        </p>
                      </div>
                      <div className="ml-3 p-1 bg-primary-200 rounded-full">
                        <User className="h-4 w-4 text-primary-700" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Assistant Response */}
                <div className="flex justify-start">
                  <div className="chat-message assistant w-full">
                    <div className="flex items-start">
                      <div className="p-1 bg-gray-200 rounded-full mr-3">
                        <Bot className="h-4 w-4 text-gray-600" />
                      </div>
                      <div className="flex-1">
                        {run.status === 'running' || run.status === 'queued' ? (
                          <div className="flex items-center">
                            <LoadingDots />
                            <span className="ml-2 text-sm text-gray-500">
                              {run.status === 'queued' ? 'Na fila...' : 'Processando...'}
                            </span>
                          </div>
                        ) : run.status === 'failed' || run.status === 'failure' ? (
                          <div className="text-red-600">
                            <p>❌ Erro ao processar a pergunta</p>
                            {run.error_type && (
                              <p className="text-sm mt-1">Tipo: {run.error_type}</p>
                            )}
                          </div>
                        ) : run.status === 'success' && run.result_data ? (
                          <div className="space-y-4 w-full">
                            {(() => {
                              const { mainResponse, sqlQuery } = parseResponse(run.result_data)
                              return (
                                <>
                                  {/* Response Text */}
                                  <div className="prose prose-sm max-w-none">
                                    <div className="text-gray-900 whitespace-pre-wrap">
                                      {mainResponse}
                                    </div>
                                  </div>

                                  {/* SQL Query */}
                                  {(sqlQuery || run.sql_used) && (
                                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 w-full">
                                      <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center space-x-2">
                                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                          <Database className="h-4 w-4 text-blue-600 mr-1" />
                                          <span className="text-sm font-semibold text-blue-800">Query SQL Gerada</span>
                                        </div>
                                        {(agent?.connection?.tipo === 'postgres' || agent?.connection?.tipo === 'postgresql') && (
                                          <button
                                            onClick={() => handleCreateTable(sqlQuery || run.sql_used || '')}
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
                                          <code className="language-sql">{sqlQuery || run.sql_used}</code>
                                        </pre>
                                      </div>
                                    </div>
                                  )}
                                </>
                              )
                            })()}

                            {/* Metadata */}
                            <div className="flex items-center space-x-4 text-xs text-gray-500">
                              {run.execution_ms && (
                                <div className="flex items-center">
                                  <Clock className="h-3 w-3 mr-1" />
                                  {formatDuration(run.execution_ms)}
                                </div>
                              )}
                              {run.result_rows_count && (
                                <div className="flex items-center">
                                  <BarChart3 className="h-3 w-3 mr-1" />
                                  {run.result_rows_count} linhas
                                </div>
                              )}
                              <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(run.status)}`}>
                                {getStatusText(run.status)}
                              </span>
                            </div>
                          </div>
                        ) : (
                          <p className="text-gray-500">Sem resposta disponível</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="flex-shrink-0 border-t border-gray-200 pt-4">
          <form onSubmit={handleSend} className="flex space-x-3">
            <div className="flex-1">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Faça uma pergunta sobre seus dados..."
                className="input-field"
                disabled={sending}
              />
            </div>
            <button
              type="submit"
              disabled={sending || !message.trim()}
              className="btn-primary flex items-center px-6"
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

      {/* Modal de Criar Tabela */}
      <CreateTableModal
        isOpen={isCreateTableModalOpen}
        onClose={() => setIsCreateTableModalOpen(false)}
        sqlQuery={selectedSqlQuery}
        agentId={agent?.id || 0}
        connectionType={agent?.connection?.tipo || ''}
      />
    </DashboardLayout>
  )
}
