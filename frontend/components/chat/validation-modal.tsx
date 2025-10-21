'use client'

import { useState } from 'react'
import { validationAPI } from '@/lib/api'
import { Loading } from '@/components/ui/loading'
import { X, CheckCircle, AlertCircle, TrendingUp, MessageSquare, Code } from 'lucide-react'
import toast from 'react-hot-toast'

interface ValidationModalProps {
  isOpen: boolean
  onClose: () => void
  sessionId: number
  sessionTitle: string
}

export function ValidationModal({ isOpen, onClose, sessionId, sessionTitle }: ValidationModalProps) {
  const [validating, setValidating] = useState(false)
  const [validationType, setValidationType] = useState('individual')
  const [validationModel, setValidationModel] = useState('gpt-4o-mini')
  const [numRunsToCompare, setNumRunsToCompare] = useState(3)
  const [validationResult, setValidationResult] = useState<any>(null)
  const [activeTab, setActiveTab] = useState('results')

  if (!isOpen) return null

  const handleValidate = async () => {
    setValidating(true)
    setValidationResult(null)
    try {
      const result = await validationAPI.validateChatSession(
        sessionId,
        validationType,
        validationModel,
        validationType === 'comparative' ? numRunsToCompare : undefined
      )
      console.log('🔍 Resultado da validação:', result)
      console.log('📋 Suggestions:', result.validation_result?.suggestions)
      console.log('💬 Observations:', result.validation_result?.observations)
      console.log('✨ Improved Question:', result.validation_result?.improved_question)
      console.log('📊 Validation Results:', result.metadata?.validation_results)
      setValidationResult(result)
      toast.success('Validação concluída com sucesso!')
    } catch (error: any) {
      console.error('Erro na validação:', error)
      toast.error(error.response?.data?.detail || 'Erro ao validar sessão')
    } finally {
      setValidating(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600'
    if (score >= 6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreBgColor = (score: number) => {
    if (score >= 8) return 'bg-green-100'
    if (score >= 6) return 'bg-yellow-100'
    return 'bg-red-100'
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Validar Conversa</h2>
            <p className="text-sm text-gray-500 mt-1">{sessionTitle}</p>
          </div>
          <button
            onClick={onClose}
            disabled={validating}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6">
          {!validationResult ? (
            <>
              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tipo de Validação
                  </label>
                  <div className="flex gap-3">
                    <button
                      onClick={() => setValidationType('individual')}
                      className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                        validationType === 'individual'
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-gray-300 text-gray-700 hover:border-gray-400'
                      }`}
                    >
                      Individual
                    </button>
                    <button
                      onClick={() => setValidationType('comparative')}
                      className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                        validationType === 'comparative'
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-gray-300 text-gray-700 hover:border-gray-400'
                      }`}
                    >
                      Comparativa
                    </button>
                  </div>
                </div>

                {validationType === 'comparative' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Número de Interações para Comparar
                    </label>
                    <input
                      type="number"
                      min="2"
                      max="10"
                      value={numRunsToCompare}
                      onChange={(e) => setNumRunsToCompare(parseInt(e.target.value))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Modelo de Validação
                  </label>
                  <select
                    value={validationModel}
                    onChange={(e) => setValidationModel(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="gpt-4o-mini">GPT-4o Mini (Rápido)</option>
                    <option value="gpt-4o">GPT-4o (Preciso)</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleValidate}
                  disabled={validating}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  {validating ? (
                    <>
                      <Loading size="sm" />
                      Validando...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-5 w-5" />
                      Validar
                    </>
                  )}
                </button>
                <button
                  onClick={onClose}
                  disabled={validating}
                  className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  Cancelar
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="flex gap-2 mb-6 border-b border-gray-200">
                <button
                  onClick={() => setActiveTab('results')}
                  className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'results'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  📊 Resultados
                </button>
                <button
                  onClick={() => setActiveTab('interactions')}
                  className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'interactions'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  💬 Interações Validadas
                </button>
              </div>

              {activeTab === 'results' ? (
                <div className="space-y-6">
                  {/* SCORES */}
                  <div className={`p-4 rounded-lg ${getScoreBgColor(validationResult.validation_result.overall_score)}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-700">Score Geral</p>
                        <p className={`text-3xl font-bold ${getScoreColor(validationResult.validation_result.overall_score)}`}>
                          {validationResult.validation_result.overall_score.toFixed(2)}/10
                        </p>
                      </div>
                      <TrendingUp className={`h-12 w-12 ${getScoreColor(validationResult.validation_result.overall_score)}`} />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <p className="text-xs font-medium text-gray-600 mb-2">Clareza da Pergunta</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {validationResult.validation_result.question_clarity.toFixed(1)}
                      </p>
                    </div>
                    <div className="p-4 bg-purple-50 rounded-lg">
                      <p className="text-xs font-medium text-gray-600 mb-2">Correção da Query</p>
                      <p className="text-2xl font-bold text-purple-600">
                        {validationResult.validation_result.query_correctness.toFixed(1)}
                      </p>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg">
                      <p className="text-xs font-medium text-gray-600 mb-2">Precisão da Resposta</p>
                      <p className="text-2xl font-bold text-green-600">
                        {validationResult.validation_result.response_accuracy.toFixed(1)}
                      </p>
                    </div>
                  </div>

                  {/* PROBLEMAS ENCONTRADOS - PRIORIDADE MÁXIMA */}
                  {validationResult.validation_result.issues_found && validationResult.validation_result.issues_found.length > 0 && (
                    <div className="p-5 bg-red-50 rounded-lg border-2 border-red-300 shadow-sm">
                      <p className="text-base font-bold text-red-800 mb-3 flex items-center gap-2">
                        <AlertCircle className="h-5 w-5 text-red-600" />
                        🚨 Problemas Encontrados
                      </p>
                      <ul className="space-y-2">
                        {validationResult.validation_result.issues_found.map((issue: string, idx: number) => (
                          <li key={idx} className="text-sm text-gray-800 flex gap-2 items-start">
                            <span className="text-red-600 font-bold mt-0.5">•</span>
                            <span className="flex-1">{issue}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* INCONSISTÊNCIAS - PARA VALIDAÇÃO COMPARATIVA */}
                  {validationResult.validation_result.inconsistencies_found && validationResult.validation_result.inconsistencies_found.length > 0 && (
                    <div className="p-5 bg-orange-50 rounded-lg border-2 border-orange-300 shadow-sm">
                      <p className="text-base font-bold text-orange-800 mb-3 flex items-center gap-2">
                        <AlertCircle className="h-5 w-5 text-orange-600" />
                        ⚠️ Inconsistências Encontradas
                      </p>
                      <ul className="space-y-2">
                        {validationResult.validation_result.inconsistencies_found.map((inconsistency: string, idx: number) => (
                          <li key={idx} className="text-sm text-gray-800 flex gap-2 items-start">
                            <span className="text-orange-600 font-bold mt-0.5">•</span>
                            <span className="flex-1">{inconsistency}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* OBSERVAÇÕES DA LLM */}
                  {validationResult.validation_result.observations ? (
                    <div className="p-5 bg-indigo-50 rounded-lg border-2 border-indigo-300 shadow-sm">
                      <p className="text-base font-bold text-indigo-800 mb-3 flex items-center gap-2">
                        📝 Observações da Análise
                      </p>
                      <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                        {validationResult.validation_result.observations}
                      </p>
                    </div>
                  ) : (
                    <div className="p-4 bg-gray-100 rounded-lg border border-gray-300">
                      <p className="text-sm text-gray-600 text-center">
                        ⚠️ Nenhuma observação foi gerada pela LLM
                      </p>
                    </div>
                  )}

                  {/* SUGESTÕES DA LLM */}
                  {validationResult.validation_result.suggestions ? (
                    <div className="p-5 bg-amber-50 rounded-lg border-2 border-amber-300 shadow-sm">
                      <p className="text-base font-bold text-amber-800 mb-3 flex items-center gap-2">
                        💡 Sugestões de Melhoria
                      </p>
                      <div className="text-sm text-gray-800 leading-relaxed">
                        {typeof validationResult.validation_result.suggestions === 'string' ? (
                          // Separar por números (1. 2. 3. etc) e criar lista
                          validationResult.validation_result.suggestions.split(/(?=\d+\.\s)/).filter((s: string) => s.trim()).length > 1 ? (
                            <ul className="space-y-2">
                              {validationResult.validation_result.suggestions.split(/(?=\d+\.\s)/).filter((s: string) => s.trim()).map((suggestion: string, idx: number) => (
                                <li key={idx} className="flex gap-2 items-start">
                                  <span className="text-amber-600 font-bold mt-0.5">•</span>
                                  <span className="flex-1">{suggestion.replace(/^\d+\.\s*/, '').trim()}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="whitespace-pre-wrap">{validationResult.validation_result.suggestions}</p>
                          )
                        ) : Array.isArray(validationResult.validation_result.suggestions) ? (
                          <ul className="space-y-2">
                            {validationResult.validation_result.suggestions.map((s: string, idx: number) => (
                              <li key={idx} className="flex gap-2 items-start">
                                <span className="text-amber-600 font-bold mt-0.5">•</span>
                                <span className="flex-1">{s}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          'Nenhuma sugestão disponível'
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 bg-gray-100 rounded-lg border border-gray-300">
                      <p className="text-sm text-gray-600 text-center">
                        ⚠️ Nenhuma sugestão foi gerada pela LLM
                      </p>
                    </div>
                  )}

                  {/* PERGUNTA CORRIGIDA/MELHORADA */}
                  {validationResult.validation_result.improved_question ? (
                    <div className="p-5 bg-green-50 rounded-lg border-2 border-green-300 shadow-sm">
                      <p className="text-base font-bold text-green-800 mb-3 flex items-center gap-2">
                        ✨ Pergunta Corrigida/Melhorada
                      </p>
                      <p className="text-base text-green-900 italic font-medium">
                        "{validationResult.validation_result.improved_question}"
                      </p>
                    </div>
                  ) : (
                    <div className="p-4 bg-gray-100 rounded-lg border border-gray-300">
                      <p className="text-sm text-gray-600 text-center">
                        ⚠️ Nenhuma pergunta corrigida foi gerada pela LLM
                      </p>
                    </div>
                  )}

                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-700">{validationResult.message}</p>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => setValidationResult(null)}
                      className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 font-medium"
                    >
                      Nova Validação
                    </button>
                    <button
                      onClick={onClose}
                      className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300 font-medium"
                    >
                      Fechar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {validationResult.metadata?.validation_results && validationResult.metadata.validation_results.length > 0 ? (
                    validationResult.metadata.validation_results.map((result: any, idx: number) => (
                      <div key={idx} className="border-2 border-gray-300 rounded-lg p-5 hover:bg-gray-50 transition-colors shadow-sm">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <p className="text-base font-bold text-gray-900 mb-1">
                              🔹 Interação {idx + 1}
                            </p>
                            <p className="text-xs text-gray-500">Run ID: {result.run_id}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-gray-600 mb-1">Score Geral</p>
                            <p className="text-2xl font-bold text-blue-600">
                              {result.validation_result.overall_score.toFixed(1)}/10
                            </p>
                          </div>
                        </div>

                        {/* PERGUNTA */}
                        <div className="mb-3 p-4 bg-blue-50 rounded-lg border-2 border-blue-200">
                          <p className="text-xs font-bold text-blue-800 mb-2 flex items-center gap-2">
                            <MessageSquare className="h-4 w-4" />
                            💬 PERGUNTA DO USUÁRIO
                          </p>
                          <p className="text-sm text-gray-900 leading-relaxed">{result.question}</p>
                        </div>

                        {/* QUERY SQL */}
                        <div className="mb-3 p-4 bg-gray-100 rounded-lg border-2 border-gray-300">
                          <p className="text-xs font-bold text-gray-700 mb-2 flex items-center gap-2">
                            <Code className="h-4 w-4" />
                            💻 QUERY SQL GERADA
                          </p>
                          <pre className="text-xs text-gray-800 font-mono whitespace-pre-wrap break-words overflow-x-auto">
                            {result.validation_result.sql_query || 'Não disponível'}
                          </pre>
                        </div>

                        {/* RESPOSTA */}
                        {result.validation_result.response && (
                          <div className="mb-3 p-4 bg-green-50 rounded-lg border-2 border-green-200">
                            <p className="text-xs font-bold text-green-800 mb-2 flex items-center gap-2">
                              <CheckCircle className="h-4 w-4" />
                              ✅ RESPOSTA FORNECIDA
                            </p>
                            <p className="text-sm text-gray-900 leading-relaxed whitespace-pre-wrap">
                              {result.validation_result.response}
                            </p>
                          </div>
                        )}

                        {/* SCORES INDIVIDUAIS */}
                        <div className="grid grid-cols-3 gap-3 mt-4">
                          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 text-center">
                            <p className="text-xs text-gray-600 mb-1">Clareza</p>
                            <p className="text-lg font-bold text-blue-600">
                              {result.validation_result.question_clarity.toFixed(1)}
                            </p>
                          </div>
                          <div className="p-3 bg-purple-50 rounded-lg border border-purple-200 text-center">
                            <p className="text-xs text-gray-600 mb-1">Query</p>
                            <p className="text-lg font-bold text-purple-600">
                              {result.validation_result.query_correctness.toFixed(1)}
                            </p>
                          </div>
                          <div className="p-3 bg-green-50 rounded-lg border border-green-200 text-center">
                            <p className="text-xs text-gray-600 mb-1">Resposta</p>
                            <p className="text-lg font-bold text-green-600">
                              {result.validation_result.response_accuracy.toFixed(1)}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-8 bg-gray-50 rounded-lg border-2 border-gray-300 text-center">
                      <p className="text-base text-gray-600 font-medium">⚠️ Nenhuma interação validada</p>
                      <p className="text-sm text-gray-500 mt-2">Verifique os logs do console para mais detalhes</p>
                    </div>
                  )}

                  <div className="flex gap-3 mt-6">
                    <button
                      onClick={() => setValidationResult(null)}
                      className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 font-medium"
                    >
                      Nova Validação
                    </button>
                    <button
                      onClick={onClose}
                      className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300 font-medium"
                    >
                      Fechar
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

