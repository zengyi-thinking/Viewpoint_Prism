export interface Viewpoint {
  source_id: string
  source_name: string
  title: string
  description: string
  timestamp: number | null
  color: 'red' | 'blue'
}

export interface Conflict {
  id: string
  topic: string
  severity: 'critical' | 'warning' | 'info'
  viewpoint_a: Viewpoint
  viewpoint_b: Viewpoint
  verdict: string
}

export interface GraphNode {
  id: string
  name: string
  category: 'boss' | 'item' | 'location' | 'character'
  timestamp?: number
  source_id?: string
}

export interface GraphLink {
  source: string
  target: string
  relation?: string
}

export interface KnowledgeGraph {
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface TimelineEvent {
  id: string
  time: string
  timestamp: number
  title: string
  description: string
  source_id: string
  is_key_moment: boolean
  event_type: 'STORY' | 'COMBAT' | 'EXPLORE'
}

export interface AnalysisResponse {
  conflicts: Conflict[]
  graph: KnowledgeGraph
  timeline: TimelineEvent[]
}

export interface SearchResult {
  text: string
  source_id: string
  type: string
  start: number
  end: number
  video_title: string
  distance: number
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  total: number
}

export interface GenerateRequest {
  source_ids: string[]
  use_cache?: boolean
}
