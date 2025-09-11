import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date) {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

export function formatDuration(ms: number) {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}min`
}

export function getStatusColor(status: string) {
  switch (status) {
    case 'completed':
    case 'success':
      return 'text-green-600 bg-green-100'
    case 'running':
      return 'text-blue-600 bg-blue-100'
    case 'queued':
      return 'text-yellow-600 bg-yellow-100'
    case 'failed':
    case 'failure':
      return 'text-red-600 bg-red-100'
    default:
      return 'text-gray-600 bg-gray-100'
  }
}

export function getStatusText(status: string) {
  switch (status) {
    case 'completed':
    case 'success':
      return 'Concluído'
    case 'running':
      return 'Executando'
    case 'queued':
      return 'Na fila'
    case 'failed':
    case 'failure':
      return 'Falhou'
    default:
      return status
  }
}

export function truncateText(text: string, maxLength: number = 100) {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export function formatJSON(data: any) {
  try {
    if (typeof data === 'string') {
      return JSON.stringify(JSON.parse(data), null, 2)
    }
    return JSON.stringify(data, null, 2)
  } catch {
    return data
  }
}
