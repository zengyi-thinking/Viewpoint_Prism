import { api } from '../client'
import type { AnalysisResponse, SearchResponse, GenerateRequest } from '@/types/modules/analysis'

export const AnalysisAPI = {
  generate: async (request: GenerateRequest): Promise<AnalysisResponse> => {
    return api.post('/analysis/generate', request)
  },

  search: async (
    query: string,
    sourceIds?: string[],
    limit = 10
  ): Promise<SearchResponse> => {
    const params = new URLSearchParams({ q: query })
    params.set('limit', limit.toString())
    if (sourceIds && sourceIds.length > 0) {
      params.set('source_ids', sourceIds.join(','))
    }
    return api.get<SearchResponse>(`/analysis/search?${params.toString()}`)
  },
}
