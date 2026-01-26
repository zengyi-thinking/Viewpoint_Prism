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
  LeftPanelMode,
  UploadState,
  DebateTask,
  SupercutTask,
  EntityStats,
  GraphNode,
  DigestTask,
  ActivePlayer,
  DirectorTask,
  Persona,
  NetworkSearchTask,
  OnePagerData,
} from '@/types/modules'
import { SourceAPI } from '@/api/modules/source'
import { AnalysisAPI } from '@/api/modules/analysis'
import { ChatAPI } from '@/api/modules/chat'
import { DebateAPI } from '@/api/modules/debate'
import { DirectorAPI } from '@/api/modules/director'
import { IngestAPI } from '@/api/modules/ingest'
import { CreativeAPI } from '@/api/modules/creative'

interface AppStore {
  sources: VideoSource[]
  selectedSourceIds: string[]
  currentSourceId: string | null
  sessionStartedAt: string | null

  // 进度条点击分析
  progressClickHistory: Array<{ time: number; timestamp: number }>
  analyzeProgressClick: (time: number, duration: number) => Promise<void>

  addSource: (source: VideoSource) => void
  removeSource: (id: string) => void
  toggleSourceSelection: (id: string) => void
  setCurrentSource: (id: string | null) => void
  setSources: (sources: VideoSource[]) => void

  fetchSources: () => Promise<void>
  uploadVideo: (file: File) => Promise<VideoSource | null>
  deleteSource: (id: string) => Promise<void>
  reprocessSource: (id: string) => Promise<void>
  analyzeSource: (id: string) => Promise<void>
  fetchAnalysis: (sourceIds?: string[]) => Promise<void>
  sendChatMessage: (message: string) => Promise<void>

  uploadState: UploadState
  setUploadState: (state: Partial<UploadState>) => void

  currentTime: number
  isPlaying: boolean
  activePlayer: ActivePlayer

  setCurrentTime: (time: number) => void
  seekTo: (sourceId: string, time: number) => void
  setIsPlaying: (playing: boolean) => void
  setActivePlayer: (player: ActivePlayer) => void

  conflicts: Conflict[]
  graph: KnowledgeGraph
  timeline: TimelineEvent[]
  isAnalyzing: boolean

  setConflicts: (conflicts: Conflict[]) => void
  setGraph: (graph: KnowledgeGraph) => void
  setTimeline: (timeline: TimelineEvent[]) => void

  messages: ChatMessage[]
  isLoading: boolean
  sessionId: string

  addMessage: (message: ChatMessage) => void
  clearMessages: () => void
  setIsLoading: (loading: boolean) => void

  activeTab: AnalysisTab
  language: Language
  panelVisibility: Record<PanelPosition, boolean>
  leftPanelMode: LeftPanelMode
  // @deprecated 现在使用路由系统控制页面显示，不再使用此状态
  showProductPage: boolean

  setActiveTab: (tab: AnalysisTab) => void
  setLanguage: (lang: Language) => void
  togglePanel: (panel: PanelPosition) => void
  setPanelVisibility: (panel: PanelPosition, visible: boolean) => void
  setLeftPanelMode: (mode: LeftPanelMode) => void
  // @deprecated 现在使用路由系统，不再需要此函数
  setShowProductPage: (show: boolean) => void

  debateTasks: Record<string, DebateTask>
  startDebateGeneration: (conflictId: string, conflict: Conflict) => Promise<string | null>
  pollDebateTask: (taskId: string) => Promise<DebateTask | null>
  setDebateTask: (conflictId: string, task: DebateTask) => void

