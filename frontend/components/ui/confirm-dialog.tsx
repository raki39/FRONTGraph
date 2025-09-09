'use client'

import { Modal } from './modal'
import { Loading } from './loading'
import { AlertTriangle, Trash2, Info } from 'lucide-react'

interface ConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  description: string
  confirmText?: string
  cancelText?: string
  type?: 'danger' | 'warning' | 'info'
  isLoading?: boolean
  children?: React.ReactNode
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmText = 'Confirmar',
  cancelText = 'Cancelar',
  type = 'danger',
  isLoading = false,
  children
}: ConfirmDialogProps) {
  const getIcon = () => {
    switch (type) {
      case 'danger':
        return <Trash2 className="h-6 w-6 text-red-600" />
      case 'warning':
        return <AlertTriangle className="h-6 w-6 text-yellow-600" />
      case 'info':
        return <Info className="h-6 w-6 text-blue-600" />
      default:
        return <AlertTriangle className="h-6 w-6 text-gray-600" />
    }
  }

  const getIconBg = () => {
    switch (type) {
      case 'danger':
        return 'bg-red-100'
      case 'warning':
        return 'bg-yellow-100'
      case 'info':
        return 'bg-blue-100'
      default:
        return 'bg-gray-100'
    }
  }

  const getConfirmButtonClass = () => {
    switch (type) {
      case 'danger':
        return 'bg-red-600 hover:bg-red-700 text-white'
      case 'warning':
        return 'bg-yellow-600 hover:bg-yellow-700 text-white'
      case 'info':
        return 'bg-blue-600 hover:bg-blue-700 text-white'
      default:
        return 'bg-gray-600 hover:bg-gray-700 text-white'
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
    >
      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-full ${getIconBg()}`}>
            {getIcon()}
          </div>
          <div>
            <h3 className="text-lg font-medium text-gray-900">
              {title}
            </h3>
            <p className="text-sm text-gray-500">
              {description}
            </p>
          </div>
        </div>
        
        {children && (
          <div className="bg-gray-50 rounded-lg p-3">
            {children}
          </div>
        )}

        <div className="flex justify-end space-x-3 pt-4">
          <button
            onClick={onClose}
            className="btn-secondary"
            disabled={isLoading}
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className={`font-medium py-2 px-4 rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center ${getConfirmButtonClass()}`}
          >
            {isLoading ? (
              <>
                <Loading size="sm" className="mr-2" />
                Processando...
              </>
            ) : (
              confirmText
            )}
          </button>
        </div>
      </div>
    </Modal>
  )
}
