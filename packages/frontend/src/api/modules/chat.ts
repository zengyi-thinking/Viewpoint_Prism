import { api, API_BASE } from '../client'
import type { ChatRequest, ChatResponse, ContextBridgeRequest, ContextBridgeResponse } from '@/types/modules/chat'

export const ChatAPI = {
  chat: async (request: ChatRequest): Promise<ChatResponse> => {
    return api.post<ChatResponse>('/chat/', request)
  },

  chatStream: async (
    request: ChatRequest
  ): Promise<ReadableStream<Uint8Array>> => {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
    return response.body as ReadableStream<Uint8Array>
  },

  getHistory: async (sessionId: string): Promise<ChatResponse[]> => {
    return api.get<ChatResponse[]>(`/chat/history/${sessionId}`)
  },

  clearHistory: async (sessionId: string) => {
    return api.delete(`/chat/history/${sessionId}`)
  },

  contextBridge: async (request: ContextBridgeRequest): Promise<ContextBridgeResponse> => {
    return api.post<ContextBridgeResponse>('/chat/context-bridge', request)
  },
}
