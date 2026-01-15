import { api } from '../client'
import type {
  ConceptsResponse,
  NebulaStructureResponse,
  HighlightTaskResponse,
  CreateHighlightRequest,
} from '@/types/modules/nebula'

export const NebulaAPI = {
  getConcepts: async (topK = 50): Promise<ConceptsResponse> => {
    return api.get<ConceptsResponse>(`/nebula/concepts?top_k=${topK}`)
  },

  getStructure: async (sourceIds?: string[]): Promise<NebulaStructureResponse> => {
    const params = sourceIds ? `?source_ids=${sourceIds.join(',')}` : ''
    return api.get<NebulaStructureResponse>(`/nebula/structure${params}`)
  },

  createHighlight: async (request: CreateHighlightRequest): Promise<HighlightTaskResponse> => {
    return api.post<HighlightTaskResponse>('/nebula/highlight', request)
  },

  getHighlightStatus: async (taskId: string): Promise<HighlightTaskResponse> => {
    return api.get<HighlightTaskResponse>(`/nebula/highlight/${taskId}`)
  },
}
