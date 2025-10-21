'use client'

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { PaginationInfo } from '@/lib/api'

interface PaginationProps {
  pagination: PaginationInfo
  onPageChange: (page: number) => void
  className?: string
}

export function Pagination({ pagination, onPageChange, className = '' }: PaginationProps) {
  const { page, total_pages, has_prev, has_next } = pagination

  // Gerar números das páginas para exibir
  const getPageNumbers = () => {
    const pages: (number | string)[] = []
    const maxVisible = 5 // Máximo de páginas visíveis

    if (total_pages <= maxVisible) {
      // Se temos poucas páginas, mostrar todas
      for (let i = 1; i <= total_pages; i++) {
        pages.push(i)
      }
    } else {
      // Lógica para páginas com ellipsis
      if (page <= 3) {
        // Início: 1, 2, 3, 4, ..., last
        for (let i = 1; i <= 4; i++) {
          pages.push(i)
        }
        if (total_pages > 5) {
          pages.push('...')
          pages.push(total_pages)
        }
      } else if (page >= total_pages - 2) {
        // Final: 1, ..., last-3, last-2, last-1, last
        pages.push(1)
        if (total_pages > 5) {
          pages.push('...')
        }
        for (let i = total_pages - 3; i <= total_pages; i++) {
          pages.push(i)
        }
      } else {
        // Meio: 1, ..., current-1, current, current+1, ..., last
        pages.push(1)
        pages.push('...')
        for (let i = page - 1; i <= page + 1; i++) {
          pages.push(i)
        }
        pages.push('...')
        pages.push(total_pages)
      }
    }

    return pages
  }

  if (total_pages <= 1) {
    return null // Não mostrar paginação se só há uma página
  }

  return (
    <div className={`flex items-center justify-between ${className}`}>
      {/* Informações da página */}
      <div className="text-sm text-gray-700">
        Página <span className="font-medium">{page}</span> de{' '}
        <span className="font-medium">{total_pages}</span>
        {' '}({pagination.total_items} itens)
      </div>

      {/* Navegação */}
      <div className="flex items-center space-x-2">
        {/* Botão Anterior */}
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={!has_prev}
          className={`
            flex items-center px-3 py-2 text-sm font-medium rounded-md
            ${has_prev 
              ? 'text-gray-500 bg-white border border-gray-300 hover:bg-gray-50 hover:text-gray-700' 
              : 'text-gray-300 bg-gray-100 border border-gray-200 cursor-not-allowed'
            }
          `}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Anterior
        </button>

        {/* Números das páginas */}
        <div className="flex space-x-1">
          {getPageNumbers().map((pageNum, index) => (
            <button
              key={index}
              onClick={() => typeof pageNum === 'number' ? onPageChange(pageNum) : undefined}
              disabled={typeof pageNum === 'string'}
              className={`
                px-3 py-2 text-sm font-medium rounded-md
                ${pageNum === page
                  ? 'bg-blue-600 text-white border border-blue-600'
                  : typeof pageNum === 'string'
                  ? 'text-gray-400 cursor-default'
                  : 'text-gray-500 bg-white border border-gray-300 hover:bg-gray-50 hover:text-gray-700'
                }
              `}
            >
              {pageNum}
            </button>
          ))}
        </div>

        {/* Botão Próximo */}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={!has_next}
          className={`
            flex items-center px-3 py-2 text-sm font-medium rounded-md
            ${has_next 
              ? 'text-gray-500 bg-white border border-gray-300 hover:bg-gray-50 hover:text-gray-700' 
              : 'text-gray-300 bg-gray-100 border border-gray-200 cursor-not-allowed'
            }
          `}
        >
          Próximo
          <ChevronRight className="h-4 w-4 ml-1" />
        </button>
      </div>
    </div>
  )
}

// Componente simples para paginação básica
export function SimplePagination({ pagination, onPageChange, className = '' }: PaginationProps) {
  const { page, total_pages, has_prev, has_next } = pagination

  if (total_pages <= 1) {
    return null
  }

  return (
    <div className={`flex items-center justify-between ${className}`}>
      <div className="text-sm text-gray-700">
        {pagination.total_items} itens
      </div>
      
      <div className="flex space-x-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={!has_prev}
          className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Anterior
        </button>
        
        <span className="px-3 py-2 text-sm text-gray-700">
          {page} / {total_pages}
        </span>
        
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={!has_next}
          className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Próximo
        </button>
      </div>
    </div>
  )
}
