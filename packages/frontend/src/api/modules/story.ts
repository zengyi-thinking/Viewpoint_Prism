import { api } from '../client'
import type { CreateWebtoonRequest, WebtoonTaskResponse } from '@/types/modules/story'

export const StoryAPI = {
  generate: async (request: CreateWebtoonRequest): Promise<WebtoonTaskResponse> => {
    return api.post('/story/generate', request)
  },

  getTaskStatus: async (taskId: string): Promise<WebtoonTaskResponse> => {
    return api.get<WebtoonTaskResponse>(`/story/task/${taskId}`)
  },

  getPanels: async (taskId: string, since = 0): Promise<{
    task_id: string
    total_panels: number
    since: number
    panels: unknown[]
    has_more: boolean
  }> => {
    return api.get(`/story/panels/${taskId}?since=${since}`)
  },
}
