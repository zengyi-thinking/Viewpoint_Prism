import { useState, useEffect } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Zap, Network, Clock, FileText, Loader2, Video, Users, Scissors, Sparkles, CheckCircle, XCircle, Play, Download } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactECharts from 'echarts-for-react'
import { FeatureCard } from '@/components/ui/FeatureCard'

// Task status polling hook
function useTaskPoll<T>(taskId: string | null, pollFn: (id: string) => Promise<T | null>, onComplete?: (result: T) => void) {
  const [status, setStatus] = useState<'pending' | 'processing' | 'completed' | 'error'>('pending')
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<T | null>(null)

  useEffect(() => {
    if (!taskId) return

    const poll = async () => {
      const data = await pollFn(taskId)
      if (!data) return

      setResult(data as T)
      setStatus(data.status || 'processing')

      if (data.status === 'completed') {
        setProgress(100)
        onComplete?.(data as T)
      } else if (data.status === 'error') {
        setProgress(0)
      } else if (data.progress) {
        setProgress(data.progress)
      }
    }

    poll()
    const interval = setInterval(poll, 2000)
    return () => clearInterval(interval)
  }, [taskId, pollFn, onComplete])

  return { status, progress, result }
}

export function AnalysisPanel() {
  const {
    activeTab,
    setActiveTab,
    conflicts,
    graph,
    timeline,
    isAnalyzing,
    fetchAnalysis,
    selectedSourceIds,
    language,
    // Studio tasks
    debateTasks,
    directorTasks,
    supercutTasks,
    digestTask,
    networkSearchTask,
    selectedPersona,
    digestIncludeTypes,
    // Actions
    startDebateGeneration,
    pollDebateTask,
    setDebateTask,
    startDirectorGeneration,
    pollDirectorTask,
    setDirectorTask,
    setSelectedPersona,
    openEntityCard,
    closeEntityCard,
    startSupercutGeneration,
    pollSupercutTask,
    setSupercutTask,
    startDigestGeneration,
    pollDigestTask,
    setDigestTask,
    setDigestIncludeTypes,
    setActivePlayer
  } = useAppStore()

  const [pendingTask, setPendingTask] = useState<{ type: string; id: string } | null>(null)

  // Handle creative generation
  const handleStartDebate = async (conflictId: string, conflict: typeof conflicts[0]) => {
    const taskId = await startDebateGeneration(conflictId, conflict)
    if (taskId) {
      setPendingTask({ type: 'debate', id: conflictId })
      setDebateTask(conflictId, { status: 'pending', progress: 0, task_id: taskId })
    }
  }

  const handleStartDirector = async (conflictId: string, conflict: typeof conflicts[0]) => {
    const taskId = await startDirectorGeneration(conflictId, conflict, selectedPersona)
    if (taskId) {
      setPendingTask({ type: 'director', id: conflictId })
      setDirectorTask(conflictId, { status: 'pending', progress: 0, task_id: taskId })
    }
  }

  const handleStartSupercut = async (entityName: string) => {
    const taskId = await startSupercutGeneration(entityName)
    if (taskId) {
      setPendingTask({ type: 'supercut', id: entityName })
      setSupercutTask(entityName, { status: 'pending', progress: 0, task_id: taskId })
    }
  }

  const handleStartDigest = async (sourceId: string) => {
    const taskId = await startDigestGeneration(sourceId)
    if (taskId) {
      setPendingTask({ type: 'digest', id: sourceId })
      setDigestTask({ status: 'pending', progress: 0, task_id: taskId })
    }
  }

  const tabs = [
    { id: 'studio' as const, icon: Zap, label: 'Studio' },
    { id: 'conflicts' as const, icon: Network, label: 'Conflicts' },
    { id: 'graph' as const, icon: Network, label: 'Graph' },
    { id: 'timeline' as const, icon: Clock, label: 'Timeline' },
    { id: 'report' as const, icon: FileText, label: 'Report' },
  ]

  return (
    <div className="h-full flex flex-col bg-[#09090b]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800/50">
        <h2 className="text-sm font-semibold text-zinc-100 mb-3">Analysis</h2>

        {/* Tabs */}
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                activeTab === tab.id
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              )}
            >
              <tab.icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {selectedSourceIds.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">
            <p className="text-sm">Select sources to analyze</p>
            <p className="text-xs mt-1">Choose at least one video from the Sources panel</p>
          </div>
        ) : isAnalyzing ? (
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-violet-500 mb-3" />
            <p className="text-sm text-zinc-400">Analyzing videos...</p>
          </div>
        ) : (
          <>
            {activeTab === 'studio' && (
              <div className="space-y-4">
                <p className="text-xs text-zinc-500 text-center mb-4">
                  AI-powered creative video generation tools
                </p>

                {/* Debate Video */}
                <FeatureCard
                  title="AI Debate Video"
                  icon={Video}
                  description={language === 'zh' ? "生成观点碰撞的辩论视频" : "Generate split-screen debate videos from conflicting viewpoints"}
                  color="bg-gradient-to-br from-red-500 to-orange-500"
                  glowColor="bg-gradient-to-br from-red-500/20 to-orange-500/20"
                  onClick={() => {
                    if (conflicts.length > 0) {
                      handleStartDebate(conflicts[0].id, conflicts[0])
                    }
                  }}
                  disabled={conflicts.length === 0}
                />

                {/* Director Cut */}
                <FeatureCard
                  title="AI Director Cut"
                  icon={Sparkles}
                  description={language === 'zh' ? "AI导演剪辑，多人设解说" : "AI-narrated director cuts with multiple personas"}
                  color="bg-gradient-to-br from-violet-500 to-purple-500"
                  glowColor="bg-gradient-to-br from-violet-500/20 to-purple-500/20"
                  onClick={() => {
                    if (conflicts.length > 0) {
                      handleStartDirector(conflicts[0].id, conflicts[0])
                    }
                  }}
                  disabled={conflicts.length === 0}
                />

                {/* Entity Supercut */}
                <FeatureCard
                  title="Entity Supercut"
                  icon={Scissors}
                  description={language === 'zh' ? "基于知识图谱的实体混剪" : "Auto-generate supercuts from knowledge graph entities"}
                  color="bg-gradient-to-br from-blue-500 to-cyan-500"
                  glowColor="bg-gradient-to-br from-blue-500/20 to-cyan-500/20"
                  onClick={() => {
                    if (graph.nodes.length > 0) {
                      handleStartSupercut(graph.nodes[0].name)
                    }
                  }}
                  disabled={graph.nodes.length === 0}
                />

                {/* Smart Digest */}
                <FeatureCard
                  title="Smart Digest"
                  icon={Clock}
                  description={language === 'zh' ? "基于时间轴的智能浓缩" : "浓缩高价值片段的精简版视频"}
                  color="bg-gradient-to-br from-emerald-500 to-teal-500"
                  glowColor="bg-gradient-to-br from-emerald-500/20 to-teal-500/20"
                  onClick={() => {
                    if (selectedSourceIds.length > 0) {
                      handleStartDigest(selectedSourceIds[0])
                    }
                  }}
                  disabled={selectedSourceIds.length === 0}
                />

                {/* Task Status Display */}
                {(pendingTask || Object.values(debateTasks).some(t => t.status === 'processing') ||
                  Object.values(directorTasks).some(t => t.status === 'processing') ||
                  Object.values(supercutTasks).some(t => t.status === 'processing') ||
                  digestTask?.status === 'processing') && (
                  <div className="mt-4 p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl">
                    <p className="text-xs text-zinc-400 mb-2">Processing Tasks</p>
                    <div className="space-y-2">
                      {pendingTask && (
                        <div className="flex items-center gap-2 text-xs">
                          <Loader2 className="w-3 h-3 animate-spin text-violet-400" />
                          <span className="text-zinc-300">{pendingTask.type} generation in progress...</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'conflicts' && (
              <div className="space-y-3">
                {conflicts.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-8">No conflicts detected</p>
                ) : (
                  conflicts.map((conflict) => {
                    const debateTask = debateTasks[conflict.id]
                    const directorTask = directorTasks[conflict.id]

                    return (
                      <div key={conflict.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                        <h3 className="text-sm font-medium text-zinc-200 mb-3">{conflict.topic}</h3>
                        <div className="space-y-2">
                          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                            <p className="text-xs text-red-400 mb-1">Viewpoint A</p>
                            <p className="text-sm text-zinc-300">{conflict.viewpoint_a.description}</p>
                          </div>
                          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                            <p className="text-xs text-blue-400 mb-1">Viewpoint B</p>
                            <p className="text-sm text-zinc-300">{conflict.viewpoint_b.description}</p>
                          </div>
                          <div className="bg-zinc-800 rounded-lg p-3">
                            <p className="text-xs text-zinc-400 mb-1">AI Verdict</p>
                            <p className="text-sm text-zinc-300">{conflict.verdict}</p>
                          </div>
                        </div>

                        {/* Creative Zone */}
                        <div className="mt-3 pt-3 border-t border-zinc-800">
                          <p className="text-xs text-zinc-500 mb-3">Creative Generation</p>

                          <div className="grid grid-cols-2 gap-3">
                            {/* Classic Mode */}
                            <div>
                              <p className="text-[10px] text-zinc-500 mb-1.5">⚡ Classic Mode</p>
                              {debateTask?.status === 'completed' ? (
                                <button
                                  onClick={() => debateTask.video_url && setActivePlayer('debate')}
                                  className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-xs text-emerald-400 hover:bg-emerald-500/30 transition-colors"
                                >
                                  <Play className="w-3 h-3" />
                                  <span>Play Debate</span>
                                </button>
                              ) : debateTask?.status === 'processing' ? (
                                <div className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                                  <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
                                  <span className="text-xs text-blue-400">Generating...</span>
                                </div>
                              ) : (
                                <button
                                  onClick={() => handleStartDebate(conflict.id, conflict)}
                                  className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-violet-500/20 border border-violet-500/30 rounded-lg text-xs text-violet-400 hover:bg-violet-500/30 transition-colors"
                                >
                                  <Video className="w-3 h-3" />
                                  <span>Split-Screen Debate</span>
                                </button>
                              )}
                            </div>

                            {/* Director Mode */}
                            <div>
                              <p className="text-[10px] text-zinc-500 mb-1.5">🎬 Director Mode</p>

                              {/* Persona Selector */}
                              <div className="flex items-center justify-center gap-1.5 mb-2">
                                {[
                                  { id: 'hajimi' as const, icon: '🐱', name: 'Hajimi' },
                                  { id: 'wukong' as const, icon: '🐵', name: 'Wukong' },
                                  { id: 'pro' as const, icon: '🎙️', name: 'Pro' }
                                ].map((persona) => (
                                  <button
                                    key={persona.id}
                                    onClick={() => setSelectedPersona(persona.id)}
                                    className={cn(
                                      "w-10 h-10 rounded-full flex items-center justify-center text-lg transition-all border-2",
                                      selectedPersona === persona.id
                                        ? "bg-violet-500/30 border-violet-500 scale-110"
                                        : "bg-zinc-800 border-zinc-700 hover:border-zinc-600"
                                    )}
                                    title={persona.name}
                                  >
                                    {persona.icon}
                                  </button>
                                ))}
                              </div>

                              {directorTask?.status === 'completed' ? (
                                <button
                                  onClick={() => directorTask.video_url && setActivePlayer('director')}
                                  className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-xs text-emerald-400 hover:bg-emerald-500/30 transition-colors"
                                >
                                  <Play className="w-3 h-3" />
                                  <span>Play Director</span>
                                </button>
                              ) : directorTask?.status === 'processing' ? (
                                <div className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                                  <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
                                  <span className="text-xs text-blue-400">Directing...</span>
                                </div>
                              ) : (
                                <button
                                  onClick={() => handleStartDirector(conflict.id, conflict)}
                                  className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-orange-500/20 border border-orange-500/30 rounded-lg text-xs text-orange-400 hover:bg-orange-500/30 transition-colors"
                                >
                                  <Sparkles className="w-3 h-3" />
                                  <span>AI Director Cut</span>
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            )}

            {activeTab === 'graph' && (
              <div className="h-full min-h-[400px] relative">
                {graph.nodes.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-8">No graph data</p>
                ) : (
                  <ReactECharts
                    option={{
                      series: [{
                        type: 'graph',
                        layout: 'force',
                        data: graph.nodes.map(n => ({ name: n.name, category: n.category, id: n.id })),
                        links: graph.links,
                        categories: [
                          { name: 'boss' },
                          { name: 'item' },
                          { name: 'location' },
                          { name: 'character' }
                        ],
                        roam: true,
                        label: { show: true, position: 'right', color: '#fff' },
                        force: { repulsion: 1500, edgeLength: [100, 300], gravity: 0.1 },
                        lineStyle: { color: '#3f3f46', width: 1 }
                      }],
                      backgroundColor: 'transparent'
                    }}
                    style={{ height: '100%', width: '100%' }}
                    onEvents={{
                      click: (params: any) => {
                        if (params.componentType === 'series' && params.dataType === 'node') {
                          const nodeName = params.data.name
                          const node = graph.nodes.find(n => n.name === nodeName)
                          if (node) {
                            const rect = (params.event as any).event
                            openEntityCard(node, { x: rect.offsetX, y: rect.offsetY })
                            fetchEntityStats(nodeName)
                          }
                        }
                      }
                    }}
                  />
                )}

                {/* Entity Card Popover */}
                {entityCard.isOpen && entityCard.entity && (
                  <div
                    className="absolute bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl p-4 min-w-[280px] z-20"
                    style={{
                      left: Math.min(entityCard.position.x, 350),
                      top: Math.min(entityCard.position.y, 200),
                    }}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="text-sm font-bold text-zinc-100">{entityCard.entity.name}</h4>
                        <p className="text-[10px] text-zinc-500 uppercase">{entityCard.entity.category}</p>
                      </div>
                      <button
                        onClick={() => closeEntityCard()}
                        className="p-1 hover:bg-zinc-800 rounded-lg transition-colors"
                      >
                        <X className="w-4 h-4 text-zinc-500" />
                      </button>
                    </div>

                    {entityCard.stats ? (
                      <div className="space-y-2 mb-3">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-zinc-400">Found in</span>
                          <span className="text-zinc-200 font-medium">{entityCard.stats.video_count} videos</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-zinc-400">Occurrences</span>
                          <span className="text-zinc-200 font-medium">{entityCard.stats.occurrence_count} times</span>
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs text-zinc-500 mb-3">Loading stats...</div>
                    )}

                    <button
                      onClick={() => {
                        handleStartSupercut(entityCard.entity!.name)
                      }}
                      disabled={entityCard.task?.status === 'processing'}
                      className={cn(
                        "w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all",
                        entityCard.task?.status === 'completed'
                          ? "bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/30"
                          : entityCard.task?.status === 'processing'
                          ? "bg-blue-500/10 border border-blue-500/20 text-blue-400"
                          : "bg-blue-500/20 border border-blue-500/30 text-blue-400 hover:bg-blue-500/30"
                      )}
                    >
                      {entityCard.task?.status === 'completed' ? (
                        <>
                          <Play className="w-3 h-3" />
                          <span>Play Supercut</span>
                        </>
                      ) : entityCard.task?.status === 'processing' ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          <span>Generating...</span>
                        </>
                      ) : (
                        <>
                          <Scissors className="w-3 h-3" />
                          <span>Generate Entity Supercut</span>
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'timeline' && (
              <div className="space-y-3">
                {timeline.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-8">No timeline data</p>
                ) : (
                  <>
                    {/* Event Type Filter */}
                    <div className="sticky top-0 bg-[#09090b] z-10 pb-3 border-b border-zinc-800/50">
                      <p className="text-[10px] text-zinc-500 mb-2">Filter by event type:</p>
                      <div className="flex items-center gap-2 flex-wrap">
                        {[
                          { type: 'STORY' as const, icon: '📖', label: 'Story', color: 'accent-amber-500' },
                          { type: 'COMBAT' as const, icon: '⚔️', label: 'Combat', color: 'accent-red-500' },
                          { type: 'EXPLORE' as const, icon: '🏃', label: 'Explore', color: 'accent-zinc-500' }
                        ].map((filter) => (
                          <label key={filter.type} className={cn(
                            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg border cursor-pointer transition-all",
                            digestIncludeTypes.includes(filter.type)
                              ? "bg-zinc-800 border-zinc-700"
                              : "bg-transparent border-zinc-800/50 opacity-60 hover:opacity-100"
                          )}>
                            <input
                              type="checkbox"
                              checked={digestIncludeTypes.includes(filter.type)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setDigestIncludeTypes([...digestIncludeTypes, filter.type])
                                } else {
                                  setDigestIncludeTypes(digestIncludeTypes.filter(t => t !== filter.type))
                                }
                              }}
                              className={cn("w-3 h-3 rounded", filter.color)}
                            />
                            <span className="text-sm">{filter.icon}</span>
                            <span className="text-xs text-zinc-300">{filter.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Filtered Events */}
                    <div className="space-y-3">
                      {timeline
                        .filter(event => digestIncludeTypes.includes(event.event_type))
                        .map((event) => (
                          <div key={event.id} className="flex gap-3">
                            <div className="flex flex-col items-center">
                              <div className={cn(
                                "w-3 h-3 rounded-full",
                                event.event_type === 'STORY' && "bg-amber-500",
                                event.event_type === 'COMBAT' && "bg-red-500",
                                event.event_type === 'EXPLORE' && "bg-zinc-500"
                              )} />
                              <div className="w-px h-full bg-zinc-800" />
                            </div>
                            <div className="flex-1 pb-4">
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-zinc-500">{event.time}</span>
                                <span className={cn(
                                  "text-[10px] px-1.5 py-0.5 rounded-full",
                                  event.event_type === 'STORY' && "bg-amber-500/20 text-amber-400",
                                  event.event_type === 'COMBAT' && "bg-red-500/20 text-red-400",
                                  event.event_type === 'EXPLORE' && "bg-zinc-500/20 text-zinc-400"
                                )}>
                                  {event.event_type}
                                </span>
                              </div>
                              <h4 className="text-sm font-medium text-zinc-200 mt-1">{event.title}</h4>
                              <p className="text-xs text-zinc-400 mt-1">{event.description}</p>
                            </div>
                          </div>
                        ))
                      }
                      {timeline.filter(event => digestIncludeTypes.includes(event.event_type)).length === 0 && (
                        <p className="text-sm text-zinc-500 text-center py-8">
                          No events match the selected filters
                        </p>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}

            {activeTab === 'report' && (
              <div className="text-center text-zinc-500 py-8">
                <p className="text-sm">Report feature coming soon</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
