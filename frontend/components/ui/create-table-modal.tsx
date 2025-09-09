'use client'

import { useState } from 'react'
import { Modal } from './modal'
import { Loading } from './loading'
import { Database, AlertCircle, CheckCircle } from 'lucide-react'
import { tablesAPI } from '@/lib/api'
import toast from 'react-hot-toast'

interface CreateTableModalProps {
  isOpen: boolean
  onClose: () => void
  sqlQuery: string
  agentId: number
  connectionType: string
}

export function CreateTableModal({
  isOpen,
  onClose,
  sqlQuery,
  agentId,
  connectionType
}: CreateTableModalProps) {
  const [tableName, setTableName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [result, setResult] = useState<{
    success: boolean
    message: string
    records_count?: number
  } | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!tableName.trim()) {
      toast.error('Nome da tabela é obrigatório')
      return
    }

    // Validação básica do nome da tabela
    const tableNamePattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/
    if (!tableNamePattern.test(tableName.trim())) {
      toast.error('Nome da tabela inválido. Use apenas letras, números e underscore, começando com letra.')
      return
    }

    setIsCreating(true)
    setResult(null)

    try {
      const response = await tablesAPI.create({
        table_name: tableName.trim(),
        sql_query: sqlQuery,
        agent_id: agentId
      })

      setResult(response)
      
      if (response.success) {
        toast.success('Tabela criada com sucesso!')
      } else {
        toast.error(response.message)
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao criar tabela'
      toast.error(message)
      setResult({
        success: false,
        message: message
      })
    } finally {
      setIsCreating(false)
    }
  }

  const handleClose = () => {
    setTableName('')
    setResult(null)
    onClose()
  }

  // Só mostrar para conexões PostgreSQL
  if (connectionType !== 'postgres' && connectionType !== 'postgresql') {
    return null
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Criar Tabela PostgreSQL"
      size="md"
    >
      <div className="space-y-4">
        {/* Ícone e descrição */}
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-full bg-blue-100">
            <Database className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-medium text-gray-900">
              Criar Nova Tabela
            </h3>
            <p className="text-sm text-gray-500">
              A tabela será criada com todos os dados da query (sem LIMIT)
            </p>
          </div>
        </div>

        {/* Formulário */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="tableName" className="block text-sm font-medium text-gray-700 mb-1">
              Nome da Tabela
            </label>
            <input
              type="text"
              id="tableName"
              value={tableName}
              onChange={(e) => setTableName(e.target.value)}
              placeholder="Digite o nome da nova tabela..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isCreating}
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Use apenas letras, números e underscore. Deve começar com letra.
            </p>
          </div>

          {/* Preview da Query */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Query SQL
            </label>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap">
                {sqlQuery}
              </pre>
            </div>
          </div>

          {/* Resultado */}
          {result && (
            <div className={`p-3 rounded-lg border ${
              result.success 
                ? 'bg-green-50 border-green-200' 
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center space-x-2">
                {result.success ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600" />
                )}
                <div>
                  <p className={`text-sm font-medium ${
                    result.success ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {result.message}
                  </p>
                  {result.success && result.records_count && (
                    <p className="text-xs text-green-600 mt-1">
                      {result.records_count} registros inseridos
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Botões */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="btn-secondary"
              disabled={isCreating}
            >
              {result?.success ? 'Fechar' : 'Cancelar'}
            </button>
            {!result?.success && (
              <button
                type="submit"
                disabled={isCreating || !tableName.trim()}
                className="btn-primary flex items-center"
              >
                {isCreating ? (
                  <>
                    <Loading size="sm" className="mr-2" />
                    Criando...
                  </>
                ) : (
                  <>
                    <Database className="h-4 w-4 mr-2" />
                    Criar Tabela
                  </>
                )}
              </button>
            )}
          </div>
        </form>
      </div>
    </Modal>
  )
}
