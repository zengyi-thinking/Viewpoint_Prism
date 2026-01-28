/**
 * 认证状态管理 Store
 * 管理用户登录状态、Token、当前工程等
 */

import { create } from 'zustand'
import { authAPI } from '@/api/modules/auth'
import { projectAPI } from '@/api/modules/project'
import type {
  User,
  UserCreate,
  UserLogin,
  Project,
  ChangePassword,
} from '@/types/modules/auth'

interface AuthState {
  // 用户状态
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean

  // 工程状态
  currentProject: Project | null
  projects: Project[]

  // 加载状态
  isLoading: boolean
  error: string | null
}

interface AuthActions {
  // 用户操作
  login: (credentials: UserLogin) => Promise<void>
  register: (userData: UserCreate) => Promise<void>
  logout: () => Promise<void>
  updateProfile: (data: { email?: string }) => Promise<void>
  changePassword: (data: ChangePassword) => Promise<void>

  // 工程操作
  loadProjects: () => Promise<void>
  createProject: (name: string, description?: string) => Promise<void>
  updateProject: (projectId: string, name?: string, description?: string) => Promise<void>
  deleteProject: (projectId: string) => Promise<void>
  switchProject: (projectId: string) => Promise<void>

  // 状态管理
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setCurrentProject: (project: Project | null) => void
  clearAuth: () => void
  setError: (error: string | null) => void
}

export const useAuthStore = create<AuthState & AuthActions>()(
  (set, get) => ({
      // 初始状态
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      currentProject: null,
      projects: [],
      isLoading: false,
      error: null,

      // 用户操作
      login: async (credentials: UserLogin) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authAPI.login(credentials)

          // 保存到状态
          set({
            user: response.user,
            token: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            currentProject: response.current_project,
            isLoading: false,
          })

          // 保存到 localStorage（供 API 客户端使用）
          localStorage.setItem('access_token', response.access_token)
          localStorage.setItem('refresh_token', response.refresh_token)
          localStorage.setItem('user', JSON.stringify(response.user))
          if (response.current_project) {
            localStorage.setItem('current_project', JSON.stringify(response.current_project))
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '登录失败',
            isLoading: false,
          })
          throw error
        }
      },

      register: async (userData: UserCreate) => {
        set({ isLoading: true, error: null })
        try {
          await authAPI.register(userData)
          set({ isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '注册失败',
            isLoading: false,
          })
          throw error
        }
      },

      logout: async () => {
        try {
          await authAPI.logout()
        } catch (error) {
          console.error('登出失败:', error)
        } finally {
          get().clearAuth()
        }
      },

      updateProfile: async (data: { email?: string }) => {
        set({ isLoading: true, error: null })
        try {
          const user = await authAPI.updateMe(data)
          set({ user, isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '更新失败',
            isLoading: false,
          })
          throw error
        }
      },

      changePassword: async (data: ChangePassword) => {
        set({ isLoading: true, error: null })
        try {
          await authAPI.changePassword(data)
          set({ isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '修改密码失败',
            isLoading: false,
          })
          throw error
        }
      },

      // 工程操作
      loadProjects: async () => {
        set({ isLoading: true, error: null })
        try {
          const response = await projectAPI.getProjects()
          set({ projects: response.projects, isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '加载工程列表失败',
            isLoading: false,
          })
          throw error
        }
      },

      createProject: async (name: string, description?: string) => {
        set({ isLoading: true, error: null })
        try {
          const project = await projectAPI.createProject({ name, description })
          set((state) => ({
            projects: [...state.projects, project],
            currentProject: project,
            isLoading: false,
          }))
          localStorage.setItem('current_project', JSON.stringify(project))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '创建工程失败',
            isLoading: false,
          })
          throw error
        }
      },

      updateProject: async (projectId: string, name?: string, description?: string) => {
        set({ isLoading: true, error: null })
        try {
          const project = await projectAPI.updateProject(projectId, { name, description })
          set((state) => ({
            projects: state.projects.map((p) => (p.id === projectId ? project : p)),
            currentProject: state.currentProject?.id === projectId ? project : state.currentProject,
            isLoading: false,
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '更新工程失败',
            isLoading: false,
          })
          throw error
        }
      },

      deleteProject: async (projectId: string) => {
        set({ isLoading: true, error: null })
        try {
          await projectAPI.deleteProject(projectId)
          set((state) => ({
            projects: state.projects.filter((p) => p.id !== projectId),
            currentProject: state.currentProject?.id === projectId ? null : state.currentProject,
            isLoading: false,
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '删除工程失败',
            isLoading: false,
          })
          throw error
        }
      },

      switchProject: async (projectId: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await projectAPI.switchProject(projectId)
          set({
            currentProject: response.current_project,
            isLoading: false,
          })
          localStorage.setItem('current_project', JSON.stringify(response.current_project))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '切换工程失败',
            isLoading: false,
          })
          throw error
        }
      },

      // 状态管理
      setUser: (user: User | null) => set({ user }),
      setToken: (token: string | null) => set({ token }),
      setCurrentProject: (project: Project | null) => {
        set({ currentProject: project })
        if (project) {
          localStorage.setItem('current_project', JSON.stringify(project))
        } else {
          localStorage.removeItem('current_project')
        }
      },
      clearAuth: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          currentProject: null,
          projects: [],
          error: null,
        })
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        localStorage.removeItem('current_project')
      },
      setError: (error: string | null) => set({ error }),
    })
  )

// 监听登出事件
if (typeof window !== 'undefined') {
  window.addEventListener('auth:logout', () => {
    useAuthStore.getState().clearAuth()
  })
}
