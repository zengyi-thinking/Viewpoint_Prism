import { api } from '../client'
import type { DebateRequest, DebateStatusResponse } from '@/types/modules/creative'

export const DebateAPI = {
  generate: async (request: DebateRequest): Promise<{ task_id: string; status: string; message: string }> => {
    return api.post('/debate/generate', request)
  },

  getTaskStatus: async (taskId: string): Promise<DebateStatusResponse> => {
    return api.get<DebateStatusResponse>(`/debate/tasks/${taskId}`)
  },
}
