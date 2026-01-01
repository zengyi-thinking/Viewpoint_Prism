import { useEffect, useRef, useState, useCallback } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Zap, GitBranch, Clock, AlertTriangle, Sparkles, RefreshCw, Loader2, Film, Download, Play, Pause, X, Video, BookOpen, Swords, Footprints, Check, Clapperboard, ArrowLeft, FileText, Network, Scissors, Image, Expand, Grid3X3 } from 'lucide-react'
import { cn } from '@/lib/utils'
import * as echarts from 'echarts'
import type { AnalysisTab, Conflict, DebateTask, GraphNode, DirectorTask, Persona, StoryboardFrame } from '@/types'
import { FeatureCard } from '@/components/ui/FeatureCard'
import { OnePager } from '@/components/ui/OnePager'

// Persona configurations for UI
const PERSONAS: Array<{ id: Persona; name: string; emoji: string; description: string }> = [
  { id: 'hajimi', name: '哈基米', emoji: '🐱', description: '可爱猫娘，活泼激萌' },
  { id: 'wukong', name: '大圣', emoji: '🐵', description: '齐天大圣，狂傲不羁' },
  { id: 'pro', name: '专业', emoji: '🎙️', description: '专业分析，冷静客观' },
]

// Conflicts View
function ConflictsView() {
  const {
    conflicts,
    language,
    seekTo,
    debateTasks,
    startDebateGeneration,
    pollDebateTask,
    setDebateTask,
    directorTasks,
    selectedPersona,
    setSelectedPersona,
    startDirectorGeneration,
    pollDirectorTask,
    setDirectorTask,
  } = useAppStore()

  const t = {
    zh: {
      critical: '核心分歧',
      warning: '注意',
      info: '信息',
      generateDebate: '⚡ 快速分屏',
      generateDirector: '🎬 AI导演',
      generating: '生成中...',
      download: '下载到本地',
      save: '保存到资源库',
      retry: '重试',
      noConflicts: '请先点击右上角"生成分析"按钮',
      classicMode: '快速对比',
      directorMode: 'AI导演精剪',
      selectPersona: '选择解说风格',
    },
    en: {
      critical: 'CRITICAL',
      warning: 'WARNING',
      info: 'INFO',
      generateDebate: '⚡ Quick Split',
      generateDirector: '🎬 AI Director',
      generating: 'Generating...',
      download: 'Download',
      save: 'Save to Library',
      retry: 'Retry',
      noConflicts: 'Click "Generate" button in top-right first',
      classicMode: 'Quick Compare',
      directorMode: 'AI Director Cut',
      selectPersona: 'Select narrator style',
    },
  }

  return (
    <div className="absolute inset-0 overflow-y-auto scroller p-5 space-y-5 fade-in">
      {conflicts.map((conflict) => (
        <ConflictCard
          key={conflict.id}
          conflict={conflict}
          language={language}
          t={t}
          seekTo={seekTo}
          debateTask={debateTasks[conflict.id]}
          directorTask={directorTasks[conflict.id]}
          selectedPersona={selectedPersona}
          onPersonaChange={setSelectedPersona}
          onGenerateDebate={async () => {
            const taskId = await startDebateGeneration(conflict.id, conflict)
            if (taskId) {
              const poll = async () => {
                const result = await pollDebateTask(taskId)
                if (result) {
                  setDebateTask(conflict.id, result)
                  if (result.status !== 'completed' && result.status !== 'error') {
                    setTimeout(poll, 2000)
                  }
                }
              }
              poll()
            }
          }}
          onGenerateDirector={async (persona: Persona) => {
            const taskId = await startDirectorGeneration(conflict.id, conflict, persona)
            if (taskId) {
              const poll = async () => {
                const result = await pollDirectorTask(taskId)
                if (result) {
                  setDirectorTask(conflict.id, result)
                  if (result.status !== 'completed' && result.status !== 'error') {
                    setTimeout(poll, 2000)
                  }
                }
              }
              poll()
            }
          }}
        />
      ))}
    </div>
  )
}

// Conflict Card with Dual Mode Creative Zone
interface ConflictCardProps {
  conflict: Conflict
  language: 'zh' | 'en'
  t: Record<string, Record<string, string>>
  seekTo: (sourceId: string, time: number) => void
  debateTask?: DebateTask
  directorTask?: DirectorTask
  selectedPersona: Persona
  onPersonaChange: (persona: Persona) => void
  onGenerateDebate: () => void
  onGenerateDirector: (persona: Persona) => void
}