  entityCard: {
    isOpen: boolean
    entity: GraphNode | null
    stats: EntityStats | null
    position: { x: number; y: number }
    task?: SupercutTask
  }
  supercutTasks: Record<string, SupercutTask>
  openEntityCard: (entity: GraphNode, position: { x: number; y: number }) => void
  closeEntityCard: () => void
  fetchEntityStats: (entityName: string) => Promise<EntityStats | null>
  startSupercutGeneration: (entityName: string) => Promise<string | null>
  pollSupercutTask: (taskId: string) => Promise<SupercutTask | null>
  setSupercutTask: (entityName: string, task: SupercutTask) => void

  digestTask: DigestTask | null
  digestIncludeTypes: string[]
  setDigestIncludeTypes: (types: string[]) => void
  startDigestGeneration: (sourceId: string) => Promise<string | null>
  pollDigestTask: (taskId: string) => Promise<DigestTask | null>
  setDigestTask: (task: DigestTask | null) => void

  directorTasks: Record<string, DirectorTask>
  selectedPersona: Persona
  setSelectedPersona: (persona: Persona) => void
  startDirectorGeneration: (conflictId: string, conflict: Conflict, persona: Persona) => Promise<string | null>
  pollDirectorTask: (taskId: string) => Promise<DirectorTask | null>
  setDirectorTask: (conflictId: string, task: DirectorTask) => void

  networkSearchTask: NetworkSearchTask | null
  startNetworkSearch: (platform: string, keyword: string, limit?: number) => Promise<string | null>
  pollNetworkSearchTask: (taskId: string) => Promise<NetworkSearchTask | null>
  setNetworkSearchTask: (task: NetworkSearchTask | null) => void

  onePagerData: OnePagerData | null
  isGeneratingOnePager: boolean
  fetchOnePager: (sourceIds: string[], useCache?: boolean) => Promise<OnePagerData | null>
  setOnePagerData: (data: OnePagerData | null) => void
}

