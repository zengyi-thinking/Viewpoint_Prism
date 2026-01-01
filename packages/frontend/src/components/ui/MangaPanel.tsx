/**
 * MangaPanel - AI Webtoon Reader
 *
 * Story Stream: Transform video highlights into AI-generated manga panels.
 *
 * Features:
 * - Vertical scrolling webtoon layout
 * - "Magic Frame" interaction: click to play video segment
 * - Streaming panel delivery (shows panels as they generate)
 * - Comic-style speech bubbles and captions
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { Loader2, Play, Pause, X, RefreshCw, Palette, Clock, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/stores/app-store'
import type { WebtoonTask, WebtoonPanel } from '@/types'

const API_BASE = 'http://localhost:8000/api'

/**
 * MagicFrame Component - Single manga panel with video toggle
 */
function MagicFrame({
  panel,
  onPlayVideo,
  isVideoPlaying,
  videoRef,
}: {
  panel: WebtoonPanel
  onPlayVideo: (panel: WebtoonPanel) => void
  isVideoPlaying: boolean
  videoRef: React.RefObject<HTMLVideoElement>
}) {
  const [isFlipped, setIsFlipped] = useState(false)
  const [imageLoaded, setImageLoaded] = useState(false)

  const handleClick = useCallback(() => {
    if (!isFlipped) {
      setIsFlipped(true)
      onPlayVideo(panel)
    } else {
      setIsFlipped(false)
    }
  }, [isFlipped, onPlayVideo, panel])

  return (
    <div className="relative group">
      {/* Panel number badge */}
      <div className="absolute -left-3 top-4 z-20 w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center shadow-lg">
        <span className="text-xs font-bold text-white">{panel.panel_number}</span>
      </div>

      {/* Time badge */}
      <div className="absolute -right-2 top-4 z-20 px-2 py-1 bg-zinc-900/90 rounded-full border border-zinc-700 flex items-center gap-1">
        <Clock className="w-3 h-3 text-zinc-400" />
        <span className="text-[10px] font-mono text-zinc-300">{panel.time_formatted}</span>
      </div>

      {/* Main frame container */}
      <div
        onClick={handleClick}
        className={cn(
          'relative cursor-pointer rounded-2xl overflow-hidden transition-all duration-500 border-4',
          isFlipped
            ? 'border-cyan-500/50 shadow-lg shadow-cyan-500/20'
            : 'border-zinc-800 hover:border-zinc-600 hover:shadow-xl'
        )}
        style={{ perspective: '1000px' }}
      >
        {/* Manga Image Side */}
        <div
          className={cn(
            'relative transition-all duration-500',
            isFlipped && 'opacity-0 pointer-events-none'
          )}
        >
          {/* Manga image */}
          <div className="relative aspect-square bg-zinc-900">
            {!imageLoaded && (
              <div className="absolute inset-0 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-zinc-600 animate-spin" />
              </div>
            )}
            <img
              src={`http://localhost:8000${panel.manga_image_url}`}
              alt={`Panel ${panel.panel_number}`}
              className={cn(
                'w-full h-full object-cover transition-opacity',
                imageLoaded ? 'opacity-100' : 'opacity-0'
              )}
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageLoaded(true)}
            />

            {/* Play overlay on hover */}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
              <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center border-2 border-white/50">
                  <Play className="w-8 h-8 text-white ml-1" />
                </div>
              </div>
            </div>
          </div>

          {/* Caption bubble */}
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black via-black/80 to-transparent">
            <div className="relative">
              {/* Speech bubble tail */}
              <div className="absolute -top-3 left-8 w-4 h-4 bg-white rotate-45 rounded-sm" />
              {/* Bubble content */}
              <div className="bg-white rounded-2xl px-4 py-3 shadow-lg">
                <p className="text-sm text-zinc-800 font-medium leading-relaxed">
                  {panel.caption}
                </p>
              </div>
            </div>
          </div>

          {/* Characters badge */}
          {panel.characters && (
            <div className="absolute top-4 left-4 px-2 py-1 bg-black/60 backdrop-blur-sm rounded-full">
              <span className="text-[10px] text-zinc-300">{panel.characters}</span>
            </div>
          )}
        </div>

        {/* Video Side */}
        {isFlipped && (
          <div className="absolute inset-0 bg-black">
            <video
              ref={videoRef}
              src={`http://localhost:8000/static/temp/${panel.video_segment.source_id}/video.mp4#t=${panel.video_segment.start}`}
              className="w-full h-full object-contain"
              autoPlay
              controls
              onEnded={() => setIsFlipped(false)}
            />
            {/* Close button */}
            <button
              onClick={(e) => {
                e.stopPropagation()
                setIsFlipped(false)
              }}
              className="absolute top-4 right-4 p-2 bg-black/60 hover:bg-black/80 rounded-full transition-colors"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * MangaPanel Component - Main Webtoon Reader
 */
export function MangaPanel() {
  const { currentSourceId, sources, seekTo } = useAppStore()
  const [task, setTask] = useState<WebtoonTask | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [displayedPanels, setDisplayedPanels] = useState<WebtoonPanel[]>([])
  const [maxPanels, setMaxPanels] = useState(8)
  const videoRef = useRef<HTMLVideoElement>(null)
  const [playingPanel, setPlayingPanel] = useState<WebtoonPanel | null>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Get current source
  const currentSource = sources.find(s => s.id === currentSourceId)

  // Start generation
  const handleGenerate = useCallback(async () => {
    if (!currentSourceId) return

    setIsGenerating(true)
    setDisplayedPanels([])
    setTask(null)

    try {
      const response = await fetch(`${API_BASE}/webtoon/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_id: currentSourceId,
          max_panels: maxPanels,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        setTask(data)

        // Start polling for status
        if (data.task_id) {
          pollTask(data.task_id)
        }
      } else {
        const error = await response.json()
        setTask({
          task_id: '',
          status: 'error',
          progress: 0,
          message: error.detail || '生成失败',
          panels: [],
          total_panels: 0,
          current_panel: 0,
          error: error.detail,
        })
        setIsGenerating(false)
      }
    } catch (error) {
      setTask({
        task_id: '',
        status: 'error',
        progress: 0,
        message: '网络连接失败',
        panels: [],
        total_panels: 0,
        current_panel: 0,
        error: String(error),
      })
      setIsGenerating(false)
    }
  }, [currentSourceId, maxPanels])

  // Poll task status
  const pollTask = useCallback(async (taskId: string) => {
    try {
      const response = await fetch(`${API_BASE}/webtoon/task/${taskId}`)
      if (response.ok) {
        const data: WebtoonTask = await response.json()
        setTask(data)

        // Update displayed panels (streaming)
        if (data.panels.length > displayedPanels.length) {
          setDisplayedPanels(data.panels)
        }

        // Continue polling if not done
        if (data.status !== 'completed' && data.status !== 'error') {
          pollIntervalRef.current = setTimeout(() => pollTask(taskId), 2000)
        } else {
          setIsGenerating(false)
          setDisplayedPanels(data.panels)
        }
      }
    } catch (error) {
      console.error('Poll error:', error)
      setIsGenerating(false)
    }
  }, [displayedPanels.length])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current)
      }
    }
  }, [])

  // Handle video play
  const handlePlayVideo = useCallback((panel: WebtoonPanel) => {
    setPlayingPanel(panel)
    // Also seek main player
    seekTo(panel.video_segment.source_id, panel.video_segment.start)
  }, [seekTo])

  return (
    <div className="h-full flex flex-col bg-[#faf9f7]">
      {/* Header */}
      <div className="sticky top-0 z-30 p-4 bg-white/95 backdrop-blur-sm border-b border-zinc-200 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center shadow-lg">
              <Palette className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-zinc-800">Story Stream</h2>
              <p className="text-xs text-zinc-500">AI 漫画故事流</p>
            </div>
          </div>

          {/* Panel count selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">格数:</span>
            <select
              value={maxPanels}
              onChange={(e) => setMaxPanels(Number(e.target.value))}
              disabled={isGenerating}
              className="px-3 py-1.5 bg-zinc-100 border border-zinc-200 rounded-lg text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
            >
              <option value={6}>6 格</option>
              <option value={8}>8 格</option>
              <option value={10}>10 格</option>
              <option value={12}>12 格</option>
            </select>
          </div>
        </div>

        {/* Source info */}
        {currentSource && (
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-zinc-400">当前视频:</span>
            <span className="text-sm font-medium text-zinc-700 truncate max-w-[200px]">
              {currentSource.title}
            </span>
          </div>
        )}

        {/* Generate button or progress */}
        {!task || task.status === 'error' ? (
          <button
            onClick={handleGenerate}
            disabled={!currentSourceId || isGenerating}
            className={cn(
              'w-full py-3 px-4 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2',
              currentSourceId && !isGenerating
                ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-500 hover:to-pink-500 shadow-lg hover:shadow-xl hover:shadow-purple-500/20'
                : 'bg-zinc-200 text-zinc-400 cursor-not-allowed'
            )}
          >
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Palette className="w-4 h-4" />
            )}
            {isGenerating ? '绘制中...' : '🎨 生成故事流'}
          </button>
        ) : task.status !== 'completed' ? (
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-purple-500 animate-spin" />
              <span className="text-sm text-purple-600 font-medium">{task.message}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-zinc-200 rounded-full h-2 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500"
                  style={{ width: `${task.progress}%` }}
                />
              </div>
              <span className="text-xs text-zinc-500 font-mono">
                {task.current_panel}/{task.total_panels}
              </span>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <span className="text-sm text-green-600 font-medium">
              ✨ {task.panels.length} 格漫画已完成
            </span>
            <button
              onClick={handleGenerate}
              className="flex items-center gap-1 px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100 rounded-lg transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              重新生成
            </button>
          </div>
        )}

        {/* Error display */}
        {task?.status === 'error' && (
          <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{task.message}</p>
          </div>
        )}
      </div>

      {/* Manga panels - Webtoon scroll layout */}
      <div className="flex-1 overflow-y-auto scroller">
        {displayedPanels.length > 0 ? (
          <div className="max-w-lg mx-auto py-8 px-4 space-y-8">
            {/* Screentone pattern background */}
            <div
              className="fixed inset-0 pointer-events-none opacity-[0.03] -z-10"
              style={{
                backgroundImage: `radial-gradient(circle, #000 1px, transparent 1px)`,
                backgroundSize: '4px 4px',
              }}
            />

            {displayedPanels.map((panel, index) => (
              <div
                key={panel.panel_number}
                className="animate-in fade-in slide-in-from-bottom-4 duration-500"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <MagicFrame
                  panel={panel}
                  onPlayVideo={handlePlayVideo}
                  isVideoPlaying={playingPanel?.panel_number === panel.panel_number}
                  videoRef={videoRef}
                />
              </div>
            ))}

            {/* Generating indicator at bottom */}
            {isGenerating && task && task.current_panel < task.total_panels && (
              <div className="flex items-center justify-center gap-3 py-8">
                <Loader2 className="w-5 h-5 text-purple-500 animate-spin" />
                <span className="text-sm text-zinc-500">
                  正在绘制第 {task.current_panel + 1} 格...
                </span>
              </div>
            )}

            {/* End marker */}
            {task?.status === 'completed' && (
              <div className="text-center py-8">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-zinc-100 rounded-full">
                  <span className="text-lg">🎬</span>
                  <span className="text-sm text-zinc-600 font-medium">故事结束</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Empty state */
          <div className="flex-1 flex items-center justify-center h-full">
            <div className="text-center py-20">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-100 to-pink-100 flex items-center justify-center mx-auto mb-4">
                <Palette className="w-10 h-10 text-purple-400" />
              </div>
              <h3 className="text-lg font-bold text-zinc-700 mb-2">AI 漫画故事流</h3>
              <p className="text-sm text-zinc-500 max-w-xs mx-auto mb-6">
                将视频的精彩时刻转化为 AI 生成的漫画，点击任意漫画格可播放原片段
              </p>
              {!currentSourceId && (
                <p className="text-xs text-amber-600 bg-amber-50 px-4 py-2 rounded-lg inline-block">
                  请先在左侧选择一个视频源
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Scroll hint */}
      {displayedPanels.length > 2 && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 animate-bounce">
          <ChevronDown className="w-6 h-6 text-zinc-400" />
        </div>
      )}
    </div>
  )
}
