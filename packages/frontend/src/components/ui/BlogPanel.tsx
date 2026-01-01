/**
 * BlogPanel - Cinematic Blog Reader
 *
 * Phase 14: Transform video into editorial-style visual articles.
 * Medium/Substack inspired design with manga illustrations.
 *
 * Features:
 * - Single column centered layout (max-width: 768px)
 * - Serif typography for body text
 * - Full-width manga panels with click-to-play
 * - Markdown export (Copy to Clipboard)
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { Loader2, Play, X, RefreshCw, BookOpen, Clock, Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/stores/app-store'
import type { WebtoonTask, WebtoonPanel, BlogSection } from '@/types'

const API_BASE = 'http://localhost:8000/api'

/**
 * MagicImage Component - Manga panel with video toggle
 */
function MagicImage({
  panel,
  onPlayVideo,
  videoRef,
}: {
  panel: WebtoonPanel
  onPlayVideo: (panel: WebtoonPanel) => void
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
    <figure className="my-8 -mx-4 md:mx-0">
      {/* Image container with aspect ratio */}
      <div
        onClick={handleClick}
        className={cn(
          'relative cursor-pointer rounded-xl overflow-hidden transition-all duration-500',
          'shadow-lg hover:shadow-2xl',
          isFlipped
            ? 'ring-2 ring-cyan-500/50 shadow-cyan-500/20'
            : 'hover:ring-1 hover:ring-zinc-600'
        )}
      >
        {/* Manga Image Side */}
        <div
          className={cn(
            'relative transition-all duration-500',
            isFlipped && 'opacity-0 pointer-events-none'
          )}
        >
          <div className="relative aspect-[4/3] bg-zinc-900">
            {!imageLoaded && (
              <div className="absolute inset-0 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-zinc-600 animate-spin" />
              </div>
            )}
            <img
              src={`http://localhost:8000${panel.manga_image_url}`}
              alt={`Illustration ${panel.panel_number}`}
              className={cn(
                'w-full h-full object-cover transition-opacity',
                imageLoaded ? 'opacity-100' : 'opacity-0'
              )}
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageLoaded(true)}
            />

            {/* Play overlay on hover */}
            <div className="absolute inset-0 bg-black/0 hover:bg-black/40 transition-colors flex items-center justify-center group">
              <div className="opacity-0 group-hover:opacity-100 transition-opacity transform group-hover:scale-100 scale-90">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center border-2 border-white/50">
                  <Play className="w-7 h-7 text-white ml-1" />
                </div>
                <p className="text-white text-xs text-center mt-2 font-medium">Click to play</p>
              </div>
            </div>
          </div>
        </div>

        {/* Video Side */}
        {isFlipped && (
          <div className="absolute inset-0 bg-black aspect-[4/3]">
            <video
              ref={videoRef}
              src={`http://localhost:8000/static/temp/${panel.video_segment.source_id}/video.mp4#t=${panel.video_segment.start}`}
              className="w-full h-full object-contain"
              autoPlay
              controls
              onEnded={() => setIsFlipped(false)}
            />
            <button
              onClick={(e) => {
                e.stopPropagation()
                setIsFlipped(false)
              }}
              className="absolute top-4 right-4 p-2 bg-black/60 hover:bg-black/80 rounded-full transition-colors z-10"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        )}
      </div>

      {/* Caption */}
      <figcaption className="mt-3 text-center text-sm text-zinc-500 italic px-4">
        {panel.caption}
      </figcaption>
    </figure>
  )
}

/**
 * BlogPanel Component - Cinematic Blog Reader
 */
