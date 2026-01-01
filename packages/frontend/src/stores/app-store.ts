import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type {
  VideoSource,
  Conflict,
  KnowledgeGraph,
  TimelineEvent,
  ChatMessage,
  AnalysisTab,
  Language,
  PanelPosition,
  UploadState,
  SourceListResponse,
  AnalysisResponse,
  DebateTask,
  SupercutTask,
  EntityStats,
  EntityCardState,
  GraphNode,
  DigestTask,
  ActivePlayer,
  DirectorTask,
  Persona,
  NetworkSearchTask,
  OnePagerData,
} from '@/types'

// API base URL
const API_BASE = 'http://localhost:8000/api'

// Chat API types
interface ChatAPIResponse {
  role: string
  content: string
  references: Array<{
    source_id: string
    timestamp: number
    text: string
  }>
}

// Store state interface
interface AppStore {
  // === Sources State ===
  sources: VideoSource[]
  selectedSourceIds: string[]
  currentSourceId: string | null

  // Source actions
  addSource: (source: VideoSource) => void
  removeSource: (id: string) => void
  toggleSourceSelection: (id: string) => void
  setCurrentSource: (id: string | null) => void
  setSources: (sources: VideoSource[]) => void

  // API actions
  fetchSources: () => Promise<void>
  uploadVideo: (file: File) => Promise<VideoSource | null>
  deleteSource: (id: string) => Promise<void>
  reprocessSource: (id: string) => Promise<void>
  analyzeSource: (id: string) => Promise<void>  // Phase 12: Manual trigger for analysis
  fetchAnalysis: (sourceIds?: string[]) => Promise<void>
  sendChatMessage: (message: string) => Promise<void>

  // === Upload State ===
  uploadState: UploadState
  setUploadState: (state: Partial<UploadState>) => void

  // === Playback State ===
  currentTime: number
  isPlaying: boolean
  activePlayer: ActivePlayer  // Which player is currently active (for mutual exclusion)

  // Playback actions
  setCurrentTime: (time: number) => void
  seekTo: (sourceId: string, time: number) => void
  setIsPlaying: (playing: boolean) => void
  setActivePlayer: (player: ActivePlayer) => void  // Set active player, pause others

  // === Analysis State ===
  conflicts: Conflict[]
  graph: KnowledgeGraph
  timeline: TimelineEvent[]
  isAnalyzing: boolean

  // Analysis actions
  setConflicts: (conflicts: Conflict[]) => void
  setGraph: (graph: KnowledgeGraph) => void
  setTimeline: (timeline: TimelineEvent[]) => void

  // === Chat State ===
  messages: ChatMessage[]
  isLoading: boolean
  sessionId: string

  // Chat actions
  addMessage: (message: ChatMessage) => void
  clearMessages: () => void
  setIsLoading: (loading: boolean) => void

  // === UI State ===
  activeTab: AnalysisTab
  language: Language
  panelVisibility: Record<PanelPosition, boolean>

  // UI actions
  setActiveTab: (tab: AnalysisTab) => void
  setLanguage: (lang: Language) => void
  togglePanel: (panel: PanelPosition) => void
  setPanelVisibility: (panel: PanelPosition, visible: boolean) => void

  // === Debate Generation ===
  debateTasks: Record<string, DebateTask>
  startDebateGeneration: (conflictId: string, conflict: Conflict) => Promise<string | null>
  pollDebateTask: (taskId: string) => Promise<DebateTask | null>
  setDebateTask: (conflictId: string, task: DebateTask) => void

  // === Phase 7: Entity Supercut ===
  entityCard: EntityCardState
  supercutTasks: Record<string, SupercutTask>
  openEntityCard: (entity: GraphNode, position: { x: number; y: number }) => void
  closeEntityCard: () => void
  fetchEntityStats: (entityName: string) => Promise<EntityStats | null>
  startSupercutGeneration: (entityName: string) => Promise<string | null>
  pollSupercutTask: (taskId: string) => Promise<SupercutTask | null>
  setSupercutTask: (entityName: string, task: SupercutTask) => void

