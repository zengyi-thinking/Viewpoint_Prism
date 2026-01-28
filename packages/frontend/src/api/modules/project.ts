/**
 * 工程 API
 * 提供工程管理相关接口
 */

import { api } from '../client'
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectDetail,
  ProjectListResponse,
  ProjectMember,
  SwitchProjectResponse,
} from '@/types/modules/auth'

/**
 * 工程 API 类
 */
export class ProjectAPI {
  /**
   * 获取用户的所有工程
   */
  async getProjects(): Promise<ProjectListResponse> {
    return api.get<ProjectListResponse>('/projects')
  }

  /**
   * 创建新工程
   */
  async createProject(data: ProjectCreate): Promise<Project> {
    return api.post<Project>('/projects', data)
  }

  /**
   * 获取工程详情
   */
  async getProject(projectId: string): Promise<ProjectDetail> {
    return api.get<ProjectDetail>(`/projects/${projectId}`)
  }

  /**
   * 更新工程信息
   */
  async updateProject(projectId: string, data: ProjectUpdate): Promise<Project> {
    return api.put<Project>(`/projects/${projectId}`, data)
  }

  /**
   * 删除工程
   */
  async deleteProject(projectId: string): Promise<{ status: string }> {
    return api.delete(`/projects/${projectId}`)
  }

  /**
   * 切换当前工程
   */
  async switchProject(projectId: string): Promise<SwitchProjectResponse> {
    return api.post<SwitchProjectResponse>(`/projects/${projectId}/switch`, {})
  }

  /**
   * 获取工程成员列表
   */
  async getMembers(projectId: string): Promise<ProjectMember[]> {
    return api.get<ProjectMember[]>(`/projects/${projectId}/members`)
  }

  /**
   * 获取最近访问的工程
   */
  async getRecentProjects(limit: number = 10): Promise<ProjectListResponse> {
    return api.get<ProjectListResponse>(`/projects/recent/list?limit=${limit}`)
  }
}

export const projectAPI = new ProjectAPI()