export function BlogPanel() {
  const { currentSourceId, sources, seekTo } = useAppStore()
  const [task, setTask] = useState<WebtoonTask | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [maxPanels, setMaxPanels] = useState(6)
  const [copied, setCopied] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_playingPanel, setPlayingPanel] = useState<WebtoonPanel | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Get current source
  const currentSource = sources.find(s => s.id === currentSourceId)

  // Start generation
  const handleGenerate = useCallback(async () => {
    if (!currentSourceId) return

    setIsGenerating(true)
    setTask(null)
    setCopied(false)

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

        if (data.task_id) {
          pollTask(data.task_id)
        }
      } else {
        const error = await response.json()
        setTask({
          task_id: '',
          status: 'error',
          progress: 0,
          message: error.detail || 'Generation failed',
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
        message: 'Network connection failed',
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

        if (data.status !== 'completed' && data.status !== 'error') {
          pollIntervalRef.current = setTimeout(() => pollTask(taskId), 2000)
        } else {
          setIsGenerating(false)
        }
      }
    } catch (error) {
      console.error('Poll error:', error)
      setIsGenerating(false)
    }
  }, [])

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
    seekTo(panel.video_segment.source_id, panel.video_segment.start)
  }, [seekTo])

  // Generate Markdown export
  const generateMarkdown = useCallback(() => {
    if (!task || !task.blog_sections) return ''

    let md = `# ${task.blog_title || 'Cinematic Blog'}\n\n`

    for (const section of task.blog_sections) {
      if (section.type === 'text' && section.content) {
        md += `${section.content}\n\n`
      } else if (section.type === 'panel' && section.panel_index !== undefined) {
        const panel = task.panels[section.panel_index]
        if (panel) {
          md += `![${panel.caption}](http://localhost:8000${panel.manga_image_url})\n`
          md += `*${panel.caption}*\n\n`
        }
      }
    }

    return md
  }, [task])

  // Copy to clipboard
  const handleCopy = useCallback(async () => {
    const markdown = generateMarkdown()
    try {
      await navigator.clipboard.writeText(markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Copy failed:', err)
    }
  }, [generateMarkdown])

  // Render blog section
  const renderSection = (section: BlogSection, index: number) => {
    if (section.type === 'text' && section.content) {
      // Render text as markdown-like content
      const paragraphs = section.content.split('\n').filter(p => p.trim())
      return (
        <div key={index} className="space-y-4">
          {paragraphs.map((p, i) => {
            // Check for headings
            if (p.startsWith('## ')) {
              return (
                <h2 key={i} className="text-2xl font-bold text-zinc-100 mt-8 mb-4 font-sans">
                  {p.slice(3)}
                </h2>
              )
            }
            if (p.startsWith('### ')) {
              return (
                <h3 key={i} className="text-xl font-semibold text-zinc-200 mt-6 mb-3 font-sans">
                  {p.slice(4)}
                </h3>
              )
            }
            // Regular paragraph with serif font
            return (
              <p
                key={i}
                className="text-lg text-zinc-300 leading-relaxed font-serif"
                style={{ fontFamily: "'Noto Serif SC', 'Georgia', serif" }}
              >
                {p}
              </p>
            )
          })}
        </div>
      )
    }

    if (section.type === 'panel' && section.panel_index !== undefined) {
      const panel = task?.panels[section.panel_index]
      if (panel) {
        return (
          <MagicImage
            key={index}
            panel={panel}
            onPlayVideo={handlePlayVideo}
            videoRef={videoRef}
          />
        )
      }
    }

    return null
  }

  const isComplete = task?.status === 'completed' && task.blog_sections && task.blog_sections.length > 0

  return (
    <div className="h-full flex flex-col bg-[#0a0a0b]">
      {/* Header */}
      <div className="sticky top-0 z-30 p-4 bg-[#0a0a0b]/95 backdrop-blur-sm border-b border-zinc-800/50">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-600 to-orange-600 flex items-center justify-center shadow-lg">
                <BookOpen className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-zinc-100">Cinematic Blog</h2>
                <p className="text-xs text-zinc-500">AI 电影级博客</p>
              </div>
            </div>

            {/* Panel count selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">插图:</span>
              <select
                value={maxPanels}
                onChange={(e) => setMaxPanels(Number(e.target.value))}
                disabled={isGenerating}
                className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-300 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
              >
                <option value={4}>4 张</option>
                <option value={6}>6 张</option>
                <option value={8}>8 张</option>
              </select>
            </div>
          </div>

          {/* Source info */}
          {currentSource && (
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-zinc-500">Current video:</span>
              <span className="text-sm font-medium text-zinc-400 truncate max-w-[200px]">
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
                  ? 'bg-gradient-to-r from-amber-600 to-orange-600 text-white hover:from-amber-500 hover:to-orange-500 shadow-lg hover:shadow-xl hover:shadow-amber-500/20'
                  : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
              )}
            >
              {isGenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <BookOpen className="w-4 h-4" />
              )}
              {isGenerating ? 'Generating...' : '📝 Generate Cinematic Blog'}
            </button>
          ) : task.status !== 'completed' ? (
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <Loader2 className="w-4 h-4 text-amber-500 animate-spin" />
                <span className="text-sm text-amber-400 font-medium">{task.message}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-zinc-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-500"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
                <span className="text-xs text-zinc-500 font-mono">
                  {task.progress}%
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-sm text-green-500 font-medium">
                ✨ Blog generated with {task.panels.length} illustrations
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className={cn(
                    'flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg transition-all',
                    copied
                      ? 'bg-green-500/20 text-green-400'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                  )}
                >
                  {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  {copied ? 'Copied!' : 'Copy MD'}
                </button>
                <button
                  onClick={handleGenerate}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors"
                >
                  <RefreshCw className="w-3 h-3" />
                  Regenerate
                </button>
              </div>
            </div>
          )}

          {/* Error display */}
          {task?.status === 'error' && (
            <div className="mt-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-400">{task.message}</p>
            </div>
          )}
        </div>
      </div>

      {/* Blog Content - Article Layout */}
      <div className="flex-1 overflow-y-auto scroller">
        {isComplete ? (
          <article className="max-w-3xl mx-auto py-12 px-6">
            {/* Article Title */}
            <header className="mb-12 text-center">
              <h1
                className="text-4xl md:text-5xl font-bold text-zinc-100 mb-4 leading-tight"
                style={{ fontFamily: "'Noto Sans SC', sans-serif" }}
              >
                {task.blog_title}
              </h1>
              <div className="flex items-center justify-center gap-4 text-sm text-zinc-500">
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {new Date().toLocaleDateString('zh-CN')}
                </span>
                <span>•</span>
                <span>{task.panels.length} illustrations</span>
              </div>
              <div className="mt-6 w-16 h-1 bg-gradient-to-r from-amber-500 to-orange-500 mx-auto rounded-full" />
            </header>

            {/* Article Sections */}
            <div className="space-y-6">
              {task.blog_sections?.map((section, index) => renderSection(section, index))}
            </div>

            {/* Footer */}
            <footer className="mt-16 pt-8 border-t border-zinc-800 text-center">
              <p className="text-sm text-zinc-500">
                Generated by Viewpoint Prism AI
              </p>
            </footer>
          </article>
        ) : (
          /* Empty state */
          <div className="flex-1 flex items-center justify-center h-full">
            <div className="text-center py-20 px-6">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-amber-900/30 to-orange-900/30 flex items-center justify-center mx-auto mb-4">
                <BookOpen className="w-10 h-10 text-amber-500/60" />
              </div>
              <h3 className="text-xl font-bold text-zinc-300 mb-2">Cinematic Blog</h3>
              <p className="text-sm text-zinc-500 max-w-sm mx-auto mb-6 leading-relaxed">
                Transform your video into an editorial-style article with AI-generated manga illustrations.
                Click any image to play the original video segment.
              </p>
              {!currentSourceId && (
                <p className="text-xs text-amber-500 bg-amber-500/10 px-4 py-2 rounded-lg inline-block">
                  Please select a video source first
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
