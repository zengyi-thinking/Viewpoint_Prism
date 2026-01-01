// Video source types
export interface VideoSource {
  id: string
  title: string
  file_path: string
  url: string
  file_type: 'video' | 'pdf' | 'audio'
  platform: 'tiktok' | 'bilibili' | 'youtube' | 'local'
  duration: number | null
  thumbnail: string | null
  status: 'imported' | 'uploaded' | 'processing' | 'analyzing' | 'done' | 'error'
  created_at: string
}

// Conflict/Viewpoint types
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

// Knowledge graph types
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

// Timeline types
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

// Chat types
export interface ChatReference {
  source_id: string
  timestamp: number
  text: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'ai'
  content: string
  timestamp: Date
  references?: ChatReference[]
}

// Layout types
export type PanelPosition = 'left' | 'bottom' | 'right'
export type AnalysisTab = 'conflicts' | 'graph' | 'timeline'
export type Language = 'zh' | 'en'
export type ActivePlayer = 'main' | 'debate' | 'supercut' | 'digest' | 'director' | null

// API Response types
export interface SourceListResponse {
  sources: VideoSource[]
  total: number
}

export interface AnalysisResponse {
  conflicts: Conflict[]
  graph: KnowledgeGraph
  timeline: TimelineEvent[]
}

// Upload state
export interface UploadState {
  isUploading: boolean
  progress: number
  error: string | null
}

// Debate video generation task
export interface DebateTask {
  task_id: string
  status: 'pending' | 'generating_script' | 'generating_voiceover' | 'composing_video' | 'completed' | 'error'
  progress: number
  message: string
  video_url?: string
  script?: string
  error?: string
}

// Phase 7: Entity Supercut types
export interface SupercutClip {
  source_id: string
  video_title: string
  timestamp: string
  score: number
}

export interface SupercutTask {
  task_id: string
  status: 'pending' | 'searching' | 'composing' | 'completed' | 'error'
  progress: number
  message: string
  video_url?: string
  entity_name?: string
  clip_count?: number
  clips?: SupercutClip[]
  error?: string
}

export interface EntityStats {
  entity_name: string
  video_count: number
  occurrence_count: number
}

// Entity Card state for Graph interaction
export interface EntityCardState {
  isOpen: boolean
  entity: GraphNode | null
  stats: EntityStats | null
  position: { x: number; y: number }
  task?: SupercutTask
}

// Phase 8: Digest types
export interface DigestTask {
  task_id: string
  status: 'pending' | 'filtering' | 'composing' | 'completed' | 'error'
  progress: number
  message: string
  video_url?: string
  source_id?: string
  segment_count?: number
  include_types?: string[]
  total_duration?: number
  error?: string
}

// Phase 10: Director Cut types
export type Persona = 'hajimi' | 'wukong' | 'pro'

export interface PersonaConfig {
  id: Persona
  name: string
  emoji: string
  description: string
}

// Phase 11: Storyboard frame types
export interface StoryboardFrame {
  frame_number: number
  image_url: string
  image_path: string
  narration: string
  prompt_used?: string
}

export interface MangaPanel {
  image_url: string
  image_path: string
  scene_description: string
  mood: string
  prompt_used?: string
}

export interface DirectorTask {
  task_id: string
  status: 'pending' | 'generating_script' | 'generating_voiceover' | 'composing_video' | 'completed' | 'error'
  progress: number
  message: string
  video_url?: string
  script?: string
  persona?: Persona
  persona_name?: string
  segment_count?: number
  error?: string
  // Phase 11: Visual content
  storyboard_frames?: StoryboardFrame[]
  cover_image?: string
}

// Phase 11: Network Search types
export interface NetworkSearchTask {
  task_id: string
  status: 'pending' | 'searching' | 'downloading' | 'ingesting' | 'completed' | 'error'
  progress: number
  message: string
  source_ids?: string[]
  error?: string
}

export interface NetworkSearchRequest {
  platform: string
  keyword: string
  limit?: number
}

// App state types
export interface AppState {
  // Sources
  sources: VideoSource[]
  selectedSourceIds: string[]
  currentSourceId: string | null

  // Playback
  currentTime: number
  isPlaying: boolean

  // Analysis
  conflicts: Conflict[]
  graph: KnowledgeGraph
  timeline: TimelineEvent[]

  // Chat
  messages: ChatMessage[]
  isLoading: boolean

  // Upload
  uploadState: UploadState

  // UI
  activeTab: AnalysisTab
  language: Language
  panelVisibility: Record<PanelPosition, boolean>
}
