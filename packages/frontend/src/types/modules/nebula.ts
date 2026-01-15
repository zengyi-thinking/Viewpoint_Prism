export interface ConceptItem {
  name: string
  weight: number
  category?: string
}

export interface ConceptsResponse {
  concepts: ConceptItem[]
  total: number
}

export interface NebulaNode {
  id: string
  name: string
  category: string
  value: number
  source_ids: string[]
}

export interface NebulaLink {
  source: string
  target: string
  value: number
}

export interface NebulaStructureResponse {
  nodes: NebulaNode[]
  links: NebulaLink[]
}

export interface CreateHighlightRequest {
  concept: string
  top_k?: number
}

export interface HighlightTaskResponse {
  task_id: string
  status: string
  progress: number
  message: string
  video_url?: string
  concept?: string
  segment_count?: number
  error?: string
}
