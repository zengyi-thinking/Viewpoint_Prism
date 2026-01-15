export interface NetworkSearchTask {
  task_id: string
  status: 'pending' | 'searching' | 'downloading' | 'ingesting' | 'completed' | 'error'
  progress: number
  message: string
  source_ids?: string[]
  error?: string
}

export interface SearchRequest {
  platform: string
  keyword: string
  limit?: number
}
