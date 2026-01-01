import { useAppStore } from '@/stores/app-store'
import { Play, Pause, Maximize, Terminal, MoreHorizontal, ArrowUp, Film, Volume2, VolumeX, Clock, FastForward } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useState, useRef, useEffect, useCallback } from 'react'

const API_BASE = 'http://localhost:8000'

const PLAYBACK_SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2]

export function VideoPlayer() {
  const {
    sources,
    currentSourceId,
    currentTime,
    isPlaying,
    setCurrentTime,
    setIsPlaying,
    activePlayer,
    setActivePlayer,
    addMessage,
  } = useAppStore()

  const videoRef = useRef<HTMLVideoElement>(null)
  const progressBarRef = useRef<HTMLDivElement>(null)
  const [duration, setDuration] = useState(0)
  const [progress, setProgress] = useState(0)
  const [isHovering, setIsHovering] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [showSpeedMenu, setShowSpeedMenu] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [dragProgress, setDragProgress] = useState(0)
  const [isHoveringProgress, setIsHoveringProgress] = useState(false)

  // Context Bridge: User memory - track which time ranges user frequently seeks to
  const seekMemoryRef = useRef<Map<number, number>>(new Map())  // timeRange -> count
  const contextBridgeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastSeekPositionRef = useRef<number>(0)

  const currentSource = sources.find((s) => s.id === currentSourceId)
  const videoUrl = currentSource ? `${API_BASE}${currentSource.url}` : null

  // Context Bridge: Fetch bridging context and add as AI message in chat
  const fetchAndShowContextBridge = useCallback(async (targetTimestamp: number, previousTimestamp?: number) => {
    if (!currentSourceId) return

    try {
      const response = await fetch(`${API_BASE}/api/chat/context-bridge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_id: currentSourceId,
          timestamp: targetTimestamp,
          previous_timestamp: previousTimestamp,
        }),
      })

      if (response.ok) {
        const data = await response.json()

        // Check if user frequently seeks to this time range (user memory)
        const timeRange = Math.floor(targetTimestamp / 30) * 30  // 30-second bins
        const seekCount = seekMemoryRef.current.get(timeRange) || 0
        seekMemoryRef.current.set(timeRange, seekCount + 1)

        // Build the message with user memory hint
        let memoryHint = ''
        if (seekCount >= 3) {
          memoryHint = `\n\n💡 记忆提示: 这已经是你第 ${seekCount} 次查看这个时间段的内容了，看来这里对你很重要。`
        }

        // Add as AI message in chat
        addMessage({
          id: `cb-${Date.now()}`,
          role: 'ai',
          content: `📍 **跳转到 ${data.timestamp_str}**\n\n${data.summary}${memoryHint}`,
          timestamp: new Date(),
        })
      }
    } catch (error) {
      console.error('[Context Bridge] Fetch error:', error)
    }
  }, [currentSourceId, addMessage])

  // Context Bridge: Trigger on seek with debounce
  const triggerContextBridge = useCallback((targetTime: number) => {
    const SEEK_THRESHOLD = 15  // Changed from 60 to 15 seconds
    const DEBOUNCE_DELAY = 1000

    const jumpDistance = Math.abs(targetTime - lastSeekPositionRef.current)

    // Only trigger if jump is significant (more than 15 seconds)
    if (jumpDistance < SEEK_THRESHOLD) {
      return
    }

    // Clear any existing timer
    if (contextBridgeTimerRef.current) {
      clearTimeout(contextBridgeTimerRef.current)
    }

    // Set new timer (debounce)
    contextBridgeTimerRef.current = setTimeout(() => {
      fetchAndShowContextBridge(targetTime, lastSeekPositionRef.current)
      lastSeekPositionRef.current = targetTime
    }, DEBOUNCE_DELAY)
  }, [fetchAndShowContextBridge])

  // Handle video source change
  useEffect(() => {
    if (videoRef.current && videoUrl) {
      videoRef.current.load()
      if (currentTime > 0) {
        videoRef.current.currentTime = currentTime
      }
    }
  }, [currentSourceId, videoUrl])

  // Sync currentTime from store to video (for seeking from other components)
  useEffect(() => {
    if (videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 1) {
      const oldTime = videoRef.current.currentTime
      videoRef.current.currentTime = currentTime
      // Trigger Context Bridge for external seeks (e.g., from chat citations)
      const jumpDistance = Math.abs(currentTime - oldTime)
      if (jumpDistance >= 15) {
        triggerContextBridge(currentTime)
      }
    }
  }, [currentTime, triggerContextBridge])

  // Initialize lastSeekPositionRef when video loads
  useEffect(() => {
    if (duration > 0 && lastSeekPositionRef.current === 0) {
      lastSeekPositionRef.current = currentTime
    }
  }, [duration, currentTime])

  // Handle play state changes
  useEffect(() => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.play().catch(() => setIsPlaying(false))
      } else {
        videoRef.current.pause()
      }
    }
  }, [isPlaying, setIsPlaying])

  // Pause when another player becomes active
  useEffect(() => {
    if (activePlayer !== 'main' && activePlayer !== null && isPlaying) {
      setIsPlaying(false)
    }
  }, [activePlayer, isPlaying, setIsPlaying])

  // Handle playback speed change
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = playbackSpeed
    }
  }, [playbackSpeed])

  const handleTimeUpdate = () => {
    if (videoRef.current && !isDragging) {
      const time = videoRef.current.currentTime
      setProgress((time / duration) * 100)
      setCurrentTime(time)
    }
  }

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration)
    }
  }

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (videoRef.current) {
      const rect = e.currentTarget.getBoundingClientRect()
      const pos = (e.clientX - rect.left) / rect.width
      const newTime = pos * duration
      seekToTime(newTime)
    }
  }

  const handleProgressDrag = (e: React.MouseEvent<HTMLDivElement> | MouseEvent) => {
    if (!progressBarRef.current) return
    const rect = progressBarRef.current.getBoundingClientRect()
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    setDragProgress(pos * 100)
    const newTime = pos * duration
    setCurrentTime(newTime)
    if (videoRef.current) {
      videoRef.current.currentTime = newTime
    }
  }

  const seekToTime = (time: number) => {
    if (videoRef.current) {
      const oldTime = videoRef.current.currentTime
      videoRef.current.currentTime = time
      setCurrentTime(time)
      setProgress((time / duration) * 100)
      // Trigger Context Bridge for significant seeks (15+ seconds)
      const jumpDistance = Math.abs(time - oldTime)
      if (jumpDistance >= 15) {
        triggerContextBridge(time)
      }
    }
  }

  const handleDragStart = () => {
    setIsDragging(true)
  }

  const handleDragEnd = () => {
    setIsDragging(false)
    // Note: Context Bridge is now triggered by seekToTime(), which is called
    // when the user clicks on the progress bar. For dragging, we trigger here.
    if (videoRef.current && lastSeekPositionRef.current !== videoRef.current.currentTime) {
      const jumpDistance = Math.abs(videoRef.current.currentTime - lastSeekPositionRef.current)
      if (jumpDistance >= 15) {
        triggerContextBridge(videoRef.current.currentTime)
      }
    }
  }

  useEffect(() => {
    if (isDragging) {
      const handleMouseMove = (e: MouseEvent) => handleProgressDrag(e)
      const handleMouseUp = () => handleDragEnd()

      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)

      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, duration])

  const togglePlay = () => {
    if (!isPlaying) {
      setActivePlayer('main')
    }
    setIsPlaying(!isPlaying)
  }

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  const toggleFullscreen = () => {
    if (videoRef.current) {
      if (document.fullscreenElement) {
        document.exitFullscreen()
      } else {
        videoRef.current.requestFullscreen()
      }
    }
  }

  const cycleSpeed = () => {
    const currentIndex = PLAYBACK_SPEEDS.indexOf(playbackSpeed)
    const nextIndex = (currentIndex + 1) % PLAYBACK_SPEEDS.length
    setPlaybackSpeed(PLAYBACK_SPEEDS[nextIndex])
  }

  const formatTime = (seconds: number) => {
    if (!isFinite(seconds)) return '00:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (contextBridgeTimerRef.current) {
        clearTimeout(contextBridgeTimerRef.current)
      }
    }
  }, [])

  // Get preview time based on drag position
  const getPreviewTime = () => {
    if (isDragging) {
      return (dragProgress / 100) * duration
    }
    return currentTime
  }

  return (
    <div
      className="flex-1 floating-panel relative group flex flex-col justify-center items-center overflow-hidden bg-black"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* Background */}
      <div className="absolute inset-0 -z-10 bg-zinc-900/50" />

      {/* Video Element or Empty State */}
      {videoUrl ? (
        <video
          ref={videoRef}
          className="max-w-full max-h-full object-contain bg-black"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
        >
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      ) : (
        <div className="flex flex-col items-center justify-center text-zinc-500">
          <Film className="w-16 h-16 mb-4 opacity-30" />
          <p className="text-sm">选择一个视频源开始播放</p>
          <p className="text-xs mt-1 text-zinc-600">Select a source to play</p>
        </div>
      )}

      {/* Play Button Overlay (when paused) */}
      {videoUrl && !isPlaying && (
        <div
          onClick={togglePlay}
          className="absolute w-16 h-16 bg-white/10 backdrop-blur-md rounded-full flex items-center justify-center border border-white/20 cursor-pointer hover:bg-white/20 hover:scale-105 transition-all z-10 shadow-[0_0_30px_rgba(0,0,0,0.3)]"
        >
          <Play className="text-white ml-1" size={24} />
        </div>
      )}

      {/* Source Badge */}
      {currentSource && (
        <div className="absolute top-6 left-6 flex gap-2">
          <div className="px-3 py-1.5 rounded-full bg-black/40 border border-white/10 backdrop-blur-md text-[10px] text-zinc-300 font-mono flex items-center gap-2 shadow-sm">
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
            <span className="font-bold text-white uppercase">
              {currentSource.title.slice(0, 20)}
            </span>
          </div>
        </div>
      )}

      {/* Context Bridge is now shown as AI messages in the chat panel */}

      {/* Controls Overlay - Always visible at bottom */}
      {videoUrl && (
        <div
          className={cn(
            'absolute bottom-0 left-0 right-0 px-6 pb-6 pt-10 bg-gradient-to-t from-black/80 via-black/50 to-transparent transition-all',
            isHovering || !isPlaying
              ? 'opacity-100'
              : 'opacity-80'
          )}
        >
          {/* Enhanced Progress Bar with Preview */}
          <div
            ref={progressBarRef}
            onClick={handleProgressClick}
            onMouseDown={handleDragStart}
            onMouseEnter={() => setIsHoveringProgress(true)}
            onMouseLeave={() => setIsHoveringProgress(false)}
            className="relative w-full h-2 bg-zinc-700/60 rounded-full cursor-pointer group/progress overflow-hidden"
            style={{ WebkitUserSelect: 'none', userSelect: 'none' }}
          >
            {/* Progress Fill */}
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 relative transition-all duration-100"
              style={{ width: `${isDragging ? dragProgress : progress}%` }}
            >
              {/* Glow effect */}
              <div className="absolute inset-0 bg-blue-400/30 blur-sm" />
              {/* Drag Handle */}
              <div
                className={cn(
                  'absolute right-0 top-1/2 -translate-y-1/2 w-5 h-5 bg-white rounded-full shadow-lg transition-all',
                  'scale-0 group-hover/progress:scale-100',
                  isDragging && 'scale-110'
                )}
              >
                <div className="absolute inset-0 bg-white/50 rounded-full animate-ping" />
              </div>
            </div>

            {/* Hover/Drag preview line */}
            {(isHoveringProgress || isDragging) && (
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-white/80 rounded-full pointer-events-none"
                style={{ left: `${isDragging ? dragProgress : progress}%` }}
              />
            )}

            {/* Time preview on hover */}
            {(isHoveringProgress || isDragging) && (
              <div
                className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-black/90 text-white text-[10px] rounded whitespace-nowrap"
                style={{ left: `${isDragging ? dragProgress : progress}%` }}
              >
                {formatTime(getPreviewTime())}
              </div>
            )}
          </div>

          {/* Control Buttons */}
          <div className="flex justify-between items-center mt-3">
            {/* Left Controls */}
            <div className="flex items-center gap-4">
              <button
                onClick={togglePlay}
                className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all hover:scale-105"
              >
                {isPlaying ? <Pause size={18} className="text-white" /> : <Play size={18} className="text-white ml-0.5" />}
              </button>

              <button
                onClick={toggleMute}
                className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all hover:scale-105"
              >
                {isMuted ? <VolumeX size={18} className="text-white" /> : <Volume2 size={18} className="text-white" />}
              </button>

              <span className="text-white text-sm font-mono min-w-[100px]">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>

              {/* Playback Speed Control */}
              <div className="relative">
                <button
                  onClick={cycleSpeed}
                  onMouseEnter={() => setShowSpeedMenu(true)}
                  onMouseLeave={() => setShowSpeedMenu(false)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
                    playbackSpeed !== 1
                      ? 'bg-blue-500 text-white'
                      : 'bg-white/10 text-gray-300 hover:bg-white/20'
                  )}
                >
                  <FastForward size={14} />
                  {playbackSpeed}x
                </button>

                {/* Speed Tooltip */}
                {showSpeedMenu && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1.5 bg-black/95 backdrop-blur-xl rounded-lg border border-white/10 whitespace-nowrap">
                    {PLAYBACK_SPEEDS.map((speed) => (
                      <button
                        key={speed}
                        onClick={() => setPlaybackSpeed(speed)}
                        className={cn(
                          'block px-3 py-1 text-xs rounded transition-colors',
                          playbackSpeed === speed
                            ? 'bg-blue-500 text-white'
                            : 'text-gray-300 hover:bg-white/10 hover:text-white'
                        )}
                      >
                        {speed}x
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Controls */}
            <div className="flex items-center gap-3">
              <button
                onClick={toggleFullscreen}
                className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all hover:scale-105"
              >
                <Maximize size={18} className="text-white" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export function ChatPanel() {
  const { messages, language, sendChatMessage, isLoading, seekTo, sources, selectedSourceIds } = useAppStore()
  const [inputValue, setInputValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const t = {
    zh: {
      placeholder: '针对视频内容提问...',
      thinking: '正在思考...',
      processingWarning: '⏳ 部分视频仍在处理中，建议等待"就绪"后再提问',
      noReadyVideos: '暂无可用视频，请等待视频处理完成',
    },
    en: {
      placeholder: 'Ask about the video...',
      thinking: 'Thinking...',
      processingWarning: '⏳ Some videos are still processing, wait for "Ready" status',
      noReadyVideos: 'No videos ready, please wait for processing to complete',
    },
  }

  // Check if any selected source (or all sources if none selected) is still processing
  const relevantSources = selectedSourceIds.length > 0
    ? sources.filter(s => selectedSourceIds.includes(s.id))
    : sources

  const processingCount = relevantSources.filter(
    s => s.status === 'processing' || s.status === 'analyzing' || s.status === 'uploaded'
  ).length
  const readyCount = relevantSources.filter(s => s.status === 'done').length
  const hasProcessing = processingCount > 0
  const noReadyVideos = readyCount === 0 && relevantSources.length > 0

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return
    const message = inputValue.trim()
    setInputValue('')
    await sendChatMessage(message)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Parse content and render citations as clickable links with markdown support
  const renderContent = (content: string) => {
    const lines = content.split('\n')
    const result: React.ReactNode[] = []

    for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
      const line = lines[lineIdx]

      // Handle headers ## or ###
      if (line.startsWith('### ')) {
        result.push(<h3 key={`h3-${lineIdx}`} className="text-sm font-bold text-white mt-3 mb-1">{line.slice(4)}</h3>)
        continue
      } else if (line.startsWith('## ')) {
        result.push(<h2 key={`h2-${lineIdx}`} className="text-base font-bold text-white mt-3 mb-1">{line.slice(3)}</h2>)
        continue
      } else if (line.startsWith('# ')) {
        result.push(<h1 key={`h1-${lineIdx}`} className="text-lg font-bold text-white mt-3 mb-2">{line.slice(2)}</h1>)
        continue
      }

      // Handle list items
      const listMatch = line.match(/^(\d+\.|-)\s+(.*)/)
      if (listMatch) {
        result.push(
          <li key={`li-${lineIdx}`} className="text-sm text-zinc-300 ml-4 mb-1 list-disc">
            {renderInlineMarkdown(listMatch[2])}
          </li>
        )
        continue
      }

      // Handle empty lines
      if (line.trim() === '') {
        result.push(<br key={`br-${lineIdx}`} />)
        continue
      }

      // Regular paragraph with inline markdown and citations
      result.push(
        <p key={`p-${lineIdx}`} className="text-sm text-zinc-300 mb-1 leading-relaxed">
          {renderInlineMarkdown(line)}
        </p>
      )
    }

    return result
  }

  // Render inline markdown (bold, citations) within a line
  const renderInlineMarkdown = (text: string): React.ReactNode => {
    const parts: React.ReactNode[] = []
    let lastIndex = 0

    // First, process bold **text**
    const boldRegex = /\*\*([^*]+)\*\*/g
    const boldMatches: Array<{index: number, length: number, text: string}> = []
    let boldMatch
    while ((boldMatch = boldRegex.exec(text)) !== null) {
      boldMatches.push({ index: boldMatch.index, length: boldMatch[0].length, text: boldMatch[1] })
    }

    // Process text with bold and citations
    const citationRegex = /\[([^\]]+)\s+(\d{1,2}):(\d{2})\]/g
    const allMatches: Array<{index: number, length: number, type: 'bold' | 'citation', data?: any}> = []

    // Collect all bold matches
    for (const m of boldMatches) {
      allMatches.push({ index: m.index, length: m.length, type: 'bold', data: m.text })
    }

    // Collect all citation matches
    let citationMatch
    citationRegex.lastIndex = 0 // Reset regex
    while ((citationMatch = citationRegex.exec(text)) !== null) {
      allMatches.push({
        index: citationMatch.index,
        length: citationMatch[0].length,
        type: 'citation',
        data: { videoTitle: citationMatch[1], minutes: citationMatch[2], seconds: citationMatch[3] }
      })
    }

    // Sort matches by position
    allMatches.sort((a, b) => a.index - b.index)

    // Build parts array
    for (const match of allMatches) {
      // Add text before match
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index))
      }

      if (match.type === 'bold') {
        parts.push(<strong key={`bold-${match.index}`} className="font-semibold text-white">{match.data}</strong>)
      } else if (match.type === 'citation') {
        const timestamp = parseInt(match.data.minutes) * 60 + parseInt(match.data.seconds)
        const source = sources.find(s =>
          s.title.includes(match.data.videoTitle) || match.data.videoTitle.includes(s.title.slice(0, 10))
        )
        const sourceId = source?.id || sources[0]?.id || ''

        parts.push(
          <span
            key={`cite-${match.index}`}
            className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 text-blue-400 cursor-pointer hover:underline hover:text-blue-300 transition-colors text-xs bg-blue-500/10 rounded"
            onClick={() => sourceId && seekTo(sourceId, timestamp)}
            title={`跳转到 ${match.data.minutes}:${match.data.seconds}`}
          >
            <Clock className="w-3 h-3" />
            {match.data.minutes}:{match.data.seconds}
          </span>
        )
      }

      lastIndex = match.index + match.length
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex))
    }

    return parts.length > 0 ? parts : text
  }

  return (
    <div className="floating-panel flex flex-col h-full bg-[#121214]">
      {/* Header */}
      <div className="h-10 flex items-center justify-between px-5 border-b border-zinc-800/50 bg-[#18181b]/50">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
          <Terminal className="w-3 h-3" />
          Intelligence Log
        </span>
        <MoreHorizontal className="w-4 h-4 text-zinc-600 cursor-pointer hover:text-zinc-400" />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto scroller p-5 space-y-5">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'flex gap-4',
              msg.role === 'user' && 'flex-row-reverse'
            )}
          >
            <div
              className={cn(
                'w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-xs shadow-md border border-white/10',
                msg.role === 'ai' ? 'bg-white text-black' : 'bg-zinc-700 text-white'
              )}
            >
              {msg.role === 'ai' ? '🔮' : '👤'}
            </div>
            <div
              className={cn(
                'p-4 rounded-2xl text-sm leading-relaxed max-w-[85%] border-zinc-800/50 shadow-sm',
                msg.role === 'ai' ? 'bubble-ai' : 'bubble-user'
              )}
            >
              {msg.role === 'ai' ? renderContent(msg.content) : msg.content}
              {/* Show references if available */}
              {msg.references && msg.references.length > 0 && (
                <div className="mt-3 pt-3 border-t border-zinc-700/50">
                  <div className="text-[10px] text-zinc-500 mb-2">📎 相关片段:</div>
                  <div className="flex flex-wrap gap-2">
                    {msg.references.slice(0, 3).map((ref, idx) => (
                      <span
                        key={idx}
                        onClick={() => ref.source_id && seekTo(ref.source_id, ref.timestamp)}
                        className="text-[10px] px-2 py-1 bg-zinc-800 rounded-full text-zinc-400 cursor-pointer hover:bg-zinc-700 hover:text-zinc-300 transition-colors"
                      >
                        {Math.floor(ref.timestamp / 60)}:{String(Math.floor(ref.timestamp % 60)).padStart(2, '0')}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-xs shadow-md border border-white/10 bg-white text-black">
              🔮
            </div>
            <div className="p-4 rounded-2xl text-sm leading-relaxed bubble-ai">
              <span className="flex items-center gap-2 text-zinc-400">
                <span className="animate-pulse">●</span>
                {t[language].thinking}
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-zinc-800/50 bg-[#18181b]/30">
        {/* Processing Warning */}
        {hasProcessing && (
          <div className="mb-3 px-3 py-2 text-[11px] text-amber-400 bg-amber-500/10 rounded-lg border border-amber-500/20">
            {noReadyVideos ? t[language].noReadyVideos : t[language].processingWarning}
            <span className="text-zinc-500 ml-2">({readyCount}/{relevantSources.length} 就绪)</span>
          </div>
        )}
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="w-full bg-[#18181b] border border-zinc-800/80 rounded-xl py-3 pl-4 pr-12 text-xs text-white focus:border-zinc-500 outline-none transition-colors shadow-inner disabled:opacity-50"
            placeholder={t[language].placeholder}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !inputValue.trim()}
            className="absolute right-2 top-1.5 w-8 h-8 bg-white text-black rounded-lg hover:bg-gray-200 flex items-center justify-center transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