  // === Phase 8: Smart Digest ===
  digestTask: DigestTask | null
  digestIncludeTypes: string[]
  setDigestIncludeTypes: (types: string[]) => void
  startDigestGeneration: (sourceId: string) => Promise<string | null>
  pollDigestTask: (taskId: string) => Promise<DigestTask | null>
  setDigestTask: (task: DigestTask | null) => void

  // === Phase 10: AI Director Cut ===
  directorTasks: Record<string, DirectorTask>
  selectedPersona: Persona
  setSelectedPersona: (persona: Persona) => void
  startDirectorGeneration: (conflictId: string, conflict: Conflict, persona: Persona) => Promise<string | null>
  pollDirectorTask: (taskId: string) => Promise<DirectorTask | null>
  setDirectorTask: (conflictId: string, task: DirectorTask) => void

  // === Phase 11: Network Search Actions ===
  networkSearchTask: NetworkSearchTask | null
  startNetworkSearch: (platform: string, keyword: string, limit?: number) => Promise<string | null>
  pollNetworkSearchTask: (taskId: string) => Promise<NetworkSearchTask | null>
  setNetworkSearchTask: (task: NetworkSearchTask | null) => void

  // === One-Pager Report Actions ===
  onePagerData: OnePagerData | null
  isGeneratingOnePager: boolean
  fetchOnePager: (sourceId: string, useCache?: boolean) => Promise<OnePagerData | null>
  setOnePagerData: (data: OnePagerData | null) => void
}

// Empty initial state - no mock data
const initialGraph: KnowledgeGraph = {
  nodes: [],
  links: [],
}

const initialConflicts: Conflict[] = []

