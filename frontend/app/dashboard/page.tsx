'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { agentsAPI, connectionsAPI, runsAPI, Agent, Connection, Run, PaginatedRunsResponse } from '@/lib/api'
import { Loading } from '@/components/ui/loading'
import { formatDate, getStatusColor, getStatusText } from '@/lib/utils'
import { Bot, Database, MessageSquare, Activity } from 'lucide-react'
import Link from 'next/link'

export default function DashboardPage() {
  const [stats, setStats] = useState({
    agents: 0,
    connections: 0,
    totalRuns: 0,
    recentRuns: [] as Run[]
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [agents, connections, runsResponse] = await Promise.all([
          agentsAPI.list(),
          connectionsAPI.list(),
          runsAPI.list(undefined, 1, 5) // Primeira página, 5 itens para recent runs
        ])

        setStats({
          agents: agents.length,
          connections: connections.length,
          totalRuns: runsResponse.pagination.total_items,
          recentRuns: runsResponse.runs
        })
      } catch (error) {
        console.error('Erro ao carregar estatísticas:', error)
      } finally {
        setLoading(false)
      }
    }

    loadStats()
  }, [])

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loading size="lg" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Visão geral dos seus agentes e atividades</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="card p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Bot className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Agentes</p>
                <p className="text-2xl font-bold text-gray-900">{stats.agents}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <Database className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Conexões</p>
                <p className="text-2xl font-bold text-gray-900">{stats.connections}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <MessageSquare className="h-6 w-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total de Runs</p>
                <p className="text-2xl font-bold text-gray-900">{stats.totalRuns}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center">
              <div className="p-2 bg-orange-100 rounded-lg">
                <Activity className="h-6 w-6 text-orange-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Runs Recentes</p>
                <p className="text-2xl font-bold text-gray-900">{stats.recentRuns.length}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Atividade Recente</h2>
          </div>
          <div className="p-6">
            {stats.recentRuns.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">Nenhuma atividade</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Comece criando um agente e fazendo perguntas.
                </p>
                <div className="mt-6">
                  <Link href="/agents" className="btn-primary">
                    Criar Agente
                  </Link>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {stats.recentRuns.map((run) => (
                  <div key={run.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {run.question}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatDate(run.created_at)}
                      </p>
                    </div>
                    <div className="ml-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(run.status)}`}>
                        {getStatusText(run.status)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link href="/agents" className="card p-6 hover:shadow-lg transition-shadow">
            <div className="text-center">
              <Bot className="mx-auto h-12 w-12 text-primary-600" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">Gerenciar Agentes</h3>
              <p className="mt-2 text-sm text-gray-500">
                Crie e configure seus agentes de IA
              </p>
            </div>
          </Link>

          <Link href="/connections" className="card p-6 hover:shadow-lg transition-shadow">
            <div className="text-center">
              <Database className="mx-auto h-12 w-12 text-primary-600" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">Conexões</h3>
              <p className="mt-2 text-sm text-gray-500">
                Configure conexões com bancos de dados
              </p>
            </div>
          </Link>

          <Link href="/chat" className="card p-6 hover:shadow-lg transition-shadow">
            <div className="text-center">
              <MessageSquare className="mx-auto h-12 w-12 text-primary-600" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">Chat</h3>
              <p className="mt-2 text-sm text-gray-500">
                Converse com seus agentes
              </p>
            </div>
          </Link>
        </div>
      </div>
    </DashboardLayout>
  )
}
