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

export interface ChatRequest {
  session_id: string
  message: string
  source_ids?: string[]
}

export interface ChatResponse {
  role: string
  content: string
  references: ChatReference[]
}

export interface ContextBridgeRequest {
  source_id: string
  timestamp: number
  previous_timestamp?: number
}

export interface ContextBridgeResponse {
  context: string
  next_segment?: {
    start: number
    end: number
    description: string
  }
}
