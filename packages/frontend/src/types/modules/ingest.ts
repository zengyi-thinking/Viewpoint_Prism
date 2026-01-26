export interface NetworkSearchTask {
  task_id: string
  status: 'pending' | 'searching' | 'downloading' | 'ingesting' | 'completed' | 'error'
  progress: number
  message: string
  source_ids?: string[]
  error?: string
  results?: any[]  // 搜索结果（向后兼容）
}

export interface SearchRequest {
  platform: string
  keyword: string
  limit?: number
}

// ==================== Extended search types ====================

export type Platform = 'bilibili' | 'youtube' | 'arxiv'
export type ContentType = 'video' | 'article' | 'paper' | 'all'

export interface ExtendedSearchRequest {
  query: string
  platforms: Platform[]
  max_results?: number
  content_type?: ContentType
}

export interface SearchResultItem {
  id: string
  title: string
  description?: string
  url: string
  thumbnail?: string
  duration?: number  // seconds
  author?: string
  published_at?: string  // ISO format
  view_count?: number
  platform: string
  content_type: 'video' | 'article' | 'paper'
  metadata?: Record<string, unknown>
}

export interface ExtendedSearchResponse {
  query: string
  results: SearchResultItem[]
  total_count: number
  platforms_searched: string[]
  content_type_filter?: string
}

export interface FetchContentRequest {
  content_id: string
  platform: Platform
  auto_analyze?: boolean
}

export interface FetchContentResponse {
  task_id: string
  status: string
  message: string
}

export interface ExtendedPlatformInfo {
  id: string
  name: string
  content_type: 'video' | 'paper' | 'article'
  supported: boolean
  description: string
}
