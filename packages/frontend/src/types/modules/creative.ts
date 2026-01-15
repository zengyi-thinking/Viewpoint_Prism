export interface DebateTask {
  task_id: string
  status: 'pending' | 'generating_script' | 'generating_voiceover' | 'composing_video' | 'completed' | 'error'
  progress: number
  message: string
  video_url?: string
  script?: string
  error?: string
}

export interface ViewpointInfo {
  title: string
  description: string
  source_id: string
}

export interface DebateRequest {
  source_a_id: string
  time_a: number
  source_b_id: string
  time_b: number
  topic: string
  viewpoint_a_title: string
  viewpoint_a_description: string
  viewpoint_b_title: string
  viewpoint_b_description: string
}

export interface DebateStatusResponse {
  task_id: string
  status: string
  progress: number
  message: string
  video_url?: string
  script?: string
  error?: string
}

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

export interface EvidenceItem {
  url: string
  caption: string
  related_insight_index: number | null
}

export interface OnePagerData {
  headline: string
  tldr: string
  insights: string[]
  conceptual_image: string | null
  evidence_items: EvidenceItem[]
  evidence_images: string[]
  generated_at: string
  source_ids: string[]
  video_titles: string[]
}

export interface EntityCardState {
  isOpen: boolean
  entity: {
    id: string
    name: string
    category: 'boss' | 'item' | 'location' | 'character'
    timestamp?: number
    source_id?: string
  } | null
  stats: EntityStats | null
  position: { x: number; y: number }
  task?: SupercutTask
}
