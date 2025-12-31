// === Core Type Definitions ===

// Video source status
export type SourceStatus = 'imported' | 'uploaded' | 'processing' | 'analyzing' | 'done' | 'error'

// Video source
export interface VideoSource {
  id: string
  title: string
  file_path: string
  url: string
  file_type: 'video' | 'document'
  platform: string
  duration: number | null
  status: SourceStatus
  created_at: string
}

// Viewpoint
export interface Viewpoint {
  source_id: string
  source_name: string
  title: string
  description: string
  timestamp: number | null
  color: 'red' | 'blue'
}

// Conflict
export interface Conflict {
  id: string
  topic: string
  severity: 'critical' | 'warning' | 'info'
  viewpoint_a: Viewpoint
  viewpoint_b: Viewpoint
  verdict: string
}

// Graph node
export interface GraphNode {
  id: string
  name: string
  category: 'boss' | 'item' | 'location' | 'character'
  timestamp: number | null
  source_id: string | null
}

// Graph link
export interface GraphLink {
  source: string
  target: string
  relation: string | null
}

// Knowledge graph
export interface KnowledgeGraph {
  nodes: GraphNode[]
  links: GraphLink[]
}

// Timeline event
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

// Chat reference
export interface ChatReference {
  source_id: string
  timestamp: number
  text: string
}

// Chat message
export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  references: ChatReference[]
  created_at: string
}

// Creative task status
export type TaskStatus = 'pending' | 'processing' | 'generating_script' |
  'generating_voiceover' | 'composing_video' | 'searching' | 'downloading' |
  'ingesting' | 'completed' | 'error'

// Debate video task
export interface DebateTask {
  status: TaskStatus
  progress: number
  message: string
  video_url?: string
  script?: string
  error?: string
}

// AI director task
export type Persona = 'hajimi' | 'wukong' | 'pro'

export interface DirectorTask {
  status: TaskStatus
  progress: number
  message: string
  video_url?: string
  script?: string
  persona?: Persona
  persona_name?: string
  segment_count?: number
  error?: string
}

// Supercut task
export interface SupercutTask {
  status: TaskStatus
  progress: number
  message: string
  video_url?: string
  clip_count?: number
  error?: string
}

// Digest task
export interface DigestTask {
  status: TaskStatus
  progress: number
  message: string
  video_url?: string
  segment_count?: number
  total_duration?: number
  error?: string
}

// Network search task
export interface NetworkSearchTask {
  status: TaskStatus
  progress: number
  message: string
  files?: Array<{
    id: string
    title: string
    file_path: string
  }>
  error?: string
}

// Analysis tab
export type AnalysisTab = 'studio' | 'conflicts' | 'graph' | 'timeline' | 'report'

// Active player
export type ActivePlayer = 'main' | 'debate' | 'director' | 'supercut' | 'digest'

// Panel position
export type PanelPosition = 'left' | 'bottom' | 'right'

// Language
export type Language = 'zh' | 'en'

// Entity card state
export interface EntityCardState {
  isOpen: boolean
  entity: GraphNode | null
  position: { x: number; y: number }
  stats: { video_count: number; occurrence_count: number } | null
  task: SupercutTask | null
}
