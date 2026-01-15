import { useAppStore } from '@/stores/app-store'
import { Play, Pause, Maximize, Film, Volume2, VolumeX, Clock, FastForward } from 'lucide-react'
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
      // Reset play state when source changes
      setIsPlaying(false)
    }
  }, [currentSourceId, videoUrl, setIsPlaying])

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
    if (videoRef.current && videoUrl) {
      if (isPlaying) {
        const playPromise = videoRef.current.play()
        if (playPromise !== undefined) {
          playPromise
            .then(() => {
              console.log('[VideoPlayer] Playing successfully')
            })
            .catch((error) => {
              console.error('[VideoPlayer] Play failed:', error)
              setIsPlaying(false)
            })
        }
      } else {
        videoRef.current.pause()
      }
    }
  }, [isPlaying, setIsPlaying, videoUrl])

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
      console.log('[VideoPlayer] Metadata loaded, duration:', videoRef.current.duration)
    }
  }

  const handleLoadedData = () => {
    console.log('[VideoPlayer] Video data loaded, ready to play')
    // 视频数据加载完成，可以播放
  }

  const handleCanPlay = () => {
    console.log('[VideoPlayer] Video can play')
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
    if (!videoUrl) {
      console.warn('[VideoPlayer] No video source selected')
      return
    }

    if (!isPlaying) {
      // 设置为活跃播放器
      setActivePlayer('main')
    }

    // 等待下一帧再切换状态，确保视频元素准备好
    requestAnimationFrame(() => {
      setIsPlaying(!isPlaying)
    })
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
          onLoadedData={handleLoadedData}
          onCanPlay={handleCanPlay}
          onPlay={() => {
            console.log('[VideoPlayer] Play event fired')
            setIsPlaying(true)
          }}
          onPause={() => {
            console.log('[VideoPlayer] Pause event fired')
            setIsPlaying(false)
          }}
          onEnded={() => setIsPlaying(false)}
          onError={(e) => {
            console.error('[VideoPlayer] Video error:', e)
            setIsPlaying(false)
          }}
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

// ChatPanel has been moved to features/chat/ChatPanel.tsx
