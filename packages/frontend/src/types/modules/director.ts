export interface PersonaConfig {
  id: Persona
  name: string
  emoji: string
  description: string
}

export type Persona = 'hajimi' | 'wukong' | 'pro'

export interface StoryboardFrame {
  frame_number: number
  image_url: string
  image_path: string
  narration: string
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
  storyboard_frames?: StoryboardFrame[]
  cover_image?: string
}

export interface ViewpointInfo {
  title: string
  description: string
  source_id: string
}

export interface DirectorRequest {
  source_a_id: string
  time_a: number
  source_b_id: string
  time_b: number
  topic: string
  viewpoint_a_title: string
  viewpoint_a_description: string
  viewpoint_b_title: string
  viewpoint_b_description: string
  persona: Persona
}

export interface DirectorStatusResponse {
  task_id: string
  status: string
  progress: number
  message: string
  video_url?: string
  script?: string
  persona?: Persona
  persona_name?: string
  segment_count?: number
  error?: string
}
