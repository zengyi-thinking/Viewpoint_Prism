import { api } from '../client'
import type {
  SearchRequest,
  // Extended types
  ExtendedSearchRequest,
  ExtendedSearchResponse,
  FetchContentRequest,
  FetchContentResponse,
  SearchResultItem,
} from '@/types/modules/ingest'

// Legacy types for backward compatibility
interface TaskStatusResponse {
  task_id: string
  status: string
  progress: number
  message: string
  source_ids?: string[]
  error?: string
}

interface PlatformInfo {
  id: string
  name: string
  supported: boolean
  description: string
}

export const IngestAPI = {
  // Legacy API
  search: async (request: SearchRequest): Promise<{ status: string; message: string; task_id: string }> => {
    return api.post('/ingest/search', request)
  },

  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    return api.get<TaskStatusResponse>(`/ingest/tasks/${taskId}`)
  },

  getPlatforms: async (): Promise<{ platforms: PlatformInfo[] }> => {
    return api.get('/ingest/platforms')
  },

  // Extended API
  extendedSearch: async (request: ExtendedSearchRequest): Promise<ExtendedSearchResponse> => {
    return api.post<ExtendedSearchResponse>('/ingest/search/extended', request)
  },

  fetchContent: async (request: FetchContentRequest): Promise<FetchContentResponse> => {
    return api.post<FetchContentResponse>('/ingest/fetch', request)
  },

  getExtendedPlatforms: async (): Promise<{ platforms: any[] }> => {
    return api.get('/ingest/platforms/extended')
  },
}

// Re-export types for convenience
export type {
  SearchRequest,
  ExtendedSearchRequest,
  ExtendedSearchResponse,
  FetchContentRequest,
  FetchContentResponse,
  SearchResultItem,
}

export type { TaskStatusResponse, PlatformInfo }
