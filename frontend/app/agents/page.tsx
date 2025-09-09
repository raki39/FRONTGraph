'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { agentsAPI, connectionsAPI, Agent, Connection } from '@/lib/api'
import { Loading } from '@/components/ui/loading'
import { Modal } from '@/components/ui/modal'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { DropdownMenu } from '@/components/ui/dropdown-menu'
import { formatDate } from '@/lib/utils'
import { Bot, Plus, Trash2, MessageSquare, Settings, Edit } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'

const MODELS = [
  { value: 'gpt-4o', label: 'GPT-4o (Recomendado)' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
  { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
  { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' }
]

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [isDeleting, setIsDeleting] = useState<number | null>(null)
  const [agentToDelete, setAgentToDelete] = useState<Agent | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [agentToEdit, setAgentToEdit] = useState<Agent | null>(null)
  const [editFormData, setEditFormData] = useState({
    nome: '',
    selected_model: '',
    top_k: 10,
    include_tables_key: '*',
    advanced_mode: false,
    processing_enabled: false,
    refinement_enabled: false,
    single_table_mode: false,
    selected_table: ''
  })
  const [formData, setFormData] = useState({
    nome: '',
    connection_id: 0,
    selected_model: 'gpt-4o',
    top_k: 10,
    include_tables_key: '*',
    advanced_mode: false,
    processing_enabled: false,
    refinement_enabled: false,
    single_table_mode: false,
    selected_table: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [agentsData, connectionsData] = await Promise.all([
        agentsAPI.list(),
        connectionsAPI.list()
      ])
      setAgents(agentsData)
      setConnections(connectionsData)
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      toast.error('Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsCreating(true)

    try {
      await agentsAPI.create(formData)
      
      toast.success('Agente criado com sucesso!')
      setIsModalOpen(false)
      setFormData({
        nome: '',
        connection_id: 0,
        selected_model: 'gpt-4o',
        top_k: 10,
        include_tables_key: '*',
        advanced_mode: false,
        processing_enabled: false,
        refinement_enabled: false,
        single_table_mode: false,
        selected_table: ''
      })
      loadData()
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao criar agente'
      toast.error(message)
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteClick = (agent: Agent) => {
    setAgentToDelete(agent)
  }

  const handleDeleteConfirm = async () => {
    if (!agentToDelete) return

    setIsDeleting(agentToDelete.id)
    try {
      await agentsAPI.delete(agentToDelete.id)
      toast.success('Agente excluído com sucesso!')
      loadData()
      setAgentToDelete(null)
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao excluir agente'
      toast.error(message)
    } finally {
      setIsDeleting(null)
    }
  }

  const handleDeleteCancel = () => {
    setAgentToDelete(null)
  }

  const handleEditClick = (agent: Agent) => {
    setAgentToEdit(agent)
    setEditFormData({
      nome: agent.nome,
      selected_model: agent.selected_model,
      top_k: agent.top_k,
      include_tables_key: agent.include_tables_key || '*',
      advanced_mode: agent.advanced_mode,
      processing_enabled: agent.processing_enabled,
      refinement_enabled: agent.refinement_enabled,
      single_table_mode: agent.single_table_mode,
      selected_table: agent.selected_table || ''
    })
    setIsEditModalOpen(true)
  }

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!agentToEdit) return

    setIsEditing(true)
    try {
      await agentsAPI.update(agentToEdit.id, {
        selected_model: editFormData.selected_model,
        top_k: editFormData.top_k,
        include_tables_key: editFormData.include_tables_key,
        advanced_mode: editFormData.advanced_mode,
        processing_enabled: editFormData.processing_enabled,
        refinement_enabled: editFormData.refinement_enabled,
        single_table_mode: editFormData.single_table_mode,
        selected_table: editFormData.selected_table || undefined
      })

      toast.success('Agente atualizado com sucesso!')
      setIsEditModalOpen(false)
      setAgentToEdit(null)
      loadData()
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao atualizar agente'
      toast.error(message)
    } finally {
      setIsEditing(false)
    }
  }

  const handleEditCancel = () => {
    setIsEditModalOpen(false)
    setAgentToEdit(null)
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Agentes</h1>
            <p className="text-gray-600">Gerencie seus agentes de análise de dados</p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-primary flex items-center"
            disabled={connections.length === 0}
          >
            <Plus className="mr-2 h-4 w-4" />
            Novo Agente
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loading size="lg" />
          </div>
        ) : connections.length === 0 ? (
          <div className="card p-12 text-center">
            <Bot className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">Nenhuma conexão disponível</h3>
            <p className="mt-2 text-gray-500">
              Você precisa criar uma conexão antes de criar agentes.
            </p>
            <Link href="/connections" className="btn-primary mt-6">
              Criar Conexão
            </Link>
          </div>
        ) : agents.length === 0 ? (
          <div className="card p-12 text-center">
            <Bot className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">Nenhum agente</h3>
            <p className="mt-2 text-gray-500">
              Comece criando seu primeiro agente de análise de dados.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="btn-primary mt-6"
            >
              Criar primeiro agente
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent) => (
              <div key={agent.id} className="card p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <Bot className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="ml-3">
                      <h3 className="text-lg font-medium text-gray-900">
                        {agent.nome}
                      </h3>
                      <p className="text-sm text-gray-500">{agent.selected_model}</p>
                    </div>
                  </div>
                  <DropdownMenu
                    items={[
                      {
                        label: 'Editar',
                        icon: <Edit className="h-4 w-4 text-blue-500" />,
                        onClick: () => handleEditClick(agent),
                        className: 'text-blue-600 hover:bg-blue-50'
                      },
                      {
                        label: 'Excluir',
                        icon: <Trash2 className="h-4 w-4 text-red-500" />,
                        onClick: () => handleDeleteClick(agent),
                        className: 'text-red-600 hover:bg-red-50'
                      }
                    ]}
                  />
                </div>
                
                <div className="mt-4 space-y-2">
                  <div className="text-sm">
                    <span className="text-gray-500">Conexão:</span>
                    <span className="ml-2 text-gray-900">
                      PostgreSQL #{agent.connection_id}
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500">Top K:</span>
                    <span className="ml-2 text-gray-900">{agent.top_k}</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500">Criado em:</span>
                    <span className="ml-2 text-gray-900">{formatDate(agent.created_at)}</span>
                  </div>
                </div>

                <div className="mt-6 flex space-x-2">
                  <Link
                    href={`/chat?agent=${agent.id}`}
                    className="flex-1 btn-primary text-center text-sm py-2 flex items-center justify-center"
                  >
                    <MessageSquare className="mr-1 h-4 w-4" />
                    Chat
                  </Link>
                  <button
                    className="btn-secondary text-sm py-2 px-3"
                    title="Configurações do agente"
                  >
                    <Settings className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Novo Agente"
          size="lg"
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Nome do agente
              </label>
              <input
                type="text"
                required
                value={formData.nome}
                onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                className="input-field mt-1"
                placeholder="Ex: Agente de Vendas"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Conexão
              </label>
              <select
                required
                value={formData.connection_id}
                onChange={(e) => setFormData({ ...formData, connection_id: parseInt(e.target.value) })}
                className="input-field mt-1"
              >
                <option value={0}>Selecione uma conexão</option>
                {connections.map((conn) => (
                  <option key={conn.id} value={conn.id}>
                    PostgreSQL #{conn.id} ({conn.tipo})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Modelo de IA
              </label>
              <select
                value={formData.selected_model}
                onChange={(e) => setFormData({ ...formData, selected_model: e.target.value })}
                className="input-field mt-1"
              >
                {MODELS.map((model) => (
                  <option key={model.value} value={model.value}>
                    {model.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Top K (exemplos)
                </label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={formData.top_k}
                  onChange={(e) => setFormData({ ...formData, top_k: parseInt(e.target.value) })}
                  className="input-field mt-1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Tabelas (padrão: todas)
                </label>
                <input
                  type="text"
                  value={formData.include_tables_key}
                  onChange={(e) => setFormData({ ...formData, include_tables_key: e.target.value })}
                  className="input-field mt-1"
                  placeholder="*"
                />
              </div>
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                Configurações Avançadas
              </label>
              
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.advanced_mode}
                    onChange={(e) => setFormData({ ...formData, advanced_mode: e.target.checked })}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Modo avançado</span>
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.processing_enabled}
                    onChange={(e) => setFormData({ ...formData, processing_enabled: e.target.checked })}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Processamento habilitado</span>
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.refinement_enabled}
                    onChange={(e) => setFormData({ ...formData, refinement_enabled: e.target.checked })}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Refinamento habilitado</span>
                </label>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="btn-secondary"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isCreating}
                className="btn-primary flex items-center"
              >
                {isCreating ? (
                  <>
                    <Loading size="sm" className="mr-2" />
                    Criando...
                  </>
                ) : (
                  'Criar Agente'
                )}
              </button>
            </div>
          </form>
        </Modal>

        {/* Modal de Edição */}
        <Modal
          isOpen={isEditModalOpen}
          onClose={handleEditCancel}
          title="Editar Agente"
        >
          <form onSubmit={handleEditSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Nome do agente
              </label>
              <input
                type="text"
                value={editFormData.nome}
                className="input-field mt-1 bg-gray-100"
                disabled
                title="O nome do agente não pode ser alterado"
              />
              <p className="text-xs text-gray-500 mt-1">
                O nome do agente não pode ser alterado
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Modelo
              </label>
              <select
                required
                value={editFormData.selected_model}
                onChange={(e) => setEditFormData({ ...editFormData, selected_model: e.target.value })}
                className="input-field mt-1"
              >
                <option value="">Selecione um modelo</option>
                <option value="gpt-4o-mini">GPT-4o Mini</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                <option value="claude-3-haiku">Claude 3 Haiku</option>
                <option value="claude-3-sonnet">Claude 3 Sonnet</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Top K (número de resultados)
              </label>
              <input
                type="number"
                min="1"
                max="50"
                required
                value={editFormData.top_k}
                onChange={(e) => setEditFormData({ ...editFormData, top_k: parseInt(e.target.value) })}
                className="input-field mt-1"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Tabelas incluídas
              </label>
              <input
                type="text"
                value={editFormData.include_tables_key}
                onChange={(e) => setEditFormData({ ...editFormData, include_tables_key: e.target.value })}
                className="input-field mt-1"
                placeholder="* (todas as tabelas)"
              />
              <p className="text-xs text-gray-500 mt-1">
                Use * para todas as tabelas ou especifique nomes separados por vírgula
              </p>
            </div>

            <div className="space-y-3">
              <h4 className="text-sm font-medium text-gray-700">Configurações Avançadas</h4>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="edit_advanced_mode"
                  checked={editFormData.advanced_mode}
                  onChange={(e) => setEditFormData({ ...editFormData, advanced_mode: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="edit_advanced_mode" className="ml-2 text-sm text-gray-700">
                  Modo avançado
                </label>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="edit_processing_enabled"
                  checked={editFormData.processing_enabled}
                  onChange={(e) => setEditFormData({ ...editFormData, processing_enabled: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="edit_processing_enabled" className="ml-2 text-sm text-gray-700">
                  Processamento habilitado
                </label>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="edit_refinement_enabled"
                  checked={editFormData.refinement_enabled}
                  onChange={(e) => setEditFormData({ ...editFormData, refinement_enabled: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="edit_refinement_enabled" className="ml-2 text-sm text-gray-700">
                  Refinamento habilitado
                </label>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="edit_single_table_mode"
                  checked={editFormData.single_table_mode}
                  onChange={(e) => setEditFormData({ ...editFormData, single_table_mode: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="edit_single_table_mode" className="ml-2 text-sm text-gray-700">
                  Modo tabela única
                </label>
              </div>

              {editFormData.single_table_mode && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Tabela selecionada
                  </label>
                  <input
                    type="text"
                    value={editFormData.selected_table}
                    onChange={(e) => setEditFormData({ ...editFormData, selected_table: e.target.value })}
                    className="input-field mt-1"
                    placeholder="Nome da tabela"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={handleEditCancel}
                className="btn-secondary"
                disabled={isEditing}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isEditing}
                className="btn-primary flex items-center"
              >
                {isEditing ? (
                  <>
                    <Loading size="sm" className="mr-2" />
                    Salvando...
                  </>
                ) : (
                  'Salvar Alterações'
                )}
              </button>
            </div>
          </form>
        </Modal>

        {/* Modal de Confirmação de Exclusão */}
        <ConfirmDialog
          isOpen={!!agentToDelete}
          onClose={handleDeleteCancel}
          onConfirm={handleDeleteConfirm}
          title="Excluir Agente"
          description="Esta ação não pode ser desfeita."
          confirmText="Excluir"
          type="danger"
          isLoading={isDeleting === agentToDelete?.id}
        >
          <div>
            <p className="text-sm text-gray-700">
              <strong>Agente:</strong> {agentToDelete?.nome}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              <strong>Modelo:</strong> {agentToDelete?.selected_model}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Todo o histórico de conversas será perdido.
            </p>
          </div>
        </ConfirmDialog>
      </div>
    </DashboardLayout>
  )
}
