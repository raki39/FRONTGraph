import { cn } from '@/lib/utils'

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function Loading({ size = 'md', className }: LoadingProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  }

  return (
    <div className={cn('animate-spin rounded-full border-2 border-gray-300 border-t-primary-600', sizeClasses[size], className)} />
  )
}

export function LoadingDots() {
  return (
    <div className="loading-dots">
      <div style={{ animationDelay: '0ms' }}></div>
      <div style={{ animationDelay: '150ms' }}></div>
      <div style={{ animationDelay: '300ms' }}></div>
    </div>
  )
}

export function LoadingPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loading size="lg" />
        <p className="mt-4 text-gray-600">Carregando...</p>
      </div>
    </div>
  )
}
