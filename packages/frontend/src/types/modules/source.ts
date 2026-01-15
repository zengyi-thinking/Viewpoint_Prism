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

export interface SourceListResponse {
  sources: VideoSource[]
  total: number
}

export interface UploadState {
  isUploading: boolean
  progress: number
  error: string | null
}
