import { api } from '../client'
import type { SearchRequest } from '@/types/modules/ingest'

export interface TaskStatusResponse {
  task_id: string
  status: string
  progress: number
  message: string
  source_ids?: string[]
  error?: string
}

export interface PlatformInfo {
  id: string
  name: string
  supported: boolean
  description: string
}

export const IngestAPI = {
  search: async (request: SearchRequest): Promise<{ status: string; message: string; task_id: string }> => {
    return api.post('/ingest/search', request)
  },

  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    return api.get<TaskStatusResponse>(`/ingest/tasks/${taskId}`)
  },

  getPlatforms: async (): Promise<{ platforms: PlatformInfo[] }> => {
    return api.get('/ingest/platforms')
  },
}