const initialTimeline: TimelineEvent[] = []

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (set, get) => ({
        // === Initial State ===
        sources: [],
        selectedSourceIds: [],
        currentSourceId: null,
        currentTime: 0,
        isPlaying: false,
        activePlayer: null,  // No player active initially
        conflicts: initialConflicts,
        graph: initialGraph,
        timeline: initialTimeline,
        isAnalyzing: false,
        messages: [
          {
            id: '1',
            role: 'ai',
            content: '您好！我是视界棱镜AI助手。请上传视频后向我提问，我将基于视频内容为您提供准确的回答。',
            timestamp: new Date(),
          },
        ],
        isLoading: false,
        sessionId: `session-${Date.now()}`,
        uploadState: {
          isUploading: false,
          progress: 0,
          error: null,
        },
        activeTab: 'conflicts',
        language: 'zh',
        panelVisibility: {
          left: true,
          bottom: true,
          right: true,
        },
        debateTasks: {},
        // Phase 7: Entity Supercut state
        entityCard: {
          isOpen: false,
          entity: null,
          stats: null,
          position: { x: 0, y: 0 },
          task: undefined,
        },
        supercutTasks: {},
        // Phase 8: Smart Digest state
        digestTask: null,
        digestIncludeTypes: ['STORY', 'COMBAT'],
        // Phase 10: AI Director state
        directorTasks: {},
        selectedPersona: 'pro' as Persona,
        // Phase 11: Network Search state
        networkSearchTask: null,
        // One-Pager Report state
        onePagerData: null,
        isGeneratingOnePager: false,

        // === Source Actions ===
        addSource: (source) =>
          set((state) => ({
            sources: [...state.sources, source],
          })),

        removeSource: (id) =>
          set((state) => ({
            sources: state.sources.filter((s) => s.id !== id),
            selectedSourceIds: state.selectedSourceIds.filter((sid) => sid !== id),
            currentSourceId: state.currentSourceId === id ? null : state.currentSourceId,
          })),

        toggleSourceSelection: (id) =>
          set((state) => ({
            selectedSourceIds: state.selectedSourceIds.includes(id)
              ? state.selectedSourceIds.filter((sid) => sid !== id)
              : [...state.selectedSourceIds, id],
          })),

        setCurrentSource: (id) =>
          set({ currentSourceId: id, currentTime: 0 }),

        setSources: (sources) =>
          set({ sources }),

        // === API Actions ===
        fetchSources: async () => {
          try {
            const response = await fetch(`${API_BASE}/sources/`)
            if (response.ok) {
              const data: SourceListResponse = await response.json()
              set({ sources: data.sources })

              // Auto-select first source if none selected
              if (data.sources.length > 0 && !get().currentSourceId) {
                set({
                  currentSourceId: data.sources[0].id,
                  selectedSourceIds: [data.sources[0].id],
                })
              }
            }
          } catch (error) {
            console.error('Failed to fetch sources:', error)
          }
        },

        uploadVideo: async (file: File) => {
          set({
            uploadState: { isUploading: true, progress: 0, error: null },
          })

          try {
            const formData = new FormData()
            formData.append('file', file)

            const response = await fetch(`${API_BASE}/sources/upload`, {
              method: 'POST',
              body: formData,
            })

            if (!response.ok) {
              const error = await response.json()
              throw new Error(error.detail || 'Upload failed')
            }

            const source: VideoSource = await response.json()

            set((state) => ({
              sources: [source, ...state.sources],
              currentSourceId: source.id,
              selectedSourceIds: [...state.selectedSourceIds, source.id],
              uploadState: { isUploading: false, progress: 100, error: null },
            }))

            return source
          } catch (error) {
            const message = error instanceof Error ? error.message : 'Upload failed'
            set({
              uploadState: { isUploading: false, progress: 0, error: message },
            })
            return null
          }
        },

        deleteSource: async (id: string) => {
          try {
            const response = await fetch(`${API_BASE}/sources/${id}`, {
              method: 'DELETE',
            })

            if (response.ok) {
              get().removeSource(id)
            }
          } catch (error) {
            console.error('Failed to delete source:', error)
          }
        },

        reprocessSource: async (id: string) => {
          try {
            const response = await fetch(`${API_BASE}/sources/${id}/reprocess`, {
              method: 'POST',
            })

            if (response.ok) {
              // Refresh sources to show updated status
              get().fetchSources()
            } else {
              const error = await response.json()
              console.error('Failed to reprocess source:', error)
            }
          } catch (error) {
            console.error('Failed to reprocess source:', error)
          }
        },

        // Phase 12: Lazy Analysis - Manually trigger analysis for imported sources
        analyzeSource: async (id: string) => {
          try {
            const response = await fetch(`${API_BASE}/sources/${id}/analyze`, {
              method: 'POST',
            })

            if (response.ok) {
              // Refresh sources to show updated status
              get().fetchSources()
            } else {
              const error = await response.json()
              console.error('Failed to analyze source:', error)
            }
          } catch (error) {
            console.error('Failed to analyze source:', error)
          }
        },

        fetchAnalysis: async (sourceIds?: string[]) => {
          const ids = sourceIds || get().selectedSourceIds
          if (ids.length === 0) {
            console.log('No sources selected for analysis')
            return
          }

          set({ isAnalyzing: true })

          try {
            const response = await fetch(`${API_BASE}/analysis/generate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ source_ids: ids, use_cache: true }),
            })

            if (response.ok) {
              const data: AnalysisResponse = await response.json()
              set({
                conflicts: data.conflicts,
                graph: data.graph,
                timeline: data.timeline,
                isAnalyzing: false,
              })
            } else {
              console.error('Failed to fetch analysis')
              set({ isAnalyzing: false })
            }
          } catch (error) {
            console.error('Failed to fetch analysis:', error)
            set({ isAnalyzing: false })
          }
        },

        sendChatMessage: async (message: string) => {
          const state = get()
          const userMessage: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: message,
            timestamp: new Date(),
          }

          set((s) => ({
            messages: [...s.messages, userMessage],
            isLoading: true,
          }))

          try {
            const sourceIds = state.selectedSourceIds.length > 0
              ? state.selectedSourceIds
              : state.sources.map((s) => s.id)

            const response = await fetch(`${API_BASE}/chat/`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                session_id: state.sessionId,
                message: message,
                source_ids: sourceIds,
              }),
            })

            if (response.ok) {
              const data: ChatAPIResponse = await response.json()

              const aiMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'ai',
                content: data.content,
                timestamp: new Date(),
                references: data.references,
              }

              set((s) => ({
                messages: [...s.messages, aiMessage],
                isLoading: false,
              }))
            } else {
              const errorData = await response.json()
              const aiMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'ai',
                content: `抱歉，处理您的问题时出现错误：${errorData.detail || '未知错误'}`,
                timestamp: new Date(),
              }
              set((s) => ({
                messages: [...s.messages, aiMessage],
                isLoading: false,
              }))
            }
          } catch (error) {
            console.error('Chat error:', error)
            const aiMessage: ChatMessage = {
              id: (Date.now() + 1).toString(),
              role: 'ai',
              content: '抱歉，网络连接出现问题，请稍后重试。',
              timestamp: new Date(),
            }
            set((s) => ({
              messages: [...s.messages, aiMessage],
              isLoading: false,
            }))
          }
        },

        // === Upload State ===
        setUploadState: (state) =>
          set((prev) => ({
            uploadState: { ...prev.uploadState, ...state },
          })),

        // === Playback Actions ===
        setCurrentTime: (time) =>
          set({ currentTime: time }),

        seekTo: (sourceId, time) =>
          set({
            currentSourceId: sourceId,
            currentTime: time,
            isPlaying: true, // Auto-play when seeking
            activePlayer: 'main', // Main stage becomes active player
          }),

        setIsPlaying: (playing) =>
          set({ isPlaying: playing }),

        setActivePlayer: (player) =>
          set((state) => ({
            activePlayer: player,
            // If main player is activated, set isPlaying; otherwise pause main player
            isPlaying: player === 'main' ? state.isPlaying : false,
          })),

        // === Analysis Actions ===
        setConflicts: (conflicts) =>
          set({ conflicts }),

        setGraph: (graph) =>
          set({ graph }),

        setTimeline: (timeline) =>
          set({ timeline }),

        // === Chat Actions ===
        addMessage: (message) =>
          set((state) => ({
            messages: [...state.messages, message],
          })),

        clearMessages: () =>
          set({ messages: [] }),

        setIsLoading: (loading) =>
          set({ isLoading: loading }),

        // === UI Actions ===
        setActiveTab: (tab) =>
          set({ activeTab: tab }),

        setLanguage: (lang) =>
          set({ language: lang }),

        togglePanel: (panel) =>
          set((state) => ({
            panelVisibility: {
              ...state.panelVisibility,
              [panel]: !state.panelVisibility[panel],
            },
          })),

        setPanelVisibility: (panel, visible) =>
          set((state) => ({
            panelVisibility: {
              ...state.panelVisibility,
              [panel]: visible,
            },
          })),

        // === Debate Generation Actions ===
        startDebateGeneration: async (conflictId: string, conflict: Conflict) => {
          // Set initial pending state
          set((state) => ({
            debateTasks: {
              ...state.debateTasks,
              [conflictId]: {
                task_id: '',
                status: 'pending',
                progress: 0,
                message: '正在启动任务...',
              },
            },
          }))

          try {
            const response = await fetch(`${API_BASE}/create/debate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                conflict_id: conflictId,
                source_a_id: conflict.viewpoint_a.source_id,
                time_a: conflict.viewpoint_a.timestamp || 0,
                source_b_id: conflict.viewpoint_b.source_id,
                time_b: conflict.viewpoint_b.timestamp || 0,
                topic: conflict.topic,
                viewpoint_a_title: conflict.viewpoint_a.title,
                viewpoint_a_description: conflict.viewpoint_a.description,
                viewpoint_b_title: conflict.viewpoint_b.title,
                viewpoint_b_description: conflict.viewpoint_b.description,
              }),
            })

            if (response.ok) {
              const data = await response.json()
              const task: DebateTask = {
                task_id: data.task_id,
                status: 'pending',
                progress: 0,
                message: data.message,
              }
              set((state) => ({
                debateTasks: { ...state.debateTasks, [conflictId]: task },
              }))
              return data.task_id
            } else {
              // Handle error response
              const errorData = await response.json().catch(() => ({ detail: '请求失败' }))
              set((state) => ({
                debateTasks: {
                  ...state.debateTasks,
                  [conflictId]: {
                    task_id: '',
                    status: 'error',
                    progress: 0,
                    message: errorData.detail || '视频源不存在，请先生成分析',
                    error: errorData.detail,
                  },
                },
              }))
              return null
            }
          } catch (error) {
            console.error('Failed to start debate generation:', error)
            set((state) => ({
              debateTasks: {
                ...state.debateTasks,
                [conflictId]: {
                  task_id: '',
                  status: 'error',
                  progress: 0,
                  message: '网络连接失败，请检查后端服务',
                  error: String(error),
                },
              },
            }))
            return null
          }
        },

        pollDebateTask: async (taskId: string) => {
          try {
            const response = await fetch(`${API_BASE}/create/tasks/${taskId}`)
            if (response.ok) {
              const data: DebateTask = await response.json()
              return data
            }
            return null
          } catch (error) {
            console.error('Failed to poll task:', error)
            return null
          }
        },

        setDebateTask: (conflictId: string, task: DebateTask) =>
          set((state) => ({
            debateTasks: { ...state.debateTasks, [conflictId]: task },
          })),

        // === Phase 7: Entity Supercut Actions ===
        openEntityCard: (entity: GraphNode, position: { x: number; y: number }) =>
          set({
            entityCard: {
              isOpen: true,
              entity,
              stats: null,
              position,
              task: undefined,
            },
          }),

        closeEntityCard: () =>
          set({
            entityCard: {
              isOpen: false,
              entity: null,
              stats: null,
              position: { x: 0, y: 0 },
              task: undefined,
            },
          }),

        fetchEntityStats: async (entityName: string) => {
          try {
            const response = await fetch(`${API_BASE}/create/entity/${encodeURIComponent(entityName)}/stats`)
            if (response.ok) {
              const stats: EntityStats = await response.json()
              set((state) => ({
                entityCard: { ...state.entityCard, stats },
              }))
              return stats
            }
            return null
          } catch (error) {
            console.error('Failed to fetch entity stats:', error)
            return null
          }
        },

        startSupercutGeneration: async (entityName: string) => {
          // Set initial pending state
          const pendingTask: SupercutTask = {
            task_id: '',
            status: 'pending',
            progress: 0,
            message: '正在启动任务...',
          }

          set((state) => ({
            supercutTasks: { ...state.supercutTasks, [entityName]: pendingTask },
            entityCard: { ...state.entityCard, task: pendingTask },
          }))

          try {
            const response = await fetch(`${API_BASE}/create/supercut`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                entity_name: entityName,
                top_k: 5,
              }),
            })

            if (response.ok) {
              const data = await response.json()
              const task: SupercutTask = {
                task_id: data.task_id,
                status: 'pending',
                progress: 0,
                message: data.message,
              }
              set((state) => ({
                supercutTasks: { ...state.supercutTasks, [entityName]: task },
                entityCard: { ...state.entityCard, task },
              }))
              return data.task_id
            } else {
              const errorData = await response.json().catch(() => ({ detail: '请求失败' }))
              const errorTask: SupercutTask = {
                task_id: '',
                status: 'error',
                progress: 0,
                message: errorData.detail || '生成失败',
                error: errorData.detail,
              }
              set((state) => ({
                supercutTasks: { ...state.supercutTasks, [entityName]: errorTask },
                entityCard: { ...state.entityCard, task: errorTask },
              }))
              return null
            }
          } catch (error) {
            console.error('Failed to start supercut generation:', error)
            const errorTask: SupercutTask = {
              task_id: '',
              status: 'error',
              progress: 0,
              message: '网络连接失败',
              error: String(error),
            }
            set((state) => ({
              supercutTasks: { ...state.supercutTasks, [entityName]: errorTask },
              entityCard: { ...state.entityCard, task: errorTask },
            }))
            return null
          }
        },

        pollSupercutTask: async (taskId: string) => {
          try {
            const response = await fetch(`${API_BASE}/create/tasks/${taskId}`)
            if (response.ok) {
              const data: SupercutTask = await response.json()
              return data
            }
            return null
          } catch (error) {
            console.error('Failed to poll supercut task:', error)
            return null
          }
        },

        setSupercutTask: (entityName: string, task: SupercutTask) =>
          set((state) => ({
            supercutTasks: { ...state.supercutTasks, [entityName]: task },
            entityCard: state.entityCard.entity?.name === entityName
              ? { ...state.entityCard, task }
              : state.entityCard,
          })),

        // === Phase 8: Smart Digest Actions ===
        setDigestIncludeTypes: (types: string[]) =>
          set({ digestIncludeTypes: types }),

        startDigestGeneration: async (sourceId: string) => {
          const state = get()

          // Set initial pending state
          const pendingTask: DigestTask = {
            task_id: '',
            status: 'pending',
            progress: 0,
            message: '正在启动任务...',
          }

          set({ digestTask: pendingTask })

          try {
            const response = await fetch(`${API_BASE}/create/digest`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                source_id: sourceId,
                include_types: state.digestIncludeTypes,
              }),
            })

            if (response.ok) {
              const data = await response.json()
              const task: DigestTask = {
                task_id: data.task_id,
                status: 'pending',
                progress: 0,
                message: data.message,
              }
              set({ digestTask: task })
              return data.task_id
            } else {
              const errorData = await response.json().catch(() => ({ detail: '请求失败' }))
              const errorTask: DigestTask = {
                task_id: '',
                status: 'error',
                progress: 0,
                message: errorData.detail || '生成失败',
                error: errorData.detail,
              }
              set({ digestTask: errorTask })
              return null
            }
          } catch (error) {
            console.error('Failed to start digest generation:', error)
            const errorTask: DigestTask = {
              task_id: '',
              status: 'error',
              progress: 0,
              message: '网络连接失败',
              error: String(error),
            }
            set({ digestTask: errorTask })
            return null
          }
        },

        pollDigestTask: async (taskId: string) => {
          try {
            const response = await fetch(`${API_BASE}/create/tasks/${taskId}`)
            if (response.ok) {
              const data: DigestTask = await response.json()
              return data
            }
            return null
          } catch (error) {
            console.error('Failed to poll digest task:', error)
            return null
          }
        },

        setDigestTask: (task: DigestTask | null) =>
          set({ digestTask: task }),

        // === Phase 10: AI Director Cut Actions ===
        setSelectedPersona: (persona: Persona) =>
          set({ selectedPersona: persona }),

        startDirectorGeneration: async (conflictId: string, conflict: Conflict, persona: Persona) => {
          // Set initial pending state
          set((state) => ({
            directorTasks: {
              ...state.directorTasks,
              [conflictId]: {
                task_id: '',
                status: 'pending',
                progress: 0,
                message: '正在启动AI导演...',
              },
            },
          }))

          try {
            const response = await fetch(`${API_BASE}/create/director_cut`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                conflict_id: conflictId,
                source_a_id: conflict.viewpoint_a.source_id,
                time_a: conflict.viewpoint_a.timestamp || 0,
                source_b_id: conflict.viewpoint_b.source_id,
                time_b: conflict.viewpoint_b.timestamp || 0,
                persona: persona,
                topic: conflict.topic,
                viewpoint_a_title: conflict.viewpoint_a.title,
                viewpoint_a_description: conflict.viewpoint_a.description,
                viewpoint_b_title: conflict.viewpoint_b.title,
                viewpoint_b_description: conflict.viewpoint_b.description,
              }),
            })

            if (response.ok) {
              const data = await response.json()
              const task: DirectorTask = {
                task_id: data.task_id,
                status: 'pending',
                progress: 0,
                message: data.message,
                persona: persona,
              }
              set((state) => ({
                directorTasks: { ...state.directorTasks, [conflictId]: task },
              }))
              return data.task_id
            } else {
              const errorData = await response.json().catch(() => ({ detail: '请求失败' }))
              set((state) => ({
                directorTasks: {
                  ...state.directorTasks,
                  [conflictId]: {
                    task_id: '',
                    status: 'error',
                    progress: 0,
                    message: errorData.detail || '生成失败',
                    error: errorData.detail,
                  },
                },
              }))
              return null
            }
          } catch (error) {
            console.error('Failed to start director generation:', error)
            set((state) => ({
              directorTasks: {
                ...state.directorTasks,
                [conflictId]: {
                  task_id: '',
                  status: 'error',
                  progress: 0,
                  message: '网络连接失败',
                  error: String(error),
                },
              },
            }))
            return null
          }
        },

        pollDirectorTask: async (taskId: string) => {
          try {
            const response = await fetch(`${API_BASE}/create/director/tasks/${taskId}`)
            if (response.ok) {
              const data: DirectorTask = await response.json()
              return data
            }
            return null
          } catch (error) {
            console.error('Failed to poll director task:', error)
            return null
          }
        },

        setDirectorTask: (conflictId: string, task: DirectorTask) =>
          set((state) => ({
            directorTasks: { ...state.directorTasks, [conflictId]: task },
          })),

        // === Phase 11: Network Search Actions ===
        startNetworkSearch: async (platform: string, keyword: string, limit: number = 3) => {
          // Set initial pending state
          const pendingTask: NetworkSearchTask = {
            task_id: '',
            status: 'pending',
            progress: 0,
            message: '正在启动搜索...',
          }

          set({ networkSearchTask: pendingTask })

          try {
            const response = await fetch(`${API_BASE}/ingest/search`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                platform,
                keyword,
                limit,
              }),
            })

            if (response.ok) {
              const data = await response.json()
              const task: NetworkSearchTask = {
                task_id: data.task_id,
                status: 'searching',
                progress: 10,
                message: data.message,
              }
              set({ networkSearchTask: task })

              // Start polling for updates
              const pollAndRefresh = async () => {
                const state = get()
                if (state.networkSearchTask?.status !== 'searching' &&
                    state.networkSearchTask?.status !== 'downloading' &&
                    state.networkSearchTask?.status !== 'ingesting' &&
                    state.networkSearchTask?.status !== 'pending') {
                  // Task completed or errored, refresh sources
                  if (state.networkSearchTask?.status === 'completed') {
                    get().fetchSources()
                  }
                  return
                }

                const updatedTask = await get().pollNetworkSearchTask(data.task_id)
                if (updatedTask) {
                  set({ networkSearchTask: updatedTask })

                  // If completed, refresh sources
                  if (updatedTask.status === 'completed') {
                    get().fetchSources()
                  } else if (updatedTask.status === 'searching' ||
                             updatedTask.status === 'downloading' ||
                             updatedTask.status === 'ingesting' ||
                             updatedTask.status === 'pending') {
                    // Continue polling
                    setTimeout(pollAndRefresh, 2000)
                  }
                }
              }

              // Start polling after a short delay
              setTimeout(pollAndRefresh, 1000)

              return data.task_id
            } else {
              const errorData = await response.json().catch(() => ({ detail: '请求失败' }))
              const errorTask: NetworkSearchTask = {
                task_id: '',
                status: 'error',
                progress: 0,
                message: errorData.detail || '搜索失败',
                error: errorData.detail,
              }
              set({ networkSearchTask: errorTask })
              return null
            }
          } catch (error) {
            console.error('Failed to start network search:', error)
            const errorTask: NetworkSearchTask = {
              task_id: '',
              status: 'error',
              progress: 0,
              message: '网络连接失败',
              error: String(error),
            }
            set({ networkSearchTask: errorTask })
            return null
          }
        },

        pollNetworkSearchTask: async (taskId: string) => {
          try {
            const response = await fetch(`${API_BASE}/ingest/tasks/${taskId}`)
            if (response.ok) {
              const data: NetworkSearchTask = await response.json()
              return data
            }
            return null
          } catch (error) {
            console.error('Failed to poll network search task:', error)
            return null
          }
        },

        setNetworkSearchTask: (task: NetworkSearchTask | null) =>
          set({ networkSearchTask: task }),

        // === One-Pager Report Actions ===
        fetchOnePager: async (sourceId: string, useCache: boolean = true) => {
          set({ isGeneratingOnePager: true })

          try {
            const response = await fetch(`${API_BASE}/analysis/one-pager`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                source_id: sourceId,
                use_cache: useCache,
              }),
            })

            if (response.ok) {
              const data: OnePagerData = await response.json()
              set({ onePagerData: data, isGeneratingOnePager: false })
              return data
            } else {
              const errorData = await response.json().catch(() => ({ detail: '请求失败' }))
              console.error('Failed to fetch one-pager:', errorData)
              set({ isGeneratingOnePager: false })
              return null
            }
          } catch (error) {
            console.error('One-pager fetch error:', error)
            set({ isGeneratingOnePager: false })
            return null
          }
        },

        setOnePagerData: (data: OnePagerData | null) =>
          set({ onePagerData: data }),
      }),
      {
        name: 'viewpoint-prism-storage',
        partialize: (state) => ({
          language: state.language,
          panelVisibility: state.panelVisibility,
        }),
      }
    ),
    { name: 'ViewpointPrismStore' }
  )
)
