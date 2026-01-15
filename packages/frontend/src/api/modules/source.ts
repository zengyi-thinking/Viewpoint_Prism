import { api, API_BASE } from '../client'
import type { VideoSource, SourceListResponse } from '@/types/modules/source'

export interface UploadState {
  isUploading: boolean
  progress: number
  error: string | null
}

export const SourceAPI = {
  list: async (limit = 100, offset = 0): Promise<SourceListResponse> => {
    return api.get<SourceListResponse>(`/sources/?limit=${limit}&offset=${offset}`)
  },

  get: async (id: string): Promise<VideoSource> => {
    return api.get<VideoSource>(`/sources/${id}`)
  },

  upload: async (file: File, onProgress?: (progress: number) => void): Promise<VideoSource> => {
    return new Promise((resolve, reject) => {
      const formData = new FormData()
      formData.append('file', file)

      const xhr = new XMLHttpRequest()
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress((e.loaded / e.total) * 100)
        }
      })
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText))
        } else {
          reject(new Error('Upload failed'))
        }
      })
      xhr.addEventListener('error', () => reject(new Error('Upload failed')))
      xhr.open('POST', `${API_BASE}/sources/upload`)
      xhr.send(formData)
    })
  },

  delete: async (id: string): Promise<{ status: string }> => {
    return api.delete(`/sources/${id}`)
  },

  reprocess: async (id: string): Promise<{ status: string }> => {
    return api.post(`/sources/${id}/reprocess`, {})
  },

  analyze: async (id: string): Promise<{ status: string }> => {
    return api.post(`/sources/${id}/analyze`, {})
  },

  recent: async (limit = 10): Promise<{ sources: VideoSource[] }> => {
    return api.get<{ sources: VideoSource[] }>(`/sources/recent/list?limit=${limit}`)
  },

  search: async (query: string): Promise<{ sources: VideoSource[] }> => {
    return api.get<{ sources: VideoSource[] }>(`/sources/search/?q=${encodeURIComponent(query)}`)
  },

  debug: async (): Promise<{ total_documents: number; unique_sources: string[] }> => {
    return api.get(`/sources/debug/chromadb`)
  },
}
