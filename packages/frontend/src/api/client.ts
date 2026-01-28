const API_BASE = 'http://localhost:8000/api'
export const BACKEND_BASE = 'http://localhost:8000'

/**
 * API 客户端类
 * 支持自动添加 Token 和处理 Token 过期
 */
class ApiClient {
  private getToken(): string | null {
    return localStorage.getItem('access_token')
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`
    const token = this.getToken()

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    // 添加认证 Token
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    // 处理 401 未授权（Token 过期）
    if (response.status === 401) {
      // 尝试刷新 Token
      const refreshed = await this.refreshToken()
      if (refreshed) {
        // 重试原请求
        const newToken = this.getToken()
        if (newToken) {
          headers['Authorization'] = `Bearer ${newToken}`
          const retryResponse = await fetch(url, {
            ...options,
            headers,
          })
          if (retryResponse.ok) {
            return retryResponse.json()
          }
        }
      }

      // 刷新失败，清除认证信息
      this.clearAuth()
      throw new Error('登录已过期，请重新登录')
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '请求失败' }))
      throw new Error(error.detail || 'Unknown error')
    }

    return response.json()
  }

  private async refreshToken(): Promise<boolean> {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) return false

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (response.ok) {
        const data = await response.json()
        localStorage.setItem('access_token', data.access_token)
        return true
      }
    } catch (error) {
      console.error('刷新 Token 失败:', error)
    }

    return false
  }

  private clearAuth() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    localStorage.removeItem('current_project')
    // 触发登出事件
    window.dispatchEvent(new Event('auth:logout'))
  }

  get<T = unknown>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  post<T = unknown>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  put<T = unknown>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  delete(endpoint: string): Promise<{ status: string }> {
    return this.request<{ status: string }>(endpoint, { method: 'DELETE' })
  }
}

export const api = new ApiClient()
export { API_BASE }