function ConflictCard({
  conflict,
  language,
  t,
  seekTo,
  debateTask,
  directorTask,
  selectedPersona,
  onPersonaChange,
  onGenerateDebate,
  onGenerateDirector,
}: ConflictCardProps) {
  const debateVideoRef = useRef<HTMLVideoElement>(null)
  const directorVideoRef = useRef<HTMLVideoElement>(null)
  const [isDebateVideoPlaying, setIsDebateVideoPlaying] = useState(false)
  const [isDirectorVideoPlaying, setIsDirectorVideoPlaying] = useState(false)
  const [activeMode, setActiveMode] = useState<'classic' | 'director'>('director')
  const { activePlayer, setActivePlayer } = useAppStore()

  // Pause video when another player becomes active
  useEffect(() => {
    if (activePlayer !== 'debate' && isDebateVideoPlaying && debateVideoRef.current) {
      debateVideoRef.current.pause()
      setIsDebateVideoPlaying(false)
    }
    if (activePlayer !== 'director' && isDirectorVideoPlaying && directorVideoRef.current) {
      directorVideoRef.current.pause()
      setIsDirectorVideoPlaying(false)
    }
  }, [activePlayer, isDebateVideoPlaying, isDirectorVideoPlaying])

  const handleDebateDownload = useCallback(() => {
    if (debateTask?.video_url) {
      const link = document.createElement('a')
      link.href = `http://localhost:8000${debateTask.video_url}`
      link.download = `debate_${conflict.id}.mp4`
      link.click()
    }
  }, [debateTask?.video_url, conflict.id])

  const handleDirectorDownload = useCallback(() => {
    if (directorTask?.video_url) {
      const link = document.createElement('a')
      link.href = `http://localhost:8000${directorTask.video_url}`
      link.download = `director_${conflict.id}.mp4`
      link.click()
    }
  }, [directorTask?.video_url, conflict.id])

  const toggleDebateVideo = useCallback(() => {
    if (debateVideoRef.current) {
      if (isDebateVideoPlaying) {
        debateVideoRef.current.pause()
        setIsDebateVideoPlaying(false)
      } else {
        setActivePlayer('debate')
        debateVideoRef.current.play()
        setIsDebateVideoPlaying(true)
      }
    }
  }, [isDebateVideoPlaying, setActivePlayer])

  const toggleDirectorVideo = useCallback(() => {
    if (directorVideoRef.current) {
      if (isDirectorVideoPlaying) {
        directorVideoRef.current.pause()
        setIsDirectorVideoPlaying(false)
      } else {
        setActivePlayer('director' as any)
        directorVideoRef.current.play()
        setIsDirectorVideoPlaying(true)
      }
    }
  }, [isDirectorVideoPlaying, setActivePlayer])

  const isDebateGenerating = debateTask && !['completed', 'error'].includes(debateTask.status) && debateTask.status !== undefined
  const isDirectorGenerating = directorTask && !['completed', 'error'].includes(directorTask.status) && directorTask.status !== undefined

  return (
    <div
      className="bg-[#18181b] border border-zinc-800/80 rounded-2xl overflow-hidden group hover:border-zinc-700 transition-all shadow-sm hover:shadow-md"
    >
      {/* Header */}
      <div className="p-4 border-b border-zinc-800/50 flex justify-between items-center bg-[#1c1c1f]">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <span className="text-sm font-bold text-gray-200">{conflict.topic}</span>
        </div>
        <span
          className={cn(
            'text-[10px] px-2.5 py-1 rounded-full border font-bold tracking-wider shadow-sm',
            conflict.severity === 'critical' &&
              'bg-red-500/10 text-red-400 border-red-500/20',
            conflict.severity === 'warning' &&
              'bg-amber-500/10 text-amber-400 border-amber-500/20',
            conflict.severity === 'info' &&
              'bg-blue-500/10 text-blue-400 border-blue-500/20'
          )}
        >
          {t[language][conflict.severity]}
        </span>
      </div>

      {/* Viewpoints */}
      <div className="flex">
        {/* Viewpoint A */}
        <div
          onClick={() =>
            conflict.viewpoint_a.timestamp !== null &&
            seekTo(conflict.viewpoint_a.source_id, conflict.viewpoint_a.timestamp)
          }
          className="flex-1 p-5 border-r border-zinc-800/50 hover:bg-red-500/5 transition-colors cursor-pointer relative overflow-hidden group/a"
        >
          <div className="absolute top-0 right-0 w-12 h-12 bg-gradient-to-bl from-red-500/10 to-transparent opacity-50 group-hover/a:opacity-100 transition-opacity" />
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-bold text-red-400 bg-red-500/10 px-2 py-1 rounded-full border border-red-500/20 shadow-sm">
              {conflict.viewpoint_a.source_name}
            </span>
          </div>
          <div className="text-base text-gray-100 font-bold mb-2">
            {conflict.viewpoint_a.title}
          </div>
          <p className="text-xs text-zinc-500 leading-relaxed">
            {conflict.viewpoint_a.description}
          </p>
        </div>

        {/* Viewpoint B */}
        <div
          onClick={() =>
            conflict.viewpoint_b.timestamp !== null &&
            seekTo(conflict.viewpoint_b.source_id, conflict.viewpoint_b.timestamp)
          }
          className="flex-1 p-5 hover:bg-blue-500/5 transition-colors cursor-pointer relative overflow-hidden group/b"
        >
          <div className="absolute top-0 right-0 w-12 h-12 bg-gradient-to-bl from-blue-500/10 to-transparent opacity-50 group-hover/b:opacity-100 transition-opacity" />
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-2 py-1 rounded-full border border-blue-500/20 shadow-sm">
              {conflict.viewpoint_b.source_name}
            </span>
          </div>
          <div className="text-base text-gray-100 font-bold mb-2">
            {conflict.viewpoint_b.title}
          </div>
          <p className="text-xs text-zinc-500 leading-relaxed">
            {conflict.viewpoint_b.description}
          </p>
        </div>
      </div>

      {/* AI Verdict */}
      <div className="p-4 bg-[#151518] border-t border-zinc-800/50 flex gap-3 items-start">
        <div className="w-6 h-6 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0 border border-blue-500/20 shadow-sm">
          <Sparkles className="w-3 h-3 text-blue-400" />
        </div>
        <p className="text-xs text-zinc-400 leading-relaxed pt-0.5">
          {conflict.verdict}
        </p>
      </div>

      {/* Dual Mode Creative Zone */}
      <div className="p-4 bg-[#0f0f11] border-t border-zinc-800/50">
        {/* Mode Tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveMode('classic')}
            className={cn(
              'flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-2',
              activeMode === 'classic'
                ? 'bg-zinc-700 text-white border border-zinc-600'
                : 'bg-zinc-800/50 text-zinc-400 border border-zinc-800 hover:border-zinc-700'
            )}
          >
            <Zap className="w-3 h-3" />
            {t[language].classicMode}
          </button>
          <button
            onClick={() => setActiveMode('director')}
            className={cn(
              'flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-2',
              activeMode === 'director'
                ? 'bg-gradient-to-r from-blue-600/30 to-cyan-600/30 text-blue-300 border border-blue-500/30'
                : 'bg-zinc-800/50 text-zinc-400 border border-zinc-800 hover:border-zinc-700'
            )}
          >
            <Clapperboard className="w-3 h-3" />
            {t[language].directorMode}
          </button>
        </div>

        {/* Classic Mode */}
        {activeMode === 'classic' && (
          <div className="space-y-4">
            {/* Generate Button */}
            {!debateTask && (
              <button
                onClick={onGenerateDebate}
                className="w-full py-3 px-4 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-xl text-sm font-medium text-zinc-300 flex items-center justify-center gap-2 transition-all"
              >
                <Film className="w-4 h-4" />
                {t[language].generateDebate}
              </button>
            )}

            {/* Generating Progress */}
            {isDebateGenerating && (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-4 h-4 text-zinc-400 animate-spin" />
                  <span className="text-sm text-zinc-300">{debateTask.message}</span>
                </div>
                <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full bg-zinc-500 transition-all duration-500"
                    style={{ width: `${debateTask.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Error State */}
            {debateTask?.status === 'error' && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-red-400">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-sm">{debateTask.message}</span>
                </div>
                <button
                  onClick={onGenerateDebate}
                  className="w-full py-2 px-4 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-sm text-red-300 transition-all"
                >
                  {t[language].retry}
                </button>
              </div>
            )}

            {/* Completed: Mini Player */}
            {debateTask?.status === 'completed' && debateTask.video_url && (
              <div className="space-y-3">
                {debateTask.script && (
                  <div className="p-3 bg-zinc-900/50 rounded-lg border border-zinc-800/50">
                    <p className="text-xs text-zinc-400 italic">"{debateTask.script}"</p>
                  </div>
                )}
                <div className="relative rounded-xl overflow-hidden bg-black aspect-video group/player">
                  <video
                    ref={debateVideoRef}
                    src={`http://localhost:8000${debateTask.video_url}`}
                    className="w-full h-full object-contain"
                    onEnded={() => setIsDebateVideoPlaying(false)}
                  />
                  <div
                    onClick={toggleDebateVideo}
                    className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover/player:opacity-100 transition-opacity cursor-pointer"
                  >
                    <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                      {isDebateVideoPlaying ? (
                        <Pause className="w-5 h-5 text-white" />
                      ) : (
                        <Play className="w-5 h-5 text-white ml-0.5" />
                      )}
                    </div>
                  </div>
                </div>
                <button
                  onClick={handleDebateDownload}
                  className="w-full py-2 px-4 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm text-zinc-300 flex items-center justify-center gap-2 transition-all"
                >
                  <Download className="w-4 h-4" />
                  {t[language].download}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Director Mode */}
        {activeMode === 'director' && (
          <div className="space-y-4">
            {/* Persona Selector */}
            {!directorTask && (
              <>
                <div className="text-[10px] text-zinc-500 mb-2">{t[language].selectPersona}</div>
                <div className="flex gap-2 mb-4">
                  {PERSONAS.map((persona) => (
                    <button
                      key={persona.id}
                      onClick={() => onPersonaChange(persona.id)}
                      className={cn(
                        'flex-1 py-3 px-2 rounded-xl text-center transition-all border',
                        selectedPersona === persona.id
                          ? 'bg-blue-500/20 border-blue-500/40 shadow-lg shadow-blue-500/10'
                          : 'bg-zinc-800/50 border-zinc-700/50 hover:border-zinc-600'
                      )}
                    >
                      <div className="text-2xl mb-1">{persona.emoji}</div>
                      <div className={cn(
                        'text-xs font-medium',
                        selectedPersona === persona.id ? 'text-blue-300' : 'text-zinc-400'
                      )}>
                        {persona.name}
                      </div>
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => onGenerateDirector(selectedPersona)}
                  className="w-full py-3 px-4 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 hover:from-blue-600/30 hover:to-cyan-600/30 border border-blue-500/30 rounded-xl text-sm font-medium text-blue-300 flex items-center justify-center gap-2 transition-all hover:shadow-lg hover:shadow-blue-500/10"
                >
                  <Clapperboard className="w-4 h-4" />
                  {t[language].generateDirector}
                </button>
              </>
            )}

            {/* Generating Progress */}
            {isDirectorGenerating && (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  <span className="text-sm text-blue-300">{directorTask.message}</span>
                </div>
                <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                    style={{ width: `${directorTask.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Error State */}
            {directorTask?.status === 'error' && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-red-400">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-sm">{directorTask.message}</span>
                </div>
                <button
                  onClick={() => onGenerateDirector(selectedPersona)}
                  className="w-full py-2 px-4 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-sm text-red-300 transition-all"
                >
                  {t[language].retry}
                </button>
              </div>
            )}

            {/* Completed: Mini Player */}
            {directorTask?.status === 'completed' && (
              <div className="space-y-3">
                {/* Director Info */}
                <div className="flex items-center gap-2 text-xs text-blue-300">
                  <span className="text-lg">{PERSONAS.find(p => p.id === directorTask.persona)?.emoji || '🎬'}</span>
                  <span>{directorTask.persona_name} 导演作品</span>
                  {directorTask.segment_count && (
                    <span className="text-zinc-500">• {directorTask.segment_count} 个片段</span>
                  )}
                </div>

                {/* Script Summary */}
                {directorTask.script && (
                  <div className="p-3 bg-zinc-900/50 rounded-lg border border-zinc-800/50">
                    <p className="text-[10px] text-zinc-500 mb-1">剧本结构</p>
                    <p className="text-xs text-zinc-400">{directorTask.script}</p>
                  </div>
                )}

                {/* Storyboard Frames - Phase 11 */}
                {directorTask.storyboard_frames && directorTask.storyboard_frames.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-purple-300">
                      <Grid3X3 className="w-3 h-3" />
                      <span>分镜脚本 ({directorTask.storyboard_frames.length} 帧)</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      {directorTask.storyboard_frames.map((frame) => (
                        <div
                          key={frame.frame_number}
                          className="relative group/frame rounded-lg overflow-hidden bg-zinc-900 border border-zinc-800 aspect-video"
                        >
                          <img
                            src={`http://localhost:8000${frame.image_url}`}
                            alt={`Frame ${frame.frame_number}`}
                            className="w-full h-full object-cover transition-transform group-hover/frame:scale-105"
                          />
                          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                          <div className="absolute bottom-0 left-0 right-0 p-2">
                            <div className="flex items-center gap-1 text-[10px] text-white/80">
                              <span className="bg-purple-500/30 px-1.5 py-0.5 rounded text-purple-300">
                                #{frame.frame_number}
                              </span>
                              <span className="truncate">{frame.narration}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Cover Image - Phase 11 */}
                {directorTask.cover_image && !directorTask.video_url && (
                  <div className="relative group/frame rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 aspect-video">
                    <img
                      src={`http://localhost:8000${directorTask.cover_image}`}
                      alt="Director cover"
                      className="w-full h-full object-cover transition-transform group-hover/frame:scale-105"
                    />
                    <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
                      <div className="text-center">
                        <Image className="w-8 h-8 text-white/80 mx-auto mb-2" />
                        <p className="text-sm text-white/80">{directorTask.persona_name} 导演封面</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Mini Video Player */}
                {directorTask.video_url && (
                  <div className="relative rounded-xl overflow-hidden bg-black aspect-video group/player">
                    <video
                      ref={directorVideoRef}
                      src={`http://localhost:8000${directorTask.video_url}`}
                      className="w-full h-full object-contain"
                      onEnded={() => setIsDirectorVideoPlaying(false)}
                    />
                    <div
                      onClick={toggleDirectorVideo}
                      className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover/player:opacity-100 transition-opacity cursor-pointer"
                    >
                      <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                        {isDirectorVideoPlaying ? (
                          <Pause className="w-5 h-5 text-white" />
                        ) : (
                          <Play className="w-5 h-5 text-white ml-0.5" />
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-2">
                  {directorTask.video_url && (
                    <button
                      onClick={handleDirectorDownload}
                      className="flex-1 py-2 px-4 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm text-zinc-300 flex items-center justify-center gap-2 transition-all"
                    >
                      <Download className="w-4 h-4" />
                      {t[language].download}
                    </button>
                  )}
                  <button
                    className="flex-1 py-2 px-4 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg text-sm text-blue-300 flex items-center justify-center gap-2 transition-all"
                  >
                    <Sparkles className="w-4 h-4" />
                    {t[language].save}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// Entity Card Popup Component
function EntityCard() {
  const {
    entityCard,
    closeEntityCard,
    fetchEntityStats,
    startSupercutGeneration,
    pollSupercutTask,
    setSupercutTask,
    language,
    activePlayer,
    setActivePlayer,
  } = useAppStore()

  const videoRef = useRef<HTMLVideoElement>(null)
  const [isVideoPlaying, setIsVideoPlaying] = useState(false)

  // Pause video when another player becomes active
  useEffect(() => {
    if (activePlayer !== 'supercut' && isVideoPlaying && videoRef.current) {
      videoRef.current.pause()
      setIsVideoPlaying(false)
    }
  }, [activePlayer, isVideoPlaying])

  const t = {
    zh: {
      foundIn: '出现在',
      videos: '个视频中',
      occurrences: '次提及',
      generateSupercut: '🎬 生成全网混剪',
      generating: '生成中...',
      download: '下载',
      retry: '重试',
      close: '关闭',
    },
    en: {
      foundIn: 'Found in',
      videos: 'videos',
      occurrences: 'occurrences',
      generateSupercut: '🎬 Generate Supercut',
      generating: 'Generating...',
      download: 'Download',
      retry: 'Retry',
      close: 'Close',
    },
  }

  // Fetch stats when entity changes
  useEffect(() => {
    if (entityCard.entity && entityCard.isOpen) {
      fetchEntityStats(entityCard.entity.name)
    }
  }, [entityCard.entity, entityCard.isOpen, fetchEntityStats])

  const handleGenerate = async () => {
    if (!entityCard.entity) return

    const taskId = await startSupercutGeneration(entityCard.entity.name)
    if (taskId) {
      const poll = async () => {
        const result = await pollSupercutTask(taskId)
        if (result) {
          setSupercutTask(entityCard.entity!.name, result)
          if (result.status !== 'completed' && result.status !== 'error') {
            setTimeout(poll, 2000)
          }
        }
      }
      poll()
    }
  }

  const handleDownload = useCallback(() => {
    if (entityCard.task?.video_url) {
      const link = document.createElement('a')
      link.href = `http://localhost:8000${entityCard.task.video_url}`
      link.download = `supercut_${entityCard.entity?.name || 'entity'}.mp4`
      link.click()
    }
  }, [entityCard.task?.video_url, entityCard.entity?.name])

  const toggleVideo = useCallback(() => {
    if (videoRef.current) {
      if (isVideoPlaying) {
        videoRef.current.pause()
        setIsVideoPlaying(false)
      } else {
        setActivePlayer('supercut')
        videoRef.current.play()
        setIsVideoPlaying(true)
      }
    }
  }, [isVideoPlaying, setActivePlayer])

  if (!entityCard.isOpen || !entityCard.entity) return null

  const { entity, stats, task, position } = entityCard
  const isGenerating = task && !['completed', 'error'].includes(task.status) && task.status !== undefined

  // Calculate popup position (keep it within viewport)
  const popupStyle = {
    left: Math.min(position.x, window.innerWidth - 320),
    top: Math.min(position.y, window.innerHeight - 400),
  }

  const categoryColors: Record<string, string> = {
    boss: 'text-red-400 bg-red-500/10 border-red-500/30',
    item: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
    location: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
    character: 'text-green-400 bg-green-500/10 border-green-500/30',
  }

  return (
    <div
      className="fixed z-50 w-80 bg-[#18181b] border border-zinc-700 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200"
      style={popupStyle}
    >
      {/* Header */}
      <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-[#1c1c1f]">
        <div className="flex items-center gap-3">
          <span className={cn(
            'text-[10px] px-2 py-1 rounded-full border font-bold',
            categoryColors[entity.category] || 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30'
          )}>
            {entity.category.toUpperCase()}
          </span>
          <h3 className="text-lg font-bold text-white">{entity.name}</h3>
        </div>
        <button
          onClick={closeEntityCard}
          className="p-1.5 hover:bg-zinc-700 rounded-lg transition-colors"
        >
          <X className="w-4 h-4 text-zinc-400" />
        </button>
      </div>

      {/* Stats */}
      <div className="p-4 border-b border-zinc-800/50">
        {stats ? (
          <p className="text-sm text-zinc-400">
            {t[language].foundIn} <span className="text-white font-bold">{stats.video_count}</span> {t[language].videos},{' '}
            <span className="text-white font-bold">{stats.occurrence_count}</span> {t[language].occurrences}
          </p>
        ) : (
          <div className="flex items-center gap-2 text-zinc-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Loading stats...</span>
          </div>
        )}
      </div>

      {/* Action Zone */}
      <div className="p-4">
        {/* Default: Generate Button */}
        {!task && (
          <button
            onClick={handleGenerate}
            disabled={!stats || stats.video_count === 0}
            className={cn(
              'w-full py-3 px-4 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-all',
              stats && stats.video_count > 0
                ? 'bg-gradient-to-r from-blue-600/20 to-cyan-600/20 hover:from-blue-600/30 hover:to-cyan-600/30 border border-blue-500/30 text-blue-300 hover:shadow-lg hover:shadow-blue-500/10'
                : 'bg-zinc-800/50 text-zinc-500 cursor-not-allowed'
            )}
          >
            <Video className="w-4 h-4" />
            {t[language].generateSupercut}
          </button>
        )}

        {/* Generating: Progress */}
        {isGenerating && (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
              <span className="text-sm text-blue-300">{task.message}</span>
            </div>
            <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                style={{ width: `${task.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error State */}
        {task?.status === 'error' && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm">{task.message}</span>
            </div>
            <button
              onClick={handleGenerate}
              className="w-full py-2 px-4 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-sm text-red-300 transition-all"
            >
              {t[language].retry}
            </button>
          </div>
        )}

        {/* Completed: Mini Player */}
        {task?.status === 'completed' && task.video_url && (
          <div className="space-y-3">
            {/* Clip Info */}
            {task.clip_count && (
              <p className="text-xs text-zinc-500">
                Compiled {task.clip_count} clips from multiple sources
              </p>
            )}

            {/* Mini Video Player */}
            <div className="relative rounded-xl overflow-hidden bg-black aspect-video group/player">
              <video
                ref={videoRef}
                src={`http://localhost:8000${task.video_url}`}
                className="w-full h-full object-contain"
                onEnded={() => setIsVideoPlaying(false)}
              />
              <div
                onClick={toggleVideo}
                className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover/player:opacity-100 transition-opacity cursor-pointer"
              >
                <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  {isVideoPlaying ? (
                    <Pause className="w-4 h-4 text-white" />
                  ) : (
                    <Play className="w-4 h-4 text-white ml-0.5" />
                  )}
                </div>
              </div>
            </div>

            {/* Download Button */}
            <button
              onClick={handleDownload}
              className="w-full py-2 px-4 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm text-zinc-300 flex items-center justify-center gap-2 transition-all"
            >
              <Download className="w-4 h-4" />
              {t[language].download}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// Graph View with ECharts - Enhanced for Phase 7
function GraphView() {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)
  const {
    graph,
    language,
    seekTo,
    sources,
    openEntityCard,
    supercutTasks
  } = useAppStore()

  useEffect(() => {
    if (!chartRef.current) return

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }

    const categoryColors: Record<string, string> = {
      boss: '#ef4444',
      item: '#3b82f6',
      location: '#eab308',
      character: '#22c55e',
    }

    // Calculate node connections for dynamic sizing
    const connectionCount: Record<string, number> = {}
    graph.links.forEach(link => {
      connectionCount[link.source] = (connectionCount[link.source] || 0) + 1
      connectionCount[link.target] = (connectionCount[link.target] || 0) + 1
    })

    // Store node data with enhanced styling
    const nodeData = graph.nodes.map((node) => {
      const connections = connectionCount[node.id] || 0
      // Larger base sizes for better visibility
      const baseSize = node.category === 'boss' ? 60 : node.category === 'item' ? 45 : node.category === 'location' ? 45 : 40
      // Dynamic size based on connections (more connections = larger node)
      const dynamicSize = baseSize + Math.min(connections * 5, 25)

      return {
        id: node.id,
        name: node.name,
        symbolSize: dynamicSize,
        category: node.category,
        itemStyle: {
          color: categoryColors[node.category] || '#888',
          shadowBlur: connections > 2 ? 25 : node.category === 'boss' ? 20 : 10,
          shadowColor: categoryColors[node.category]
            ? `${categoryColors[node.category]}80`
            : 'transparent',
          borderColor: '#ffffff40',
          borderWidth: 3,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 40,
            shadowColor: categoryColors[node.category] || '#888',
            borderColor: '#ffffff',
            borderWidth: 4,
          },
          label: {
            fontSize: 16,
            fontWeight: 'bold' as const,
            color: '#ffffff',
          },
        },
        // Store original node data for click handling
        value: node.timestamp,
        sourceId: node.source_id || (sources.length > 0 ? sources[0].id : ''),
        timestamp: node.timestamp,
        originalNode: node,
      }
    })

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        show: true,
        formatter: (params: unknown) => {
          const p = params as { data: { name: string; category: string } }
          return `<div style="padding:8px;background:#18181b;border:1px solid #3f3f46;border-radius:8px;">
            <div style="font-weight:bold;color:white;margin-bottom:4px;">${p.data.name}</div>
            <div style="font-size:11px;color:#a1a1aa;">${p.data.category?.toUpperCase()}</div>
            <div style="font-size:10px;color:#71717a;margin-top:4px;">点击查看详情</div>
          </div>`
        },
        backgroundColor: 'transparent',
        borderWidth: 0,
        extraCssText: 'box-shadow: none;',
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          label: {
            show: true,
            position: 'bottom',
            color: '#e4e4e7',
            fontSize: 12,
            fontWeight: 'bold',
            distance: 8,
            textShadowBlur: 4,
            textShadowColor: 'rgba(0, 0, 0, 0.8)',
          },
          data: nodeData,
          links: graph.links.map((link) => ({
            source: link.source,
            target: link.target,
            lineStyle: {
              width: 2,
              curveness: 0.2,
            },
          })),
          lineStyle: {
            color: '#52525b',
            curveness: 0.2,
            width: 2,
            opacity: 0.6,
          },
          force: {
            repulsion: 1500,
            edgeLength: [120, 280],
            gravity: 0.05,
            friction: 0.5,
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 4,
              color: '#3b82f6',
            },
          },
        },
      ],
      animationDuration: 1500,
      animationEasingUpdate: 'quinticInOut',
    }

    chartInstance.current.setOption(option)

    // Handle node click - open Entity Card popup
    const handleNodeClick = (params: echarts.ECElementEvent) => {
      if (params.dataType === 'node' && params.data) {
        const data = params.data as { originalNode?: GraphNode; name: string; category: string }

        // Get click position relative to viewport
        const event = params.event?.event as MouseEvent
        const position = {
          x: event?.clientX || 200,
          y: event?.clientY || 200,
        }

        // Create node object if originalNode not available
        const node: GraphNode = data.originalNode || {
          id: String(params.dataIndex),
          name: data.name,
          category: data.category as 'boss' | 'item' | 'location' | 'character',
        }

        openEntityCard(node, position)
      }
    }

    chartInstance.current.on('click', handleNodeClick)

    // Handle resize
    const handleResize = () => chartInstance.current?.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      chartInstance.current?.off('click', handleNodeClick)
      window.removeEventListener('resize', handleResize)
    }
  }, [graph, language, seekTo, sources, openEntityCard, supercutTasks])

  return (
    <div className="absolute inset-0 flex flex-col fade-in">
      <div ref={chartRef} className="flex-1 w-full bg-[#121214]" />
      {/* Legend */}
      <div className="absolute bottom-5 left-5 right-5 bg-[#18181b]/90 border border-zinc-800/50 p-3 rounded-xl flex justify-around text-[10px] text-zinc-400 backdrop-blur-md shadow-lg">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500 shadow-lg shadow-red-500/30" />
          Boss
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-blue-500 shadow-lg shadow-blue-500/30" />
          Item
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-yellow-500 shadow-lg shadow-yellow-500/30" />
          Location
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-green-500 shadow-lg shadow-green-500/30" />
          Character
        </div>
      </div>
      {/* Entity Card Popup */}
      <EntityCard />
    </div>
  )
}

// Timeline View with Smart Digest - Phase 8
function TimelineView() {
  const {
    timeline,
    seekTo,
    language,
    currentSourceId,
    digestTask,
    digestIncludeTypes,
    setDigestIncludeTypes,
    startDigestGeneration,
    pollDigestTask,
    setDigestTask,
    activePlayer,
    setActivePlayer,
  } = useAppStore()

  const videoRef = useRef<HTMLVideoElement>(null)
  const [isVideoPlaying, setIsVideoPlaying] = useState(false)

  // Pause video when another player becomes active
  useEffect(() => {
    if (activePlayer !== 'digest' && isVideoPlaying && videoRef.current) {
      videoRef.current.pause()
      setIsVideoPlaying(false)
    }
  }, [activePlayer, isVideoPlaying])

  const t = {
    zh: {
      smartDigest: '智能浓缩',
      storyOnly: '剧情',
      combatOnly: '战斗',
      generateDigest: '🎬 生成精简版视频',
      generating: '生成中...',
      download: '下载',
      retry: '重试',
      segments: '个片段',
      duration: '时长',
      noEvents: '请先生成分析以获取时间轴',
    },
    en: {
      smartDigest: 'Smart Digest',
      storyOnly: 'Story',
      combatOnly: 'Combat',
      generateDigest: '🎬 Generate Digest',
      generating: 'Generating...',
      download: 'Download',
      retry: 'Retry',
      segments: 'segments',
      duration: 'Duration',
      noEvents: 'Generate analysis first to get timeline',
    },
  }

  // Event type styling
  const eventTypeConfig: Record<string, { icon: React.ElementType; color: string; bgColor: string; borderColor: string }> = {
    STORY: {
      icon: BookOpen,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/30',
    },
    COMBAT: {
      icon: Swords,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/30',
    },
    EXPLORE: {
      icon: Footprints,
      color: 'text-zinc-400',
      bgColor: 'bg-zinc-500/10',
      borderColor: 'border-zinc-500/30',
    },
  }

  const handleToggleType = (type: string) => {
    if (digestIncludeTypes.includes(type)) {
      if (digestIncludeTypes.length > 1) {
        setDigestIncludeTypes(digestIncludeTypes.filter(t => t !== type))
      }
    } else {
      setDigestIncludeTypes([...digestIncludeTypes, type])
    }
  }

  const handleGenerate = async () => {
    if (!currentSourceId) return

    const taskId = await startDigestGeneration(currentSourceId)
    if (taskId) {
      const poll = async () => {
        const result = await pollDigestTask(taskId)
        if (result) {
          setDigestTask(result)
          if (result.status !== 'completed' && result.status !== 'error') {
            setTimeout(poll, 2000)
          }
        }
      }
      poll()
    }
  }

  const handleDownload = useCallback(() => {
    if (digestTask?.video_url) {
      const link = document.createElement('a')
      link.href = `http://localhost:8000${digestTask.video_url}`
      link.download = `digest_${currentSourceId || 'video'}.mp4`
      link.click()
    }
  }, [digestTask?.video_url, currentSourceId])

  const toggleVideo = useCallback(() => {
    if (videoRef.current) {
      if (isVideoPlaying) {
        videoRef.current.pause()
        setIsVideoPlaying(false)
      } else {
        setActivePlayer('digest')
        videoRef.current.play()
        setIsVideoPlaying(true)
      }
    }
  }, [isVideoPlaying, setActivePlayer])

  const isGenerating = digestTask && !['completed', 'error'].includes(digestTask.status) && digestTask.status !== undefined

  // Count events by type
  const eventCounts = {
    STORY: timeline.filter(e => e.event_type === 'STORY').length,
    COMBAT: timeline.filter(e => e.event_type === 'COMBAT').length,
    EXPLORE: timeline.filter(e => e.event_type === 'EXPLORE').length,
  }

  return (
    <div className="absolute inset-0 overflow-y-auto scroller fade-in">
      {/* Smart Digest Control Panel */}
      <div className="sticky top-0 z-10 p-4 bg-[#18181b]/95 backdrop-blur-sm border-b border-zinc-800/50">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-400" />
            {t[language].smartDigest}
          </h3>
        </div>

        {/* Type Filters */}
        <div className="flex gap-2 mb-3">
          {(['STORY', 'COMBAT'] as const).map(type => {
            const config = eventTypeConfig[type]
            const Icon = config.icon
            const isSelected = digestIncludeTypes.includes(type)
            return (
              <button
                key={type}
                onClick={() => handleToggleType(type)}
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border',
                  isSelected
                    ? `${config.bgColor} ${config.color} ${config.borderColor}`
                    : 'bg-zinc-800/50 text-zinc-500 border-zinc-700/50 hover:border-zinc-600'
                )}
              >
                {isSelected && <Check className="w-3 h-3" />}
                <Icon className="w-3.5 h-3.5" />
                <span>{t[language][type === 'STORY' ? 'storyOnly' : 'combatOnly']}</span>
                <span className="text-[10px] opacity-70">({eventCounts[type]})</span>
              </button>
            )
          })}
        </div>

        {/* Generate Button or Progress */}
        {!digestTask && (
          <button
            onClick={handleGenerate}
            disabled={!currentSourceId || timeline.length === 0}
            className={cn(
              'w-full py-2.5 px-4 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-all',
              currentSourceId && timeline.length > 0
                ? 'bg-gradient-to-r from-blue-600/20 to-cyan-600/20 hover:from-blue-600/30 hover:to-cyan-600/30 border border-blue-500/30 text-blue-300 hover:shadow-lg hover:shadow-blue-500/10'
                : 'bg-zinc-800/50 text-zinc-500 cursor-not-allowed border border-zinc-700/50'
            )}
          >
            <Film className="w-4 h-4" />
            {t[language].generateDigest}
          </button>
        )}

        {/* Generating Progress */}
        {isGenerating && (
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
              <span className="text-sm text-blue-300">{digestTask.message}</span>
            </div>
            <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                style={{ width: `${digestTask.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error State */}
        {digestTask?.status === 'error' && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm">{digestTask.message}</span>
            </div>
            <button
              onClick={handleGenerate}
              className="w-full py-2 px-4 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-sm text-red-300 transition-all"
            >
              {t[language].retry}
            </button>
          </div>
        )}

        {/* Completed: Mini Player */}
        {digestTask?.status === 'completed' && digestTask.video_url && (
          <div className="space-y-3">
            {/* Stats */}
            <div className="flex items-center gap-4 text-xs text-zinc-400">
              <span>{digestTask.segment_count} {t[language].segments}</span>
              <span>{t[language].duration}: {digestTask.total_duration}s</span>
            </div>

            {/* Mini Video Player */}
            <div className="relative rounded-xl overflow-hidden bg-black aspect-video group/player">
              <video
                ref={videoRef}
                src={`http://localhost:8000${digestTask.video_url}`}
                className="w-full h-full object-contain"
                onEnded={() => setIsVideoPlaying(false)}
              />
              <div
                onClick={toggleVideo}
                className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover/player:opacity-100 transition-opacity cursor-pointer"
              >
                <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  {isVideoPlaying ? (
                    <Pause className="w-4 h-4 text-white" />
                  ) : (
                    <Play className="w-4 h-4 text-white ml-0.5" />
                  )}
                </div>
              </div>
            </div>

            {/* Download Button */}
            <button
              onClick={handleDownload}
              className="w-full py-2 px-4 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm text-zinc-300 flex items-center justify-center gap-2 transition-all"
            >
              <Download className="w-4 h-4" />
              {t[language].download}
            </button>
          </div>
        )}
      </div>

      {/* Timeline Events */}
      <div className="p-6">
        {timeline.length === 0 ? (
          <div className="text-center text-zinc-500 py-10">
            {t[language].noEvents}
          </div>
        ) : (
          <div className="relative pl-8 border-l-2 border-zinc-800/50 space-y-6">
            {timeline.map((event) => {
              const config = eventTypeConfig[event.event_type] || eventTypeConfig.EXPLORE
              const Icon = config.icon
              const isFiltered = !digestIncludeTypes.includes(event.event_type) && event.event_type !== 'EXPLORE'

              return (
                <div
                  key={event.id}
                  onClick={() => seekTo(event.source_id, event.timestamp)}
                  className={cn(
                    'relative group cursor-pointer transition-opacity',
                    isFiltered && 'opacity-40'
                  )}
                >
                  {/* Node with Icon */}
                  <div
                    className={cn(
                      'absolute -left-[37px] top-0 w-6 h-6 rounded-full flex items-center justify-center transition-all z-10 border',
                      config.bgColor,
                      config.borderColor,
                      event.is_key_moment && 'ring-2 ring-offset-2 ring-offset-[#121214]',
                      event.is_key_moment && event.event_type === 'STORY' && 'ring-amber-500/50',
                      event.is_key_moment && event.event_type === 'COMBAT' && 'ring-red-500/50',
                      'group-hover:scale-110'
                    )}
                  >
                    <Icon className={cn('w-3 h-3', config.color)} />
                  </div>

                  {/* Content */}
                  <div className="pl-2">
                    {/* Type Badge + Time */}
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={cn(
                        'text-[10px] px-2 py-0.5 rounded-full border font-medium',
                        config.bgColor,
                        config.color,
                        config.borderColor
                      )}>
                        {event.event_type}
                      </span>
                      <span className="text-[10px] text-zinc-500 font-mono bg-zinc-900/50 px-2 py-0.5 rounded-md border border-zinc-800/50">
                        {event.time}
                      </span>
                    </div>

                    {/* Title */}
                    <h4 className={cn(
                      'text-sm font-bold mb-1 transition-colors',
                      event.event_type === 'EXPLORE' ? 'text-zinc-400 group-hover:text-zinc-300' : 'text-gray-100 group-hover:text-white'
                    )}>
                      {event.title}
                    </h4>

                    {/* Description */}
                    <p className="text-xs text-gray-500 leading-relaxed group-hover:text-gray-400">
                      {event.description}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// Report View (One-Pager Executive Summary)
function ReportView() {
  const { language, selectedSourceIds } = useAppStore()

  return (
    <div className="absolute inset-0 overflow-hidden bg-[#121214]">
      <OnePager sourceIds={selectedSourceIds} language={language} />
    </div>
  )
}

// Studio Dashboard View
function StudioDashboard({ onNavigate }: { onNavigate: (view: string) => void }) {
  const { language, fetchAnalysis, isAnalyzing, selectedSourceIds } = useAppStore()

  const t = {
    zh: {
      title: 'Studio 工作室',
      subtitle: '选择一个 AI 创作工具开始',
      generate: '生成分析',
      generating: '分析中...',
      recentCreations: '最近创作',
      noRecent: '暂无最近生成的视频',
    },
    en: {
      title: 'Studio',
      subtitle: 'Select an AI creative tool to begin',
      generate: 'Generate Analysis',
      generating: 'Analyzing...',
      recentCreations: 'Recent Creations',
      noRecent: 'No recent videos',
    },
  }

  const handleGenerateAnalysis = async () => {
    if (selectedSourceIds.length > 0) {
      await fetchAnalysis(selectedSourceIds)
    }
  }

  // Feature cards configuration
  const features = [
    {
      id: 'conflicts',
      icon: Swords,
      title: language === 'zh' ? 'AI 辩论' : 'AI Debate',
      description: language === 'zh' ? '生成正反方观点的激辩视频' : 'Generate debate videos with opposing viewpoints',
      color: 'bg-gradient-to-br from-red-600 to-orange-600',
      glowColor: 'bg-gradient-to-br from-red-600/20 to-orange-600/20',
    },
    {
      id: 'graph',
      icon: Network,
      title: language === 'zh' ? '全网混剪' : 'Entity Supercut',
      description: language === 'zh' ? '基于知识图谱生成实体高光集锦' : 'Generate entity highlights from knowledge graph',
      color: 'bg-gradient-to-br from-blue-600 to-cyan-600',
      glowColor: 'bg-gradient-to-br from-blue-600/20 to-cyan-600/20',
    },
    {
      id: 'timeline',
      icon: Scissors,
      title: language === 'zh' ? '剧情浓缩' : 'Smart Digest',
      description: language === 'zh' ? '智能识别剧情/战斗，生成纯享版' : 'Smart digest: story & combat highlights only',
      color: 'bg-gradient-to-br from-amber-600 to-yellow-600',
      glowColor: 'bg-gradient-to-br from-amber-600/20 to-yellow-600/20',
    },
    {
      id: 'report',
      icon: FileText,
      title: language === 'zh' ? '深度报告' : 'Deep Report',
      description: language === 'zh' ? '查看详细的文字分析与摘要' : 'View detailed text analysis and summaries',
      color: 'bg-gradient-to-br from-green-600 to-emerald-600',
      glowColor: 'bg-gradient-to-br from-green-600/20 to-emerald-600/20',
    },
  ]

  return (
    <div className="h-full overflow-y-auto scroller fade-in">
      {/* Header */}
      <div className="sticky top-0 z-10 p-5 bg-[#18181b]/95 backdrop-blur-sm border-b border-zinc-800/50">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-blue-400" />
              {t[language].title}
            </h2>
            <p className="text-xs text-zinc-400 mt-1">{t[language].subtitle}</p>
          </div>
          <button
            onClick={handleGenerateAnalysis}
            disabled={isAnalyzing || selectedSourceIds.length === 0}
            className={cn(
              'px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2',
              isAnalyzing
                ? 'bg-blue-500/30 text-blue-300 cursor-wait animate-pulse'
                : selectedSourceIds.length === 0
                ? 'bg-zinc-800/50 text-zinc-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:from-blue-500 hover:to-cyan-500 shadow-lg hover:shadow-blue-500/20'
            )}
            title={selectedSourceIds.length === 0 ? '请先在左侧勾选视频源' : '基于选中视频生成AI分析'}
          >
            {isAnalyzing ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <RefreshCw className="w-3 h-3" />
            )}
            <span>{isAnalyzing ? t[language].generating : t[language].generate}</span>
          </button>
        </div>
      </div>

      {/* Feature Cards Grid */}
      <div className="p-5">
        <div className="grid grid-cols-2 gap-4">
          {features.map((feature) => (
            <FeatureCard
              key={feature.id}
              title={feature.title}
              icon={feature.icon}
              description={feature.description}
              color={feature.color}
              glowColor={feature.glowColor}
              onClick={() => onNavigate(feature.id)}
            />
          ))}
        </div>
      </div>

      {/* Recent Creations */}
      <div className="px-5 pb-5">
        <div className="bg-[#18181b]/80 border border-zinc-800/50 rounded-xl p-4">
          <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <Video className="w-4 h-4 text-zinc-400" />
            {t[language].recentCreations}
          </h3>
          <div className="text-center py-6 text-zinc-500 text-xs">
            {t[language].noRecent}
          </div>
        </div>
      </div>
    </div>
  )
}

// Main Analysis Panel
export function AnalysisPanel() {
  const [activeView, setActiveView] = useState<string>('dashboard')
  const { language } = useAppStore()

  const t = {
    zh: {
      backToStudio: '返回工作室',
    },
    en: {
      backToStudio: 'Back to Studio',
    },
  }

  return (
    <aside className="floating-panel flex flex-col h-full bg-[#121214]">
      {activeView === 'dashboard' ? (
        <StudioDashboard onNavigate={setActiveView} />
      ) : (
        <>
          {/* Header with back button */}
          <div className="flex items-center p-3 border-b border-zinc-800/50 bg-[#18181b]/50">
            <button
              onClick={() => setActiveView('dashboard')}
              className="flex items-center gap-2 px-3 py-1.5 text-xs text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-all"
            >
              <ArrowLeft className="w-3 h-3" />
              {t[language].backToStudio}
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden relative bg-[#121214]">
            {activeView === 'conflicts' && <ConflictsView />}
            {activeView === 'graph' && <GraphView />}
            {activeView === 'timeline' && <TimelineView />}
            {activeView === 'report' && <ReportView />}
          </div>
        </>
      )}
    </aside>
  )
}
