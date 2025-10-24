'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { connectionsAPI, agentsAPI, Connection } from '@/lib/api'
import { Loading } from '@/components/ui/loading'
import { Modal } from '@/components/ui/modal'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { DropdownMenu } from '@/components/ui/dropdown-menu'
import { formatDate } from '@/lib/utils'
import { Database, Plus, Trash2, Edit, MoreVertical } from 'lucide-react'
import toast from 'react-hot-toast'

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<Connection[]>([])
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [isDeleting, setIsDeleting] = useState<number | null>(null)
  const [connectionToDelete, setConnectionToDelete] = useState<Connection | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [connectionToEdit, setConnectionToEdit] = useState<Connection | null>(null)
  const [dbType, setDbType] = useState<'postgres' | 'clickhouse'>('postgres')
  const [editFormData, setEditFormData] = useState({
    pg_host: '',
    pg_port: 5432,
    pg_database: '',
    pg_username: '',
    pg_password: '',
    ch_host: '',
    ch_port: 8123,
    ch_database: 'default',
    ch_username: 'default',
    ch_password: '',
    ch_secure: false
  })
  const [formData, setFormData] = useState({
    pg_host: '',
    pg_port: 5432,
    pg_database: '',
    pg_username: '',
    pg_password: '',
    ch_host: '',
    ch_port: 8123,
    ch_database: 'default',
    ch_username: 'default',
    ch_password: '',
    ch_secure: false
  })

  useEffect(() => {
    loadConnections()
  }, [])

  const loadConnections = async () => {
    try {
      const [connectionsData, agentsData] = await Promise.all([
        connectionsAPI.list(),
        agentsAPI.list()
      ])
      setConnections(connectionsData)
      setAgents(agentsData)
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
      toast.error('Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }

  const getAgentCount = (connectionId: number) => {
    return agents.filter(agent => agent.connection_id === connectionId).length
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsCreating(true)

    try {
      if (dbType === 'postgres') {
        await connectionsAPI.create({
          tipo: 'postgres',
          postgresql_config: {
            host: formData.pg_host,
            port: formData.pg_port,
            database: formData.pg_database,
            username: formData.pg_username,
            password: formData.pg_password
          }
        })
      } else {
        await connectionsAPI.create({
          tipo: 'clickhouse',
          clickhouse_config: {
            host: formData.ch_host,
            port: formData.ch_port,
            database: formData.ch_database,
            username: formData.ch_username,
            password: formData.ch_password,
            secure: formData.ch_secure
          }
        })
      }

      toast.success('Conexão criada com sucesso!')
      setIsModalOpen(false)
      setFormData({
        pg_host: '',
        pg_port: 5432,
        pg_database: '',
        pg_username: '',
        pg_password: '',
        ch_host: '',
        ch_port: 8123,
        ch_database: 'default',
        ch_username: 'default',
        ch_password: '',
        ch_secure: false
      })
      setDbType('postgres')
      loadConnections()
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao criar conexão'
      toast.error(message)
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteClick = (connection: Connection) => {
    setConnectionToDelete(connection)
  }

  const handleDeleteConfirm = async () => {
    if (!connectionToDelete) return

    setIsDeleting(connectionToDelete.id)
    try {
      await connectionsAPI.delete(connectionToDelete.id)
      toast.success('Conexão excluída com sucesso!')
      loadConnections()
      setConnectionToDelete(null)
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao excluir conexão'
      toast.error(message)
    } finally {
      setIsDeleting(null)
    }
  }

  const handleDeleteCancel = () => {
    setConnectionToDelete(null)
  }

  const handleEditClick = (connection: Connection) => {
    setConnectionToEdit(connection)

    // Parse pg_dsn para preencher o formulário
    if (connection.pg_dsn) {
      try {
        const url = new URL(connection.pg_dsn)
        setEditFormData({
          pg_host: url.hostname,
          pg_port: parseInt(url.port) || 5432,
          pg_database: url.pathname.slice(1), // Remove a barra inicial
          pg_username: url.username,
          pg_password: '' // Não mostramos a senha por segurança
        })
      } catch (error) {
        console.error('Erro ao parsear pg_dsn:', error)
        setEditFormData({
          pg_host: '',
          pg_port: 5432,
          pg_database: '',
          pg_username: '',
          pg_password: ''
        })
      }
    }

    setIsEditModalOpen(true)
  }

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!connectionToEdit) return

    setIsEditing(true)
    try {
      // Construir a nova connection string PostgreSQL
      const pg_dsn = `postgresql://${editFormData.pg_username}:${editFormData.pg_password}@${editFormData.pg_host}:${editFormData.pg_port}/${editFormData.pg_database}`

      await connectionsAPI.update(connectionToEdit.id, { pg_dsn })

      toast.success('Conexão atualizada com sucesso!')
      setIsEditModalOpen(false)
      setConnectionToEdit(null)
      loadConnections()
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao atualizar conexão'
      toast.error(message)
    } finally {
      setIsEditing(false)
    }
  }

  const handleEditCancel = () => {
    setIsEditModalOpen(false)
    setConnectionToEdit(null)
  }

  const handleTestConnection = async (formData: any) => {
    setIsTesting(true)
    try {
      let response

      if (dbType === 'postgres') {
        response = await connectionsAPI.test({
          tipo: 'postgres',
          postgresql_config: {
            host: formData.pg_host,
            port: formData.pg_port,
            database: formData.pg_database,
            username: formData.pg_username,
            password: formData.pg_password
          }
        })
      } else {
        response = await connectionsAPI.test({
          tipo: 'clickhouse',
          clickhouse_config: {
            host: formData.ch_host,
            port: formData.ch_port,
            database: formData.ch_database,
            username: formData.ch_username,
            password: formData.ch_password,
            secure: formData.ch_secure
          }
        })
      }

      if (response.valid) {
        toast.success(`✅ ${response.message}`)
      } else {
        toast.error(`❌ ${response.message}`)
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao testar conexão'
      toast.error(`❌ ${message}`)
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Conexões</h1>
            <p className="text-gray-600">Gerencie suas conexões com bancos de dados</p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-primary flex items-center"
          >
            <Plus className="mr-2 h-4 w-4" />
            Nova Conexão
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loading size="lg" />
          </div>
        ) : connections.length === 0 ? (
          <div className="card p-12 text-center">
            <Database className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">Nenhuma conexão</h3>
            <p className="mt-2 text-gray-500">
              Comece criando uma conexão com PostgreSQL ou ClickHouse.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="btn-primary mt-6"
            >
              Criar primeira conexão
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {connections.map((connection) => (
              <div key={connection.id} className="card p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center">
                    <div className={`p-2 rounded-lg ${
                      connection.tipo === 'clickhouse'
                        ? 'bg-orange-100'
                        : 'bg-green-100'
                    }`}>
                      <Database className={`h-6 w-6 ${
                        connection.tipo === 'clickhouse'
                          ? 'text-orange-600'
                          : 'text-green-600'
                      }`} />
                    </div>
                    <div className="ml-3">
                      <h3 className="text-lg font-medium text-gray-900">
                        Conexão {connection.tipo === 'clickhouse' ? 'ClickHouse' : 'PostgreSQL'} #{connection.id}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {connection.tipo === 'clickhouse' ? 'ClickHouse (OLAP)' : 'PostgreSQL (OLTP)'}
                      </p>
                    </div>
                  </div>
                  <DropdownMenu
                    items={[
                      {
                        label: 'Editar',
                        icon: <Edit className="h-4 w-4 text-blue-500" />,
                        onClick: () => handleEditClick(connection),
                        className: 'text-blue-600 hover:bg-blue-50'
                      },
                      {
                        label: 'Excluir',
                        icon: <Trash2 className="h-4 w-4 text-red-500" />,
                        onClick: () => handleDeleteClick(connection),
                        className: 'text-red-600 hover:bg-red-50'
                      }
                    ]}
                  />
                </div>
                
                <div className="mt-4 space-y-2">
                  <div className="text-sm">
                    <span className="text-gray-500">DSN:</span>
                    <span className="ml-2 text-gray-900 font-mono text-xs">
                      {connection.tipo === 'clickhouse'
                        ? (connection.ch_dsn ? connection.ch_dsn.replace(/:[^:@]*@/, ':***@') : 'N/A')
                        : (connection.pg_dsn ? connection.pg_dsn.replace(/:[^:@]*@/, ':***@') : 'N/A')
                      }
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500">Agentes:</span>
                    <span className="ml-2 text-gray-900">
                      {getAgentCount(connection.id)} agente(s)
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500">Criado em:</span>
                    <span className="ml-2 text-gray-900">{formatDate(connection.created_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Nova Conexão de Banco de Dados"
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Seletor de tipo de banco */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tipo de Banco de Dados
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setDbType('postgres')}
                  className={`p-4 border-2 rounded-lg text-left transition-all ${
                    dbType === 'postgres'
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-semibold text-gray-900">PostgreSQL</div>
                  <div className="text-xs text-gray-500 mt-1">OLTP - Transacional</div>
                </button>
                <button
                  type="button"
                  onClick={() => setDbType('clickhouse')}
                  className={`p-4 border-2 rounded-lg text-left transition-all ${
                    dbType === 'clickhouse'
                      ? 'border-orange-500 bg-orange-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-semibold text-gray-900">ClickHouse</div>
                  <div className="text-xs text-gray-500 mt-1">OLAP - Analítico</div>
                </button>
              </div>
            </div>

            {/* Campos PostgreSQL */}
            {dbType === 'postgres' && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Host
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.pg_host}
                      onChange={(e) => setFormData({ ...formData, pg_host: e.target.value })}
                      className="input-field mt-1"
                      placeholder="localhost"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Porta
                    </label>
                    <input
                      type="number"
                      required
                      value={formData.pg_port}
                      onChange={(e) => setFormData({ ...formData, pg_port: parseInt(e.target.value) })}
                      className="input-field mt-1"
                      placeholder="5432"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Database
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.pg_database}
                    onChange={(e) => setFormData({ ...formData, pg_database: e.target.value })}
                    className="input-field mt-1"
                    placeholder="nome_do_banco"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Usuário
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.pg_username}
                    onChange={(e) => setFormData({ ...formData, pg_username: e.target.value })}
                    className="input-field mt-1"
                    placeholder="postgres"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Senha
                  </label>
                  <input
                    type="password"
                    required
                    value={formData.pg_password}
                    onChange={(e) => setFormData({ ...formData, pg_password: e.target.value })}
                    className="input-field mt-1"
                    placeholder="••••••••"
                  />
                </div>
              </>
            )}

            {/* Campos ClickHouse */}
            {dbType === 'clickhouse' && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Host
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.ch_host}
                      onChange={(e) => setFormData({ ...formData, ch_host: e.target.value })}
                      className="input-field mt-1"
                      placeholder="localhost ou clickhouse.cloud"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Porta
                    </label>
                    <input
                      type="number"
                      required
                      value={formData.ch_port}
                      onChange={(e) => setFormData({ ...formData, ch_port: parseInt(e.target.value) })}
                      className="input-field mt-1"
                      placeholder="8123 (HTTP) ou 8443 (HTTPS)"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Database
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.ch_database}
                    onChange={(e) => setFormData({ ...formData, ch_database: e.target.value })}
                    className="input-field mt-1"
                    placeholder="default"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Usuário
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.ch_username}
                    onChange={(e) => setFormData({ ...formData, ch_username: e.target.value })}
                    className="input-field mt-1"
                    placeholder="default"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Senha
                  </label>
                  <input
                    type="password"
                    value={formData.ch_password}
                    onChange={(e) => setFormData({ ...formData, ch_password: e.target.value })}
                    className="input-field mt-1"
                    placeholder="••••••••"
                  />
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="ch_secure"
                    checked={formData.ch_secure}
                    onChange={(e) => setFormData({ ...formData, ch_secure: e.target.checked })}
                    className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded"
                  />
                  <label htmlFor="ch_secure" className="ml-2 block text-sm text-gray-700">
                    Usar HTTPS (recomendado para ClickHouse Cloud)
                  </label>
                </div>
              </>
            )}

            <div className="flex justify-between pt-4">
              <button
                type="button"
                onClick={() => handleTestConnection(formData)}
                disabled={isTesting || isCreating}
                className="btn-secondary flex items-center"
              >
                {isTesting ? (
                  <>
                    <Loading size="sm" className="mr-2" />
                    Testando...
                  </>
                ) : (
                  'Testar Conexão'
                )}
              </button>

              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-secondary"
                  disabled={isCreating}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isCreating || isTesting}
                  className="btn-primary flex items-center"
                >
                  {isCreating ? (
                    <>
                      <Loading size="sm" className="mr-2" />
                      Testando e criando...
                    </>
                  ) : (
                    'Criar Conexão'
                  )}
                </button>
              </div>
            </div>
          </form>
        </Modal>

        {/* Modal de Edição */}
        <Modal
          isOpen={isEditModalOpen}
          onClose={handleEditCancel}
          title="Editar Conexão PostgreSQL"
        >
          <form onSubmit={handleEditSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Host
                </label>
                <input
                  type="text"
                  required
                  value={editFormData.pg_host}
                  onChange={(e) => setEditFormData({ ...editFormData, pg_host: e.target.value })}
                  className="input-field mt-1"
                  placeholder="localhost"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Porta
                </label>
                <input
                  type="number"
                  required
                  value={editFormData.pg_port}
                  onChange={(e) => setEditFormData({ ...editFormData, pg_port: parseInt(e.target.value) })}
                  className="input-field mt-1"
                  placeholder="5432"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Database
              </label>
              <input
                type="text"
                required
                value={editFormData.pg_database}
                onChange={(e) => setEditFormData({ ...editFormData, pg_database: e.target.value })}
                className="input-field mt-1"
                placeholder="nome_do_banco"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Usuário
              </label>
              <input
                type="text"
                required
                value={editFormData.pg_username}
                onChange={(e) => setEditFormData({ ...editFormData, pg_username: e.target.value })}
                className="input-field mt-1"
                placeholder="postgres"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Senha
              </label>
              <input
                type="password"
                required
                value={editFormData.pg_password}
                onChange={(e) => setEditFormData({ ...editFormData, pg_password: e.target.value })}
                className="input-field mt-1"
                placeholder="••••••••"
              />
              <p className="text-xs text-gray-500 mt-1">
                Digite a senha novamente para confirmar as alterações
              </p>
            </div>

            <div className="flex justify-between pt-4">
              <button
                type="button"
                onClick={() => handleTestConnection(editFormData)}
                disabled={isTesting || isEditing}
                className="btn-secondary flex items-center"
              >
                {isTesting ? (
                  <>
                    <Loading size="sm" className="mr-2" />
                    Testando...
                  </>
                ) : (
                  'Testar Conexão'
                )}
              </button>

              <div className="flex space-x-3">
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
                  disabled={isEditing || isTesting}
                  className="btn-primary flex items-center"
                >
                  {isEditing ? (
                    <>
                      <Loading size="sm" className="mr-2" />
                      Testando e salvando...
                    </>
                  ) : (
                    'Salvar Alterações'
                  )}
                </button>
              </div>
            </div>
          </form>
        </Modal>

        {/* Modal de Confirmação de Exclusão */}
        <ConfirmDialog
          isOpen={!!connectionToDelete}
          onClose={handleDeleteCancel}
          onConfirm={handleDeleteConfirm}
          title="Excluir Conexão"
          description="Esta ação não pode ser desfeita."
          confirmText="Excluir"
          type="danger"
          isLoading={isDeleting === connectionToDelete?.id}
        >
          <div>
            <p className="text-sm text-gray-700">
              <strong>Conexão:</strong> PostgreSQL #{connectionToDelete?.id}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              <strong>Agentes afetados:</strong> {connectionToDelete ? getAgentCount(connectionToDelete.id) : 0}
            </p>
            {connectionToDelete && getAgentCount(connectionToDelete.id) > 0 && (
              <p className="text-sm text-red-600 mt-1">
                ⚠️ Todos os agentes que usam esta conexão serão afetados.
              </p>
            )}
          </div>
        </ConfirmDialog>
      </div>
    </DashboardLayout>
  )
}
