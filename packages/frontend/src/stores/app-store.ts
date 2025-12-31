import { create } from 'zustand'
import type {
  VideoSource,
  Conflict,
  KnowledgeGraph,
  TimelineEvent,
  ChatMessage,
  DebateTask,
  DirectorTask,
  SupercutTask,
  DigestTask,
  NetworkSearchTask,
  AnalysisTab,
  ActivePlayer,
  PanelPosition,
  Language,
  Persona,
  GraphNode,
  EntityCardState
} from '@/types'

const API_BASE = 'http://localhost:8000'

interface AppStore {
  // === Data State ===
  sources: VideoSource[]
  selectedSourceIds: string[]
  currentSourceId: string | null
  conflicts: Conflict[]
  graph: KnowledgeGraph
  timeline: TimelineEvent[]
  messages: ChatMessage[]

  // === UI State ===
  currentTime: number
  isPlaying: boolean
  activePlayer: ActivePlayer
  activeTab: AnalysisTab
  language: Language
  panelVisibility: Record<PanelPosition, boolean>
  entityCard: EntityCardState

  // === Creative Tasks ===
  debateTasks: Record<string, DebateTask>
  directorTasks: Record<string, DirectorTask>
  supercutTasks: Record<string, SupercutTask>
  digestTask: DigestTask | null
  networkSearchTask: NetworkSearchTask | null
  selectedPersona: Persona

  // === Upload State ===
  uploadState: {
    isUploading: boolean
    progress: number
    message: string
  }

  // === Analysis State ===
  isAnalyzing: boolean

  // === Chat State ===
  isChatting: boolean
  currentSessionId: string

  // === Actions ===
  setLanguage: (lang: Language) => void
  togglePanel: (panel: PanelPosition) => void
  setCurrentSource: (id: string) => void
  toggleSourceSelection: (id: string) => void
  seekTo: (sourceId: string, time: number) => void
  setActivePlayer: (player: ActivePlayer) => void
  setActiveTab: (tab: AnalysisTab) => void
  openEntityCard: (entity: GraphNode, position: { x: number; y: number }) => void
  closeEntityCard: () => void
  setCurrentTime: (time: number) => void
  setIsPlaying: (playing: boolean) => void

  // === API Actions ===
  fetchSources: () => Promise<void>
  uploadVideo: (file: File) => Promise<void>
  deleteSource: (id: string) => Promise<void>
  reprocessSource: (id: string) => Promise<void>
  analyzeSource: (id: string) => Promise<void>
  fetchAnalysis: (sourceIds: string[]) => Promise<void>
  sendChatMessage: (message: string) => Promise<void>
  startNetworkSearch: (platform: string, keyword: string, limit: number) => Promise<void>

  // === Creative Actions ===
  startDebateGeneration: (conflictId: string, conflict: Conflict) => Promise<string | null>
  pollDebateTask: (taskId: string) => Promise<DebateTask | null>
  setDebateTask: (conflictId: string, task: DebateTask) => void

  startDirectorGeneration: (conflictId: string, conflict: Conflict, persona: Persona) => Promise<string | null>
  pollDirectorTask: (taskId: string) => Promise<DirectorTask | null>
  setDirectorTask: (conflictId: string, task: DirectorTask) => void
  setSelectedPersona: (persona: Persona) => void

  startSupercutGeneration: (entityName: string) => Promise<string | null>
  pollSupercutTask: (taskId: string) => Promise<SupercutTask | null>
  setSupercutTask: (entityName: string, task: SupercutTask) => void
  fetchEntityStats: (entityName: string) => Promise<void>

  startDigestGeneration: (sourceId: string) => Promise<string | null>
  pollDigestTask: (taskId: string) => Promise<DigestTask | null>
  setDigestTask: (task: DigestTask) => void
  digestIncludeTypes: string[]
  setDigestIncludeTypes: (types: string[]) => void

  setNetworkSearchTask: (task: NetworkSearchTask | null) => void
}

