'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import Cookies from 'js-cookie'
import { User, authAPI } from './api'
import toast from 'react-hot-toast'

interface AuthContextType {
  user: User | null
  login: (email: string, password: string) => Promise<boolean>
  register: (nome: string, email: string, password: string) => Promise<boolean>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      const token = Cookies.get('token')
      const savedUser = Cookies.get('user')
      
      if (token && savedUser) {
        try {
          const userData = JSON.parse(savedUser)
          setUser(userData)
          
          // Verificar se o token ainda é válido
          await authAPI.me()
        } catch (error) {
          console.error('Token inválido:', error)
          Cookies.remove('token')
          Cookies.remove('user')
          setUser(null)
        }
      }
      
      setLoading(false)
    }

    initAuth()
  }, [])

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      const response = await authAPI.login(email, password)
      
      Cookies.set('token', response.access_token, { expires: 7 })
      Cookies.set('user', JSON.stringify(response.user), { expires: 7 })
      
      setUser(response.user)
      toast.success('Login realizado com sucesso!')
      return true
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao fazer login'
      toast.error(message)
      return false
    }
  }

  const register = async (nome: string, email: string, password: string): Promise<boolean> => {
    try {
      await authAPI.register(nome, email, password)
      toast.success('Conta criada com sucesso! Faça login para continuar.')
      return true
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao criar conta'
      toast.error(message)
      return false
    }
  }

  const logout = () => {
    Cookies.remove('token')
    Cookies.remove('user')
    setUser(null)
    toast.success('Logout realizado com sucesso!')
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider')
  }
  return context
}
