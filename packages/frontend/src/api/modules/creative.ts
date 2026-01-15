import { api } from '../client'
import type { SupercutTask, DigestTask, EntityStats, OnePagerData } from '@/types/modules/creative'

export interface CreateSupercutRequest {
  entity_name: string
  top_k?: number
}

export interface CreateDigestRequest {
  source_id: string
  include_types?: string[]
}

export interface CreateOnePagerRequest {
  source_ids: string[]
  use_cache?: boolean
}

export const CreativeAPI = {
  supercut: {
    create: async (request: CreateSupercutRequest): Promise<{ task_id: string; status: string; message: string }> => {
      return api.post('/create/supercut', request)
    },
    getStatus: async (taskId: string): Promise<SupercutTask> => {
      return api.get(`/create/tasks/${taskId}`)
    },
  },

  digest: {
    create: async (request: CreateDigestRequest): Promise<{ task_id: string; status: string; message: string }> => {
      return api.post('/create/digest', request)
    },
    getStatus: async (taskId: string): Promise<DigestTask> => {
      return api.get(`/create/tasks/${taskId}`)
    },
  },

  entity: {
    getStats: async (entityName: string): Promise<EntityStats> => {
      return api.get(`/create/entity/${encodeURIComponent(entityName)}/stats`)
    },
  },

  onePager: {
    create: async (request: CreateOnePagerRequest): Promise<OnePagerData> => {
      return api.post('/analysis/one-pager', request)
    },
  },
}
