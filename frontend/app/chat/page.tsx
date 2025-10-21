'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { Sidebar } from '@/components/layout/sidebar'
import { agentsAPI, chatAPI, Agent, ChatSession } from '@/lib/api'
import { Loading } from '@/components/ui/loading'
import { CreateTableModal } from '@/components/ui/create-table-modal'
import { ChatSessionsList } from '@/components/chat/chat-sessions-list'
import { ChatMessages } from '@/components/chat/chat-messages'
import { Bot } from 'lucide-react'
import toast from 'react-hot-toast'

export default function ChatPage() {
  const searchParams = useSearchParams()
  const agentId = searchParams.get('agent')

  const [agent, setAgent] = useState<Agent | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [isCreateTableModalOpen, setIsCreateTableModalOpen] = useState(false)
  const [selectedSqlQuery, setSelectedSqlQuery] = useState('')

  useEffect(() => {
    if (agentId) {
      loadAgent()
    }
  }, [agentId])

  const loadAgent = async () => {
    try {
      const agentData = await agentsAPI.get(parseInt(agentId!))
      setAgent(agentData)
    } catch (error) {
      console.error('Erro ao carregar agente:', error)
      toast.error('Erro ao carregar agente')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSession = async () => {
    if (!agentId) return

    try {
      const newSession = await chatAPI.createSession(
        parseInt(agentId),
        `Conversa ${new Date().toLocaleString('pt-BR', {
          day: '2-digit',
          month: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })}`
      )
      setSelectedSessionId(newSession.id)
      toast.success('Nova conversa criada!')
    } catch (error) {
      console.error('Erro ao criar sessão:', error)
      toast.error('Erro ao criar nova conversa')
    }
  }

  const handleSessionSelect = (sessionId: number) => {
    setSelectedSessionId(sessionId)
  }

  const handleCreateTable = (sqlQuery: string) => {
    setSelectedSqlQuery(sqlQuery)
    setIsCreateTableModalOpen(true)
  }







  if (loading) {
    return (
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 overflow-hidden lg:ml-0">
          <div className="flex items-center justify-center h-full">
            <Loading size="lg" />
          </div>
        </main>
      </div>
    )
  }

  if (!agentId) {
    return (
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 overflow-hidden lg:ml-0">
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Bot className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">Selecione um agente</h3>
              <p className="mt-2 text-gray-500">
                Escolha um agente para começar a conversar.
              </p>
            </div>
          </div>
        </main>
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 overflow-hidden lg:ml-0">
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Bot className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">Agente não encontrado</h3>
              <p className="mt-2 text-gray-500">
                O agente selecionado não foi encontrado.
              </p>
            </div>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-hidden lg:ml-0">
        <div className="flex h-full">
          {/* Sidebar - Lista de Sessões */}
          <div className="w-72 bg-white border-r border-gray-200 flex flex-col">
            <ChatSessionsList
              agentId={parseInt(agentId)}
              onSessionSelect={handleSessionSelect}
              onCreateSession={handleCreateSession}
              selectedSessionId={selectedSessionId || undefined}
            />
          </div>

          {/* Main Content - Mensagens */}
          <div className="flex-1 flex flex-col bg-white">
            {selectedSessionId ? (
              <ChatMessages
                sessionId={selectedSessionId}
                agentId={parseInt(agentId)}
                onCreateTable={handleCreateTable}
                connectionType={agent.connection?.tipo}
              />
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center max-w-md">
                  <Bot className="mx-auto h-16 w-16 text-gray-400" />
                  <h3 className="mt-4 text-xl font-medium text-gray-900">
                    {agent.nome}
                  </h3>
                  <p className="mt-2 text-gray-500 mb-6">
                    {agent.selected_model} • {agent.connection?.tipo} #{agent.connection_id}
                  </p>
                  <p className="text-gray-500 mb-4">
                    Selecione uma conversa existente ou crie uma nova para começar.
                  </p>
                  <button
                    onClick={handleCreateSession}
                    className="btn-primary"
                  >
                    Criar Nova Conversa
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Modal de Criar Tabela */}
      <CreateTableModal
        isOpen={isCreateTableModalOpen}
        onClose={() => setIsCreateTableModalOpen(false)}
        sqlQuery={selectedSqlQuery}
        agentId={agent?.id || 0}
        connectionType={agent?.connection?.tipo || ''}
      />
    </div>
  )
}
