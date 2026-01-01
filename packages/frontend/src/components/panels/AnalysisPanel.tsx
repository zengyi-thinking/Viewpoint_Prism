import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAppStore } from '@/stores/app-store'
import { Zap, Network, Clock, FileText, Loader2, Video, Users, Scissors, Sparkles, CheckCircle, XCircle, Play, Download, MonitorSpeaker } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactECharts from 'echarts-for-react'
import { FeatureCard } from '@/components/ui/FeatureCard'
import { KnowledgeGraphComponent, GraphNodeCard } from '@/components/ui/knowledge-graph'
import { ProgressBar, RippleButton } from '@/components/ui/feedback'

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
    debateTasks,
    directorTasks,
    supercutTasks,
    digestTask,
    networkSearchTask,
    selectedPersona,
    digestIncludeTypes,
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
    fetchEntityStats,
    startDigestGeneration,
    pollDigestTask,
    setDigestTask,
    setDigestIncludeTypes,
    setActivePlayer,
    entityCard
  } = useAppStore()

  const [pendingTask, setPendingTask] = useState(null)

  const handleStartDebate = async (conflictId, conflict) => {
    const taskId = await startDebateGeneration(conflictId, conflict)
    if (taskId) {
      setPendingTask({ type: "debate", id: conflictId })
      setDebateTask(conflictId, { status: "pending", progress: 0, task_id: taskId })
    }
  }

  const handleStartDirector = async (conflictId, conflict) => {
    const taskId = await startDirectorGeneration(conflictId, conflict, selectedPersona)
    if (taskId) {
      setPendingTask({ type: "director", id: conflictId })
      setDirectorTask(conflictId, { status: "pending", progress: 0, task_id: taskId })
    }
  }

  const handleStartSupercut = async (entityName) => {
    const taskId = await startSupercutGeneration(entityName)
    if (taskId) {
      setPendingTask({ type: "supercut", id: entityName })
      setSupercutTask(entityName, { status: "pending", progress: 0, task_id: taskId })
    }
  }

  const handleStartDigest = async (sourceId) => {
    const taskId = await startDigestGeneration(sourceId)
    if (taskId) {
      setPendingTask({ type: "digest", id: sourceId })
      setDigestTask({ status: "pending", progress: 0, task_id: taskId })
    }
  }

  const tabs = [
    { id: "studio" as const, icon: Zap, label: "Studio" },
    { id: "conflicts" as const, icon: Network, label: "Conflicts" },
    { id: "graph" as const, icon: Network, label: "Graph" },
    { id: "timeline" as const, icon: Clock, label: "Timeline" },
    { id: "report" as const, icon: FileText, label: "Report" },
  ]

  return (
    <div className="h-full flex flex-col bg-[#09090b]">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-4 py-3 border-b border-zinc-800/50"
      >
        <h2 className="text-sm font-semibold text-zinc-100 mb-3">Analysis</h2>

        {/* Tabs */}
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <motion.button
              key={tab.id}
              whileTap={{ scale: 0.95 }}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all relative",
                activeTab === tab.id
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              )}
            >
              <tab.icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              {activeTab === tab.id && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-zinc-700 rounded-lg -z-10"
                />
              )}
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {selectedSourceIds.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center text-zinc-500 py-8"
          >
            <p className="text-sm">Select sources to analyze</p>
            <p className="text-xs mt-1">Choose at least one video from the Sources panel</p>
          </motion.div>
        ) : isAnalyzing ? (
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-violet-500 mb-3" />
            <p className="text-sm text-zinc-400">Analyzing videos...</p>
          </div>
        ) : (
          <>
            {activeTab === "studio" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-4"
              >
                <p className="text-xs text-zinc-500 text-center mb-4">
                  AI-powered creative video generation tools
                </p>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  <FeatureCard
                    title="AI Debate Video"
                    icon={Video}
                    description={language === "zh" ? "生成观点碰撞的辩论视频" : "Generate split-screen debate videos from conflicting viewpoints"}
                    color="bg-gradient-to-br from-red-500 to-orange-500"
                    glowColor="bg-gradient-to-br from-red-500/20 to-orange-500/20"
                    onClick={() => {
                      if (conflicts.length > 0) {
                        handleStartDebate(conflicts[0].id, conflicts[0])
                      }
                    }}
                    disabled={conflicts.length === 0}
                  />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 }}
                >
                  <FeatureCard
                    title="AI Director Cut"
                    icon={Sparkles}
                    description={language === "zh" ? "AI导演剪辑，多人设解说" : "AI-narrated director cuts with multiple personas"}
                    color="bg-gradient-to-br from-violet-500 to-purple-500"
                    glowColor="bg-gradient-to-br from-violet-500/20 to-purple-500/20"
                    onClick={() => {
                      if (conflicts.length > 0) {
                        handleStartDirector(conflicts[0].id, conflicts[0])
                      }
                    }}
                    disabled={conflicts.length === 0}
                  />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  <FeatureCard
                    title="Entity Supercut"
                    icon={Scissors}
                    description={language === "zh" ? "基于知识图谱的实体混剪" : "Auto-generate supercuts from knowledge graph entities"}
                    color="bg-gradient-to-br from-blue-500 to-cyan-500"
                    glowColor="bg-gradient-to-br from-blue-500/20 to-cyan-500/20"
                    onClick={() => {
                      if (graph.nodes.length > 0) {
                        handleStartSupercut(graph.nodes[0].name)
                      }
                    }}
                    disabled={graph.nodes.length === 0}
                  />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25 }}
                >
                  <FeatureCard
                    title="Smart Digest"
                    icon={Clock}
                    description={language === "zh" ? "基于时间轴的智能浓缩" : "浓缩高价值片段的精简版视频"}
                    color="bg-gradient-to-br from-emerald-500 to-teal-500"
                    glowColor="bg-gradient-to-br from-emerald-500/20 to-teal-500/20"
                    onClick={() => {
                      if (selectedSourceIds.length > 0) {
                        handleStartDigest(selectedSourceIds[0])
                      }
                    }}
                    disabled={selectedSourceIds.length === 0}
                  />
                </motion.div>
              </motion.div>
            )}

            {activeTab === "conflicts" && (
              <div className="space-y-3">
                {conflicts.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-8">No conflicts detected</p>
                ) : (
                  conflicts.map((conflict, index) => {
                    const debateTask = debateTasks[conflict.id]
                    const directorTask = directorTasks[conflict.id]

                    return (
                      <motion.div
                        key={conflict.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="bg-zinc-900 border border-zinc-800 rounded-xl p-4"
                      >
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

                        <div className="mt-3 pt-3 border-t border-zinc-800">
                          <p className="text-xs text-zinc-500 mb-3">Creative Generation</p>

                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <p className="text-[10px] text-zinc-500 mb-1.5">⚡ Classic Mode</p>
                              {debateTask?.status === "completed" ? (
                                <RippleButton
                                  onClick={() => debateTask.video_url && setActivePlayer("debate")}
                                  className="w-full"
                                >
                                  <Play className="w-3 h-3" />
                                  <span>Play Debate</span>
                                </RippleButton>
                              ) : debateTask?.status === "processing" ? (
                                <div className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                                  <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
                                  <span className="text-xs text-blue-400">Generating...</span>
                                </div>
                              ) : (
                                <RippleButton
                                  onClick={() => handleStartDebate(conflict.id, conflict)}
                                  variant="secondary"
                                  className="w-full"
                                >
                                  <Video className="w-3 h-3" />
                                  <span>Split-Screen Debate</span>
                                </RippleButton>
                              )}
                            </div>

                            <div>
                              <p className="text-[10px] text-zinc-500 mb-1.5">🎬 Director Mode</p>

                              <div className="flex items-center justify-center gap-1.5 mb-2">
                                {[
                                  { id: "hajimi" as const, icon: "🐱", name: "Hajimi" },
                                  { id: "wukong" as const, icon: "🐵", name: "Wukong" },
                                  { id: "pro" as const, icon: "🎙️", name: "Pro" }
                                ].map((persona) => (
                                  <motion.button
                                    key={persona.id}
                                    whileTap={{ scale: 0.9 }}
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
                                  </motion.button>
                                ))}
                              </div>

                              {directorTask?.status === "completed" ? (
                                <RippleButton
                                  onClick={() => directorTask.video_url && setActivePlayer("director")}
                                  className="w-full"
                                >
                                  <Play className="w-3 h-3" />
                                  <span>Play Director</span>
                                </RippleButton>
                              ) : directorTask?.status === "processing" ? (
                                <div className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                                  <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
                                  <span className="text-xs text-blue-400">Directing...</span>
                                </div>
                              ) : (
                                <RippleButton
                                  onClick={() => handleStartDirector(conflict.id, conflict)}
                                  variant="secondary"
                                  className="w-full"
                                >
                                  <MonitorSpeaker className="w-3 h-3" />
                                  <span>AI Director Cut</span>
                                </RippleButton>
                              )}
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )
                  })
                )}
              </div>
            )}

            {activeTab === "graph" && (
              <div className="h-full min-h-[400px] relative">
                {graph.nodes.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-8">No graph data</p>
                ) : (
                  <KnowledgeGraphComponent
                    graph={graph}
                    onNodeClick={(node, position) => {
                      openEntityCard(node, position)
                      fetchEntityStats(node.name)
                    }}
                    className="h-full"
                  />
                )}

                <AnimatePresence>
                  {entityCard.isOpen && entityCard.entity && (
                    <GraphNodeCard
                      node={entityCard.entity}
                      stats={entityCard.stats}
                      onClose={closeEntityCard}
                      onGenerateSupercut={() => {
                        handleStartSupercut(entityCard.entity!.name)
                      }}
                      taskStatus={entityCard.task?.status}
                      position={entityCard.position}
                    />
                  )}
                </AnimatePresence>
              </div>
            )}

            {activeTab === "timeline" && (
              <div className="space-y-3">
                {timeline.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-8">No timeline data</p>
                ) : (
                  <>
                    <div className="sticky top-0 bg-[#09090b] z-10 pb-3 border-b border-zinc-800/50">
                      <p className="text-[10px] text-zinc-500 mb-2">Filter by event type:</p>
                      <div className="flex items-center gap-2 flex-wrap">
                        {[
                          { type: "STORY" as const, icon: "📖", label: "Story", color: "accent-amber-500" },
                          { type: "COMBAT" as const, icon: "⚔️", label: "Combat", color: "accent-red-500" },
                          { type: "EXPLORE" as const, icon: "🏃", label: "Explore", color: "accent-zinc-500" }
                        ].map((filter) => (
                          <motion.label
                            key={filter.type}
                            whileTap={{ scale: 0.95 }}
                            className={cn(
                              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg border cursor-pointer transition-all",
                              digestIncludeTypes.includes(filter.type)
                                ? "bg-zinc-800 border-zinc-700"
                                : "bg-transparent border-zinc-800/50 opacity-60 hover:opacity-100"
                            )}
                          >
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
                          </motion.label>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-3">
                      {timeline
                        .filter(event => digestIncludeTypes.includes(event.event_type))
                        .map((event, index) => (
                          <motion.div
                            key={event.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="flex gap-3"
                          >
                            <div className="flex flex-col items-center">
                              <div className={cn(
                                "w-3 h-3 rounded-full",
                                event.event_type === "STORY" && "bg-amber-500",
                                event.event_type === "COMBAT" && "bg-red-500",
                                event.event_type === "EXPLORE" && "bg-zinc-500"
                              )} />
                              <div className="w-px h-full bg-zinc-800" />
                            </div>
                            <div className="flex-1 pb-4">
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-zinc-500">{event.time}</span>
                                <span className={cn(
                                  "text-[10px] px-1.5 py-0.5 rounded-full",
                                  event.event_type === "STORY" && "bg-amber-500/20 text-amber-400",
                                  event.event_type === "COMBAT" && "bg-red-500/20 text-red-400",
                                  event.event_type === "EXPLORE" && "bg-zinc-500/20 text-zinc-400"
                                )}>
                                  {event.event_type}
                                </span>
                              </div>
                              <h4 className="text-sm font-medium text-zinc-200 mt-1">{event.title}</h4>
                              <p className="text-xs text-zinc-400 mt-1">{event.description}</p>
                            </div>
                          </motion.div>
                        ))}
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

            {activeTab === "report" && (
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
