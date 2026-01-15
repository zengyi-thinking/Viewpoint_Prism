export interface WebtoonVideoSegment {
  source_id: string
  start: number
  end: number
}

export interface WebtoonPanel {
  panel_number: number
  time: number
  time_formatted: string
  caption: string
  characters: string
  frame_description?: string
  manga_image_url: string
  original_frame_url: string
  video_segment: WebtoonVideoSegment
}

export interface BlogSection {
  type: 'text' | 'panel'
  content?: string
  panel_index?: number
}

export interface WebtoonTask {
  task_id: string
  status: 'pending' | 'extracting' | 'analyzing' | 'scripting' | 'drawing' | 'writing' | 'completed' | 'error'
  progress: number
  message: string
  panels: WebtoonPanel[]
  total_panels: number
  current_panel: number
  blog_title?: string
  blog_sections?: BlogSection[]
  error?: string
  audio_status?: 'pending' | 'generating' | 'completed' | 'error'
  audio_progress?: number
  audio_message?: string
  audio_url?: string
}

export interface CreateWebtoonRequest {
  source_id: string
  max_panels?: number
}

export interface WebtoonTaskResponse {
  task_id: string
  status: string
  progress: number
  message: string
  panels?: WebtoonPanel[]
  total_panels?: number
  current_panel?: number
  blog_title?: string
  blog_sections?: BlogSection[]
  error?: string
}
