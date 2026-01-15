import { api } from '../client'
import type { DirectorRequest, DirectorStatusResponse, PersonaConfig } from '@/types/modules/director'

export const DirectorAPI = {
  createCut: async (request: DirectorRequest): Promise<{ task_id: string; status: string; message: string }> => {
    return api.post('/director/cut', request)
  },

  getTaskStatus: async (taskId: string): Promise<DirectorStatusResponse> => {
    return api.get<DirectorStatusResponse>(`/director/tasks/${taskId}`)
  },

  getPersonas: async (): Promise<{ personas: PersonaConfig[] }> => {
    return api.get('/director/personas')
  },
}
