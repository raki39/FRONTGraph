'use client'

import { useState } from 'react'
import { validationAPI } from '@/lib/api'
import { Loading } from '@/components/ui/loading'
import { BarChart3, CheckCircle, AlertCircle, TrendingUp, MessageSquare } from 'lucide-react'
import toast from 'react-hot-toast'

interface ChatValidationProps {
  sessionId: number
  sessionTitle: string
  onValidationComplete?: (result: any) => void
}

interface ValidationResult {
  success: boolean
  message: string
  validation_result: {
    overall_score: number
    question_clarity: number
    query_correctness: number
    response_accuracy: number
    suggestions: string[]
  }
  execution_time: number
  metadata: {
    session_id: number
    total_runs: number
    average_score: number
    consistency_analysis: {
      consistency_score: number
      score_variance: number
      suggestions: string[]
    }
    individual_results: any[]
  }
}

export function ChatValidation({ sessionId, sessionTitle, onValidationComplete }: ChatValidationProps) {
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [validationType, setValidationType] = useState('individual')
  const [validationModel, setValidationModel] = useState('gpt-4o-mini')

  const handleValidate = async () => {
    setValidating(true)
    try {
      const result = await validationAPI.validateChatSession(sessionId, validationType, validationModel)
      setValidationResult(result)
      onValidationComplete?.(result)
      toast.success('Validação da sessão concluída!')
    } catch (error: any) {
      console.error('Erro na validação:', error)
      toast.error(error.response?.data?.detail || 'Erro ao validar sessão')
    } finally {
      setValidating(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600 bg-green-50'
    if (score >= 6) return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  const getScoreIcon = (score: number) => {
    if (score >= 8) return <CheckCircle className="h-4 w-4" />
    if (score >= 6) return <AlertCircle className="h-4 w-4" />
    return <AlertCircle className="h-4 w-4" />
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <BarChart3 className="h-5 w-5 mr-2 text-blue-600" />
            Validação da Conversa
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Analise a qualidade e consistência de toda a sessão de chat
          </p>
        </div>
      </div>

      {/* Configurações de Validação */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tipo de Validação
          </label>
          <select
            value={validationType}
            onChange={(e) => setValidationType(e.target.value)}
            className="input-field"
            disabled={validating}
          >
            <option value="individual">Individual</option>
            <option value="comparative">Comparativa</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Modelo de Validação
          </label>
          <select
            value={validationModel}
            onChange={(e) => setValidationModel(e.target.value)}
            className="input-field"
            disabled={validating}
          >
            <option value="gpt-4o-mini">GPT-4o Mini</option>
            <option value="gpt-4o">GPT-4o</option>
            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
          </select>
        </div>
      </div>

      {/* Botão de Validação */}
      <button
        onClick={handleValidate}
        disabled={validating}
        className="btn-primary w-full mb-6 flex items-center justify-center"
      >
        {validating ? (
          <>
            <Loading size="sm" />
            <span className="ml-2">Validando sessão...</span>
          </>
        ) : (
          <>
            <BarChart3 className="h-4 w-4 mr-2" />
            Validar Sessão Completa
          </>
        )}
      </button>

      {/* Resultados da Validação */}
      {validationResult && (
        <div className="space-y-6">
          {/* Resumo Geral */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-blue-900">Resumo da Validação</h4>
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(validationResult.validation_result.overall_score)}`}>
                {validationResult.validation_result.overall_score.toFixed(1)}/10
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Interações:</span>
                <div className="font-medium text-blue-900">{validationResult.metadata.total_runs}</div>
              </div>
              <div>
                <span className="text-gray-600">Score Médio:</span>
                <div className="font-medium text-blue-900">{validationResult.metadata.average_score.toFixed(1)}</div>
              </div>
              <div>
                <span className="text-gray-600">Consistência:</span>
                <div className="font-medium text-blue-900">{validationResult.metadata.consistency_analysis.consistency_score.toFixed(1)}</div>
              </div>
              <div>
                <span className="text-gray-600">Tempo:</span>
                <div className="font-medium text-blue-900">{validationResult.execution_time.toFixed(1)}s</div>
              </div>
            </div>
          </div>

          {/* Métricas Detalhadas */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Clareza das Perguntas</span>
                {getScoreIcon(validationResult.validation_result.question_clarity)}
              </div>
              <div className={`text-2xl font-bold ${getScoreColor(validationResult.validation_result.question_clarity).split(' ')[0]}`}>
                {validationResult.validation_result.question_clarity.toFixed(1)}
              </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Correção das Queries</span>
                {getScoreIcon(validationResult.validation_result.query_correctness)}
              </div>
              <div className={`text-2xl font-bold ${getScoreColor(validationResult.validation_result.query_correctness).split(' ')[0]}`}>
                {validationResult.validation_result.query_correctness.toFixed(1)}
              </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Precisão das Respostas</span>
                {getScoreIcon(validationResult.validation_result.response_accuracy)}
              </div>
              <div className={`text-2xl font-bold ${getScoreColor(validationResult.validation_result.response_accuracy).split(' ')[0]}`}>
                {validationResult.validation_result.response_accuracy.toFixed(1)}
              </div>
            </div>
          </div>

          {/* Análise de Consistência */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
              <TrendingUp className="h-4 w-4 mr-2 text-green-600" />
              Análise de Consistência
            </h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Score de Consistência:</span>
                <span className={`font-medium ${getScoreColor(validationResult.metadata.consistency_analysis.consistency_score).split(' ')[0]}`}>
                  {validationResult.metadata.consistency_analysis.consistency_score.toFixed(1)}/10
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Variância dos Scores:</span>
                <span className="font-medium text-gray-900">
                  {validationResult.metadata.consistency_analysis.score_variance.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          {/* Sugestões */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
              <MessageSquare className="h-4 w-4 mr-2 text-blue-600" />
              Sugestões de Melhoria
            </h4>
            <div className="space-y-2">
              {validationResult.validation_result.suggestions.map((suggestion, index) => (
                <div key={index} className="flex items-start">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                  <span className="text-sm text-gray-700">{suggestion}</span>
                </div>
              ))}
              {validationResult.metadata.consistency_analysis.suggestions.map((suggestion, index) => (
                <div key={`consistency-${index}`} className="flex items-start">
                  <div className="w-2 h-2 bg-green-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                  <span className="text-sm text-gray-700">{suggestion}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