export const useAppStore = create<AppStore>((set, get) => ({
  // === Initial State ===
  sources: [],
  selectedSourceIds: [],
  currentSourceId: null,
  conflicts: [],
  graph: { nodes: [], links: [] },
  timeline: [],
  messages: [],

  currentTime: 0,
  isPlaying: false,
  activePlayer: 'main',
  activeTab: 'studio',
  language: 'zh',
  panelVisibility: { left: true, bottom: true, right: true },
  entityCard: {
    isOpen: false,
    entity: null,
    position: { x: 0, y: 0 },
    stats: null,
    task: null
  },

  debateTasks: {},
  directorTasks: {},
  supercutTasks: {},
  digestTask: null,
  networkSearchTask: null,
  selectedPersona: 'pro',

  uploadState: {
    isUploading: false,
    progress: 0,
    message: ''
  },

  isAnalyzing: false,
  isChatting: false,
  currentSessionId: 'session_' + Date.now(),
  digestIncludeTypes: ['STORY', 'COMBAT'],

  // === UI Actions ===
  setLanguage: (lang) => set({ language: lang }),

  togglePanel: (panel) => set((state) => ({
    panelVisibility: {
      ...state.panelVisibility,
      [panel]: !state.panelVisibility[panel]
    }
  })),

  setCurrentSource: (id) => set({ currentSourceId: id }),

  toggleSourceSelection: (id) => set((state) => {
    const isSelected = state.selectedSourceIds.includes(id)
    return {
      selectedSourceIds: isSelected
        ? state.selectedSourceIds.filter(sid => sid !== id)
        : [...state.selectedSourceIds, id]
    }
  }),

  seekTo: (sourceId, time) => {
    set({ currentSourceId: sourceId, currentTime: time })
    const videoElement = document.querySelector(`video[data-source-id="${sourceId}"]`) as HTMLVideoElement
    if (videoElement) {
      videoElement.currentTime = time
    }
  },

  setActivePlayer: (player) => set({ activePlayer: player, isPlaying: false }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setCurrentTime: (time) => set({ currentTime: time }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),

  openEntityCard: (entity, position) => set({
    entityCard: {
      isOpen: true,
      entity,
      position,
      stats: null,
      task: null
    }
  }),

  closeEntityCard: () => set((state) => ({
    entityCard: { ...state.entityCard, isOpen: false }
  })),

  setSelectedPersona: (persona) => set({ selectedPersona: persona }),
  setDigestIncludeTypes: (types) => set({ digestIncludeTypes: types }),

  // === API Actions ===
  fetchSources: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sources/`)
      const data = await res.json()
      set({ sources: data.sources })
    } catch (error) {
      console.error('Failed to fetch sources:', error)
    }
  },

  uploadVideo: async (file) => {
    set({ uploadState: { isUploading: true, progress: 0, message: '上传中...' } })

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API_BASE}/api/sources/upload`, {
        method: 'POST',
        body: formData
      })

      if (!res.ok) throw new Error('Upload failed')

      await get().fetchSources()
      set({ uploadState: { isUploading: false, progress: 100, message: '上传成功' } })
    } catch (error) {
      set({ uploadState: { isUploading: false, progress: 0, message: '上传失败' } })
    }
  },

  deleteSource: async (id) => {
    try {
      await fetch(`${API_BASE}/api/sources/${id}`, { method: 'DELETE' })
      await get().fetchSources()
    } catch (error) {
      console.error('Failed to delete source:', error)
    }
  },

  reprocessSource: async (id) => {
    try {
      await fetch(`${API_BASE}/api/sources/${id}/reprocess`, { method: 'POST' })
      await get().fetchSources()
    } catch (error) {
      console.error('Failed to reprocess source:', error)
    }
  },

  analyzeSource: async (id) => {
    try {
      await fetch(`${API_BASE}/api/sources/${id}/analyze`, { method: 'POST' })
      await get().fetchSources()
    } catch (error) {
      console.error('Failed to analyze source:', error)
    }
  },

  fetchAnalysis: async (sourceIds) => {
    set({ isAnalyzing: true })

    try {
      const res = await fetch(`${API_BASE}/api/analysis/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_ids: sourceIds })
      })

      if (!res.ok) throw new Error('Analysis failed')

      const data = await res.json()
      set({
        conflicts: data.conflicts,
        graph: data.graph,
        timeline: data.timeline,
        isAnalyzing: false
      })
    } catch (error) {
      console.error('Failed to fetch analysis:', error)
      set({ isAnalyzing: false })
    }
  },

  sendChatMessage: async (message) => {
    set({ isChatting: true })

    try {
      const state = get()
      const res = await fetch(`${API_BASE}/api/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: state.currentSessionId,
          message,
          source_ids: state.selectedSourceIds
        })
      })

      if (!res.ok) throw new Error('Chat failed')

      const data = await res.json()
      set((state) => ({
        messages: [
          ...state.messages,
          { id: Date.now().toString(), role: 'user' as const, content: message, references: [], session_id: state.currentSessionId, created_at: new Date().toISOString() },
          { id: (Date.now() + 1).toString(), role: 'assistant' as const, content: data.content, references: data.references, session_id: state.currentSessionId, created_at: new Date().toISOString() }
        ],
        isChatting: false
      }))
    } catch (error) {
      console.error('Failed to send chat message:', error)
      set({ isChatting: false })
    }
  },

  startNetworkSearch: async (platform, keyword, limit) => {
    try {
      const res = await fetch(`${API_BASE}/api/ingest/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform, keyword, limit })
      })

      if (!res.ok) throw new Error('Search failed')

      const data = await res.json()
      set({ networkSearchTask: { status: 'pending', progress: 0, message: '搜索已启动...' } })

      const pollInterval = setInterval(async () => {
        const state = get()
        if (!state.networkSearchTask) return

        const taskRes = await fetch(`${API_BASE}/api/ingest/tasks/${data.task_id}`)
        const taskData = await taskRes.json()

        if (taskData.status === 'completed' || taskData.status === 'error') {
          clearInterval(pollInterval)
          await get().fetchSources()
        }

        set({ networkSearchTask: taskData })
      }, 2000)

    } catch (error) {
      console.error('Failed to start network search:', error)
    }
  },

  // === Creative Actions ===
  startDebateGeneration: async (conflictId, conflict) => {
    try {
      const res = await fetch(`${API_BASE}/api/create/debate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conflict_id: conflictId,
          viewpoint_a: conflict.viewpoint_a,
          viewpoint_b: conflict.viewpoint_b
        })
      })

      if (!res.ok) throw new Error('Failed to start debate')

      const data = await res.json()
      return data.task_id
    } catch (error) {
      console.error('Failed to start debate generation:', error)
      return null
    }
  },

  pollDebateTask: async (taskId) => {
    try {
      const res = await fetch(`${API_BASE}/api/create/tasks/${taskId}`)
      if (!res.ok) return null
      return await res.json()
    } catch (error) {
      console.error('Failed to poll debate task:', error)
      return null
    }
  },

  setDebateTask: (conflictId, task) => set((state) => ({
    debateTasks: { ...state.debateTasks, [conflictId]: task }
  })),

  startDirectorGeneration: async (conflictId, conflict, persona) => {
    try {
      const res = await fetch(`${API_BASE}/api/create/director_cut`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conflict_id: conflictId, conflict, persona })
      })

      if (!res.ok) throw new Error('Failed to start director')

      const data = await res.json()
      return data.task_id
    } catch (error) {
      console.error('Failed to start director generation:', error)
      return null
    }
  },

  pollDirectorTask: async (taskId) => {
    try {
      const res = await fetch(`${API_BASE}/api/create/tasks/${taskId}`)
      if (!res.ok) return null
      return await res.json()
    } catch (error) {
      console.error('Failed to poll director task:', error)
      return null
    }
  },

  setDirectorTask: (conflictId, task) => set((state) => ({
    directorTasks: { ...state.directorTasks, [conflictId]: task }
  })),

  startSupercutGeneration: async (entityName) => {
    try {
      const res = await fetch(`${API_BASE}/api/create/supercut`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_name: entityName })
      })

      if (!res.ok) throw new Error('Failed to start supercut')

      const data = await res.json()
      return data.task_id
    } catch (error) {
      console.error('Failed to start supercut generation:', error)
      return null
    }
  },

  pollSupercutTask: async (taskId) => {
    try {
      const res = await fetch(`${API_BASE}/api/create/tasks/${taskId}`)
      if (!res.ok) return null
      return await res.json()
    } catch (error) {
      console.error('Failed to poll supercut task:', error)
      return null
    }
  },

  setSupercutTask: (entityName, task) => set((state) => ({
    supercutTasks: { ...state.supercutTasks, [entityName]: task }
  })),

  fetchEntityStats: async (entityName) => {
    set((state) => ({
      entityCard: {
        ...state.entityCard,
        stats: { video_count: 3, occurrence_count: 15 }
      }
    }))
  },

  startDigestGeneration: async (sourceId) => {
    try {
      const state = get()
      const res = await fetch(`${API_BASE}/api/create/digest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_id: sourceId,
          include_types: state.digestIncludeTypes
        })
      })

      if (!res.ok) throw new Error('Failed to start digest')

      const data = await res.json()
      return data.task_id
    } catch (error) {
      console.error('Failed to start digest generation:', error)
      return null
    }
  },

  pollDigestTask: async (taskId) => {
    try {
      const res = await fetch(`${API_BASE}/api/create/tasks/${taskId}`)
      if (!res.ok) return null
      return await res.json()
    } catch (error) {
      console.error('Failed to poll digest task:', error)
      return null
    }
  },

  setDigestTask: (task) => set({ digestTask: task }),

  setNetworkSearchTask: (task) => set({ networkSearchTask: task })
}))
