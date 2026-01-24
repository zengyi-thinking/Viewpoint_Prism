import { useAppStore } from '@/stores/app-store'
import { Play, Pause, Maximize, Film, Volume2, VolumeX, FastForward } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useState, useRef, useEffect, useCallback } from 'react'
import { BACKEND_BASE } from '@/api/client'

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
    analyzeProgressClick,
  } = useAppStore()

  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
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
  const [isLoading, setIsLoading] = useState(false)
  const [hasError, setHasError] = useState(false)

  const currentSource = sources.find((s) => s.id === currentSourceId)
  const videoUrl = currentSource ? `${BACKEND_BASE}${currentSource.url}` : null

  // Debug: Log video URL for troubleshooting
  useEffect(() => {
    if (videoUrl) {
      console.log('[VideoPlayer] Video URL:', videoUrl)
      console.log('[VideoPlayer] Source:', currentSource)
    }
  }, [videoUrl, currentSource])

  // Sync currentTime from store to video
  useEffect(() => {
    if (videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 0.5) {
      videoRef.current.currentTime = currentTime
    }
  }, [currentTime])

  // Handle play state changes with proper ready state check
  useEffect(() => {
    if (videoRef.current && videoUrl) {
      const video = videoRef.current
      if (isPlaying) {
        // Only play if video has enough data
        if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
          video.play().catch((error) => {
            // Ignore AbortError (caused by rapid pause/play)
            if (error.name !== 'AbortError') {
              console.error('[VideoPlayer] Play failed:', error)
            }
            setIsPlaying(false)
          })
        }
      } else {
        video.pause()
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
      console.log('[VideoPlayer] Duration:', videoRef.current.duration)
    }
  }

  const handleLoadedData = () => {
    console.log('[VideoPlayer] Video loaded')
    setIsLoading(false)
  }

  const handleCanPlay = () => {
    console.log('[VideoPlayer] Can play')
    setIsLoading(false)
    // Try to auto-play if user wanted to play
    if (isPlaying && videoRef.current) {
      videoRef.current.play().catch((error) => {
        if (error.name !== 'AbortError') {
          console.error('[VideoPlayer] Auto-play failed:', error)
        }
      })
    }
  }

  const handleError = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    console.error('[VideoPlayer] Error:', e)
    setIsPlaying(false)
    setHasError(true)
    setIsLoading(false)
  }

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!progressBarRef.current || !videoRef.current) return
    const rect = progressBarRef.current.getBoundingClientRect()
    const pos = (e.clientX - rect.left) / rect.width
    const newTime = pos * duration
    videoRef.current.currentTime = newTime
    setCurrentTime(newTime)

    // 触发 AI 分析进度条点击位置之前的内容
    if (duration > 0) {
      analyzeProgressClick(newTime, duration)
    }
  }

  const handleProgressDrag = (e: React.MouseEvent<HTMLDivElement> | MouseEvent) => {
    if (!progressBarRef.current || !videoRef.current) return
    const rect = progressBarRef.current.getBoundingClientRect()
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    setDragProgress(pos * 100)
    const newTime = pos * duration
    videoRef.current.currentTime = newTime
    setCurrentTime(newTime)
  }

  const handleDragStart = () => {
    setIsDragging(true)
  }

  const handleDragEnd = () => {
    setIsDragging(false)
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
    if (!videoUrl) return

    if (!isPlaying) {
      setActivePlayer('main')
    }

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
    if (!containerRef.current) return

    if (document.fullscreenElement) {
      document.exitFullscreen()
    } else {
      containerRef.current.requestFullscreen()
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

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900 rounded-2xl overflow-hidden flex flex-col relative shadow-2xl"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* Video Container */}
      <div className="flex-1 relative flex items-center justify-center bg-black/40">
        {videoUrl ? (
          <video
            ref={videoRef}
            className="w-full h-full object-contain"
            preload="metadata"
            playsInline
            onLoadStart={() => setIsLoading(true)}
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onLoadedData={handleLoadedData}
            onCanPlay={handleCanPlay}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
            onError={handleError}
          >
            <source src={videoUrl} type="video/mp4" />
          </video>
        ) : (
          <div className="flex flex-col items-center justify-center text-zinc-500">
            <Film className="w-20 h-20 mb-6 opacity-20" />
            <p className="text-base">选择一个视频源开始播放</p>
            <p className="text-sm mt-2 text-zinc-600">Select a source to play</p>
          </div>
        )}

        {/* Loading/Error Overlay */}
        {videoUrl && (isLoading || hasError) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/90 backdrop-blur-sm text-zinc-200">
            <Film className={cn('w-20 h-20 mb-6', isLoading ? 'animate-pulse' : '')} />
            <p className="text-xl font-medium">
              {hasError ? '视频加载失败' : '正在加载视频…'}
            </p>
            {currentSource?.status && currentSource.status !== 'done' && !hasError && (
              <p className="text-sm mt-3 text-zinc-400">
                当前状态: {currentSource.status}
              </p>
            )}
          </div>
        )}

        {/* Play Button Overlay */}
        {videoUrl && !isPlaying && !isLoading && !hasError && (
          <button
            onClick={togglePlay}
            className="absolute w-24 h-24 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center border-2 border-white/30 cursor-pointer hover:bg-white/30 hover:scale-110 transition-all shadow-2xl"
          >
            <Play className="text-white ml-1" size={36} fill="white" />
          </button>
        )}

        {/* Source Badge */}
        {currentSource && (
          <div className="absolute top-6 left-6">
            <div className="px-5 py-2.5 rounded-full bg-black/70 backdrop-blur-xl border border-white/10 shadow-lg">
              <span className="text-sm text-white font-medium">
                {currentSource.title}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      {videoUrl && (
        <div
          className={cn(
            'absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/95 via-black/70 to-transparent px-6 py-6 transition-opacity rounded-b-2xl',
            isHovering || !isPlaying ? 'opacity-100' : 'opacity-0'
          )}
        >
          {/* Progress Bar */}
          <div
            ref={progressBarRef}
            onClick={handleProgressClick}
            onMouseDown={handleDragStart}
            onMouseEnter={() => setIsHoveringProgress(true)}
            onMouseLeave={() => setIsHoveringProgress(false)}
            className="relative w-full h-2.5 bg-zinc-700/80 rounded-full cursor-pointer mb-5 group backdrop-blur-sm"
          >
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full relative transition-all shadow-lg"
              style={{ width: `${isDragging ? dragProgress : progress}%` }}
            >
              {/* Glow effect */}
              <div className="absolute inset-0 bg-blue-400/50 blur-sm rounded-full" />
              <div className="absolute right-0 top-1/2 -translate-y-1/2 w-5 h-5 bg-white rounded-full shadow-xl scale-0 group-hover:scale-100 transition-transform" />
            </div>

            {/* Hover time preview */}
            {(isHoveringProgress || isDragging) && (
              <>
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-white/90 rounded-full pointer-events-none shadow-lg"
                  style={{ left: `${isDragging ? dragProgress : progress}%` }}
                />
                <div
                  className="absolute bottom-full mb-3 px-3 py-1.5 bg-black/95 text-white text-xs rounded-lg whitespace-nowrap border border-white/10 shadow-xl"
                  style={{ left: `${isDragging ? dragProgress : progress}%` }}
                >
                  {formatTime((isDragging ? dragProgress : progress) / 100 * duration)}
                </div>
              </>
            )}
          </div>

          {/* Control Buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Play/Pause */}
              <button
                onClick={togglePlay}
                className="w-14 h-14 rounded-full bg-white/15 hover:bg-white/25 flex items-center justify-center transition-all backdrop-blur-sm border border-white/10"
              >
                {isPlaying ? <Pause size={22} className="text-white" /> : <Play size={22} className="text-white ml-0.5" />}
              </button>

              {/* Volume */}
              <button
                onClick={toggleMute}
                className="w-11 h-11 rounded-full bg-white/15 hover:bg-white/25 flex items-center justify-center transition-all backdrop-blur-sm border border-white/10"
              >
                {isMuted ? <VolumeX size={18} className="text-white" /> : <Volume2 size={18} className="text-white" />}
              </button>

              {/* Time */}
              <span className="text-white text-base font-mono font-medium tracking-wide">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>

              {/* Speed */}
              <div className="relative">
                <button
                  onClick={cycleSpeed}
                  onMouseEnter={() => setShowSpeedMenu(true)}
                  onMouseLeave={() => setShowSpeedMenu(false)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all backdrop-blur-sm border',
                    playbackSpeed !== 1
                      ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                      : 'bg-white/15 text-zinc-300 border-white/10 hover:bg-white/25'
                  )}
                >
                  <FastForward size={15} />
                  {playbackSpeed}x
                </button>

                {showSpeedMenu && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 p-2 bg-black/95 backdrop-blur-xl rounded-xl border border-white/10 whitespace-nowrap shadow-2xl">
                    {PLAYBACK_SPEEDS.map((speed) => (
                      <button
                        key={speed}
                        onClick={() => setPlaybackSpeed(speed)}
                        className={cn(
                          'block w-full px-4 py-2 text-sm rounded-lg text-left transition-all',
                          playbackSpeed === speed
                            ? 'bg-blue-500 text-white'
                            : 'text-zinc-300 hover:bg-white/10'
                        )}
                      >
                        {speed}x
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Fullscreen */}
            <button
              onClick={toggleFullscreen}
              className="w-11 h-11 rounded-full bg-white/15 hover:bg-white/25 flex items-center justify-center transition-all backdrop-blur-sm border border-white/10"
            >
              <Maximize size={18} className="text-white" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