const initialGraph: KnowledgeGraph = {
  nodes: [],
  links: [],
}

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (set, get) => ({
        sources: [],
        selectedSourceIds: [],
        currentSourceId: null,
        sessionStartedAt: null,
        currentTime: 0,
        isPlaying: false,
        activePlayer: null,
        conflicts: [],
        graph: initialGraph,
        timeline: [],
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
        leftPanelMode: 'sources',
        showProductPage: true,
        debateTasks: {},
        entityCard: {
          isOpen: false,
          entity: null,
          stats: null,
          position: { x: 0, y: 0 },
          task: undefined,
        },
        supercutTasks: {},
        digestTask: null,
        digestIncludeTypes: ['STORY', 'COMBAT'],
        directorTasks: {},
        selectedPersona: 'pro' as Persona,
        networkSearchTask: null,
        onePagerData: null,
        isGeneratingOnePager: false,
        progressClickHistory: [],

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

        fetchSources: async () => {
          try {
            const data = await SourceAPI.list()
            const sessionStart = get().sessionStartedAt
            let filteredSources = data.sources

            // 只有当 sessionStartedAt 存在时才过滤
            if (sessionStart) {
              const sessionStartTime = new Date(sessionStart).getTime()
              filteredSources = data.sources.filter((s) => {
                const createdAt = new Date(s.created_at).getTime()
                return Number.isNaN(createdAt) || createdAt >= sessionStartTime
              })
            }

            set({ sources: filteredSources })
            if (filteredSources.length > 0 && !get().currentSourceId) {
              set({
                currentSourceId: filteredSources[0].id,
                selectedSourceIds: [filteredSources[0].id],
              })
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
            const source = await SourceAPI.upload(file, (progress) => {
              set({
                uploadState: { isUploading: true, progress, error: null },
              })
            })
            set((state) => ({
              sources: [source, ...state.sources],
              currentSourceId: source.id,
              selectedSourceIds: [...state.selectedSourceIds, source.id],
              uploadState: { isUploading: false, progress: 100, error: null },
              sessionStartedAt: state.sessionStartedAt ?? source.created_at,
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
            await SourceAPI.delete(id)
            get().removeSource(id)
          } catch (error) {
            console.error('Failed to delete source:', error)
          }
        },

        reprocessSource: async (id: string) => {
          try {
            await SourceAPI.reprocess(id)
            get().fetchSources()
          } catch (error) {
            console.error('Failed to reprocess source:', error)
          }
        },

        analyzeSource: async (id: string) => {
          try {
            await SourceAPI.analyze(id)
            get().fetchSources()
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
            const data = await AnalysisAPI.generate({ source_ids: ids, use_cache: true })
            set({
              conflicts: data.conflicts,
              graph: data.graph,
              timeline: data.timeline,
              isAnalyzing: false,
            })
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
            const data = await ChatAPI.chat({
              session_id: state.sessionId,
              message,
              source_ids: sourceIds,
            })
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

        setUploadState: (state) =>
          set((prev) => ({
            uploadState: { ...prev.uploadState, ...state },
          })),

        setCurrentTime: (time) =>
          set({ currentTime: time }),

        seekTo: (sourceId, time) =>
          set({
            currentSourceId: sourceId,
            currentTime: time,
            isPlaying: true,
            activePlayer: 'main',
          }),

        analyzeProgressClick: async (time, duration) => {
          const state = get()
          const now = Date.now()

          // 记录点击历史（保留最近10次）
          const newHistory = [...state.progressClickHistory, { time, timestamp: now }].slice(-10)
          set({ progressClickHistory: newHistory })

          // 分析点击模式
          const recentClicks = newHistory.filter(c => now - c.timestamp < 30000) // 30秒内

          let analysisPrompt = ''

          if (recentClicks.length >= 3) {
            // 检测是否有重复点击某个区间
            const times = recentClicks.map(c => c.time)
            const minTime = Math.min(...times)
            const maxTime = Math.max(...times)
            const range = maxTime - minTime
            const avgTime = times.reduce((a, b) => a + b, 0) / times.length

            // 如果点击集中在某个区间（范围小于总时长的20%）
            if (range < duration * 0.2) {
              const startMin = Math.floor(minTime / 60)
              const startSec = Math.floor(minTime % 60)
              const endMin = Math.floor(maxTime / 60)
              const endSec = Math.floor(maxTime % 60)

              analysisPrompt = `我反复查看了 ${startMin}:${String(startSec).padStart(2, '0')} 到 ${endMin}:${String(endSec).padStart(2, '0')} 这段内容，请详细分析这段视频在讲什么？`
            } else {
              // 分析从开始到平均点击位置
              const avgMin = Math.floor(avgTime / 60)
              const avgSec = Math.floor(avgTime % 60)
              analysisPrompt = `请帮我分析从视频开始到 ${avgMin}:${String(avgSec).padStart(2, '0')} 这个时间点之前的内容`
            }
          } else {
            // 第一次点击：分析从0到点击位置
            const min = Math.floor(time / 60)
            const sec = Math.floor(time % 60)
            analysisPrompt = `请帮我分析从视频开始到 ${min}:${String(sec).padStart(2, '0')} 这个时间点之前的内容`
          }

          // 发送到聊天
          await state.sendChatMessage(analysisPrompt)
        },

        setIsPlaying: (playing) =>
          set({ isPlaying: playing }),

        setActivePlayer: (player) =>
          set((state) => ({
            activePlayer: player,
            isPlaying: player === 'main' ? state.isPlaying : false,
          })),

        setConflicts: (conflicts) =>
          set({ conflicts }),

        setGraph: (graph) =>
          set({ graph }),

        setTimeline: (timeline) =>
          set({ timeline }),

        addMessage: (message) =>
          set((state) => ({
            messages: [...state.messages, message],
          })),

        clearMessages: () =>
          set({ messages: [] }),

        setIsLoading: (loading) =>
          set({ isLoading: loading }),

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

        setLeftPanelMode: (mode) =>
          set({ leftPanelMode: mode }),

        setShowProductPage: (show) =>
          set({ showProductPage: show }),

        startDebateGeneration: async (conflictId: string, conflict: Conflict) => {
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
            const data = await DebateAPI.generate({
              source_a_id: conflict.viewpoint_a.source_id,
              time_a: conflict.viewpoint_a.timestamp || 0,
              source_b_id: conflict.viewpoint_b.source_id,
              time_b: conflict.viewpoint_b.timestamp || 0,
              topic: conflict.topic,
              viewpoint_a_title: conflict.viewpoint_a.title,
              viewpoint_a_description: conflict.viewpoint_a.description,
              viewpoint_b_title: conflict.viewpoint_b.title,
              viewpoint_b_description: conflict.viewpoint_b.description,
            })
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
          } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : '请求失败'
            set((state) => ({
              debateTasks: {
                ...state.debateTasks,
                [conflictId]: {
                  task_id: '',
                  status: 'error',
                  progress: 0,
                  message: errorMessage,
                  error: errorMessage,
                },
              },
            }))
            return null
          }
        },

        pollDebateTask: async (taskId: string) => {
          try {
            const data = await DebateAPI.getTaskStatus(taskId)
            return data as unknown as DebateTask
          } catch (error) {
            console.error('Failed to poll task:', error)
            return null
          }
        },

        setDebateTask: (conflictId: string, task: DebateTask) =>
          set((state) => ({
            debateTasks: { ...state.debateTasks, [conflictId]: task },
          })),

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
            const stats = await CreativeAPI.entity.getStats(entityName)
            set((state) => ({
              entityCard: { ...state.entityCard, stats },
            }))
            return stats
          } catch (error) {
            console.error('Failed to fetch entity stats:', error)
            return null
          }
        },

        startSupercutGeneration: async (entityName: string) => {
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
            const data = await CreativeAPI.supercut.create({ entity_name: entityName, top_k: 5 })
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
          } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : '生成失败'
            const errorTask: SupercutTask = {
              task_id: '',
              status: 'error',
              progress: 0,
              message: errorMessage,
              error: errorMessage,
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
            const data = await CreativeAPI.supercut.getStatus(taskId)
            return data
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

        setDigestIncludeTypes: (types) =>
          set({ digestIncludeTypes: types }),

        startDigestGeneration: async (sourceId: string) => {
          const state = get()
          const pendingTask: DigestTask = {
            task_id: '',
            status: 'pending',
            progress: 0,
            message: '正在启动任务...',
          }
          set({ digestTask: pendingTask })
          try {
            const data = await CreativeAPI.digest.create({
              source_id: sourceId,
              include_types: state.digestIncludeTypes,
            })
            const task: DigestTask = {
              task_id: data.task_id,
              status: 'pending',
              progress: 0,
              message: data.message,
            }
            set({ digestTask: task })
            return data.task_id
          } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : '生成失败'
            const errorTask: DigestTask = {
              task_id: '',
              status: 'error',
              progress: 0,
              message: errorMessage,
              error: errorMessage,
            }
            set({ digestTask: errorTask })
            return null
          }
        },

        pollDigestTask: async (taskId: string) => {
          try {
            const data = await CreativeAPI.digest.getStatus(taskId)
            return data
          } catch (error) {
            console.error('Failed to poll digest task:', error)
            return null
          }
        },

        setDigestTask: (task: DigestTask | null) =>
          set({ digestTask: task }),

        setSelectedPersona: (persona) =>
          set({ selectedPersona: persona }),

        startDirectorGeneration: async (conflictId: string, conflict: Conflict, persona: Persona) => {
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
            const data = await DirectorAPI.createCut({
              source_a_id: conflict.viewpoint_a.source_id,
              time_a: conflict.viewpoint_a.timestamp || 0,
              source_b_id: conflict.viewpoint_b.source_id,
              time_b: conflict.viewpoint_b.timestamp || 0,
              topic: conflict.topic,
              viewpoint_a_title: conflict.viewpoint_a.title,
              viewpoint_a_description: conflict.viewpoint_a.description,
              viewpoint_b_title: conflict.viewpoint_b.title,
              viewpoint_b_description: conflict.viewpoint_b.description,
              persona,
            })
            const task: DirectorTask = {
              task_id: data.task_id,
              status: 'pending',
              progress: 0,
              message: data.message,
              persona,
            }
            set((state) => ({
              directorTasks: { ...state.directorTasks, [conflictId]: task },
            }))
            return data.task_id
          } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : '生成失败'
            set((state) => ({
              directorTasks: {
                ...state.directorTasks,
                [conflictId]: {
                  task_id: '',
                  status: 'error',
                  progress: 0,
                  message: errorMessage,
                  error: errorMessage,
                },
              },
            }))
            return null
          }
        },

        pollDirectorTask: async (taskId: string) => {
          try {
            const data = await DirectorAPI.getTaskStatus(taskId)
            return data as unknown as DirectorTask
          } catch (error) {
            console.error('Failed to poll director task:', error)
            return null
          }
        },

        setDirectorTask: (conflictId: string, task: DirectorTask) =>
          set((state) => ({
            directorTasks: { ...state.directorTasks, [conflictId]: task },
          })),

        startNetworkSearch: async (platform: string, keyword: string, limit: number = 3) => {
          const pendingTask: NetworkSearchTask = {
            task_id: '',
            status: 'pending',
            progress: 0,
            message: '正在启动搜索...',
          }
          set({ networkSearchTask: pendingTask })
          try {
            const data = await IngestAPI.search({ platform, keyword, limit })
            const task: NetworkSearchTask = {
              task_id: data.task_id,
              status: 'searching',
              progress: 10,
              message: data.message,
            }
            set({ networkSearchTask: task })
            const pollAndRefresh = async () => {
              const state = get()
              if (state.networkSearchTask?.status !== 'searching' &&
                  state.networkSearchTask?.status !== 'downloading' &&
                  state.networkSearchTask?.status !== 'ingesting' &&
                  state.networkSearchTask?.status !== 'pending') {
                if (state.networkSearchTask?.status === 'completed') {
                  get().fetchSources()
                }
                return
              }
              const updatedTask = await get().pollNetworkSearchTask(data.task_id)
              if (updatedTask) {
                set({ networkSearchTask: updatedTask })
                if (updatedTask.status === 'completed') {
                  get().fetchSources()
                } else if (['searching', 'downloading', 'ingesting', 'pending'].includes(updatedTask.status)) {
                  setTimeout(pollAndRefresh, 2000)
                }
              }
            }
            setTimeout(pollAndRefresh, 1000)
            return data.task_id
          } catch (error: unknown) {
            const errorMessage = error instanceof Error ? error.message : '搜索失败'
            const errorTask: NetworkSearchTask = {
              task_id: '',
              status: 'error',
              progress: 0,
              message: errorMessage,
              error: errorMessage,
            }
            set({ networkSearchTask: errorTask })
            return null
          }
        },

        pollNetworkSearchTask: async (taskId: string) => {
          try {
            const data = await IngestAPI.getTaskStatus(taskId)
            return data as unknown as NetworkSearchTask
          } catch (error) {
            console.error('Failed to poll network search task:', error)
            return null
          }
        },

        setNetworkSearchTask: (task: NetworkSearchTask | null) =>
          set({ networkSearchTask: task }),

        fetchOnePager: async (sourceIds: string[], useCache: boolean = true) => {
          if (sourceIds.length === 0) {
            console.warn('No source IDs provided for one-pager')
            return null
          }
          set({ isGeneratingOnePager: true })
          try {
            const data = await CreativeAPI.onePager.create({ source_ids: sourceIds, use_cache: useCache })
            set({ onePagerData: data, isGeneratingOnePager: false })
            return data
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
