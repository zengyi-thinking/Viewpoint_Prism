/**
 * 认证 API
 * 提供用户注册、登录、登出等认证相关接口
 */

import { api } from '../client'
import type {
  User,
  UserCreate,
  UserLogin,
  UserUpdate,
  ChangePassword,
  LoginResponse,
  TokenResponse,
} from '@/types/modules/auth'

/**
 * 认证 API 类
 */
export class AuthAPI {
  /**
   * 用户注册
   */
  async register(data: UserCreate): Promise<User> {
    return api.post<User>('/auth/register', data)
  }

  /**
   * 用户登录
   */
  async login(data: UserLogin): Promise<LoginResponse> {
    return api.post<LoginResponse>('/auth/login', data)
  }

  /**
   * 用户登出
   */
  async logout(): Promise<{ message: string }> {
    return api.post<{ message: string }>('/auth/logout', {})
  }

  /**
   * 登出所有设备
   */
  async logoutAll(): Promise<{ message: string }> {
    return api.post<{ message: string }>('/auth/logout-all', {})
  }

  /**
   * 获取当前用户信息
   */
  async getMe(): Promise<User> {
    return api.get<User>('/auth/me')
  }

  /**
   * 更新当前用户信息
   */
  async updateMe(data: UserUpdate): Promise<User> {
    return api.put<User>('/auth/me', data)
  }

  /**
   * 修改密码
   */
  async changePassword(data: ChangePassword): Promise<{ message: string }> {
    return api.post<{ message: string }>('/auth/change-password', data)
  }

  /**
   * 刷新访问令牌
   */
  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    return api.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken })
  }
}

export const authAPI = new AuthAPI()
