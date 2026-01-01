import { useRef, useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Maximize,
  Minimize,
  SkipBack,
  SkipForward,
  PictureInPicture,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface VideoPlayerProps {
  src: string
  poster?: string
  className?: string
  onTimeUpdate?: (currentTime: number) => void
  onEnded?: () => void
  autoPlay?: boolean
  showControls?: boolean
}

type PlaybackSpeed = 0.25 | 0.5 | 0.75 | 1 | 1.25 | 1.5 | 2

const PLAYBACK_SPEEDS: PlaybackSpeed[] = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2]

export function VideoPlayer({
  src,
  poster,
  className,
  onTimeUpdate,
  onEnded,
  autoPlay = false,
  showControls = true,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const progressRef = useRef<HTMLDivElement>(null)

  // State
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showUi, setShowUi] = useState(true)
  const [playbackSpeed, setPlaybackSpeed] = useState<PlaybackSpeed>(1)
  const [isPiP, setIsPiP] = useState(false)
  const [showSpeedMenu, setShowSpeedMenu] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // Format time
  const formatTime = (time: number) => {
    const hours = Math.floor(time / 3600)
    const mins = Math.floor((time % 3600) / 60)
    const secs = Math.floor(time % 60)

    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Toggle play/pause
  const togglePlay = useCallback(() => {
    const video = videoRef.current
    if (!video) return

    if (video.paused) {
      video.play()
      setIsPlaying(true)
    } else {
      video.pause()
      setIsPlaying(false)
    }
  }, [])

  // Skip forward/backward
  const skip = (seconds: number) => {
    const video = videoRef.current
    if (!video) return
    video.currentTime = Math.min(Math.max(0, video.currentTime + seconds), video.duration)
  }

  // Handle volume change
  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value)
    setVolume(newVolume)
    setIsMuted(newVolume === 0)
    if (videoRef.current) {
      videoRef.current.volume = newVolume
      videoRef.current.muted = newVolume === 0
    }
  }

  // Toggle mute
  const toggleMute = () => {
    const video = videoRef.current
    if (!video) return

    if (isMuted) {
      video.muted = false
      video.volume = volume || 1
      setIsMuted(false)
    } else {
      video.muted = true
      setIsMuted(true)
    }
  }

  // Handle seek
  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = x / rect.width

    const video = videoRef.current
    if (!video) return

    video.currentTime = percentage * video.duration
  }

  // Toggle fullscreen
  const toggleFullscreen = useCallback(async () => {
    const container = containerRef.current
    if (!container) return

    if (!document.fullscreenElement) {
      await container.requestFullscreen()
      setIsFullscreen(true)
    } else {
      await document.exitFullscreen()
      setIsFullscreen(false)
    }
  }, [])

  // Toggle Picture-in-Picture
  const togglePiP = async () => {
    const video = videoRef.current
    if (!video) return

    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture()
        setIsPiP(false)
      } else if (document.pictureInPictureEnabled) {
        await video.requestPictureInPicture()
        setIsPiP(true)
      }
    } catch (error) {
      console.error('PiP error:', error)
    }
  }

  // Change playback speed
  const changePlaybackSpeed = (speed: PlaybackSpeed) => {
    const video = videoRef.current
    if (!video) return

    video.playbackRate = speed
    setPlaybackSpeed(speed)
    setShowSpeedMenu(false)
  }

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const video = videoRef.current
      if (!video) return

      switch (e.key) {
        case ' ':
        case 'k':
          e.preventDefault()
          togglePlay()
          break
        case 'ArrowLeft':
          skip(-5)
          break
        case 'ArrowRight':
          skip(5)
          break
        case 'ArrowUp':
          e.preventDefault()
          setVolume((v) => Math.min(1, v + 0.1))
          break
        case 'ArrowDown':
          e.preventDefault()
          setVolume((v) => Math.max(0, v - 0.1))
          break
        case 'm':
          toggleMute()
          break
        case 'f':
          toggleFullscreen()
          break
        case '>':
        case '.':
          changePlaybackSpeed(PLAYBACK_SPEEDS[Math.min(PLAYBACK_SPEEDS.length - 1, PLAYBACK_SPEEDS.indexOf(playbackSpeed) + 1)])
          break
        case '<':
        case ',':
          changePlaybackSpeed(PLAYBACK_SPEEDS[Math.max(0, PLAYBACK_SPEEDS.indexOf(playbackSpeed) - 1)])
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [togglePlay, toggleMute, toggleFullscreen, playbackSpeed])

  // Auto-hide controls
  useEffect(() => {
    if (!showControls || !isPlaying) return

    const hideTimer = setTimeout(() => {
      setShowUi(false)
    }, 3000)

    return () => clearTimeout(hideTimer)
  }, [showUi, isPlaying, showControls])

  // Sync with external onTimeUpdate
  useEffect(() => {
    onTimeUpdate?.(currentTime)
  }, [currentTime, onTimeUpdate])

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative bg-black rounded-xl overflow-hidden group",
        "video-container",
        className
      )}
      onMouseMove={() => setShowUi(true)}
      onMouseLeave={() => isPlaying && setShowUi(false)}
    >
      {/* Video Element */}
      <video
        ref={videoRef}
        src={src}
        poster={poster}
        autoPlay={autoPlay}
        className="w-full h-full object-contain"
        onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
        onLoadedMetadata={(e) => setDuration(e.target.duration)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={onEnded}
        onWaiting={() => setIsLoading(true)}
        onCanPlay={() => setIsLoading(false)}
      />

      {/* Loading Spinner */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex items-center justify-center bg-black/50"
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            >
              <Loader2 className="w-12 h-12 text-white" />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Center Play Button (when paused) */}
      <AnimatePresence>
        {!isPlaying && !isLoading && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="absolute inset-0 flex items-center justify-center cursor-pointer"
            onClick={togglePlay}
          >
            <div className="w-20 h-20 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center hover:bg-white/30 transition-colors">
              <Play className="w-10 h-10 text-white ml-1" fill="white" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Controls */}
      <AnimatePresence>
        {showUi && showControls && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="video-controls absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4"
          >
            {/* Progress Bar */}
            <div
              ref={progressRef}
              className="w-full h-1.5 bg-white/20 rounded-full mb-4 cursor-pointer relative group/progress"
              onClick={handleSeek}
            >
              <motion.div
                className="h-full bg-violet-500 rounded-full relative"
                initial={{ width: 0 }}
                animate={{ width: `${(currentTime / duration) * 100}%` }}
              >
                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full opacity-0 group-hover/progress:opacity-100 transition-opacity" />
              </motion.div>
              {/* Hover preview */}
              <div className="absolute inset-0 bg-violet-500/30 rounded-full opacity-0 group-hover/progress:opacity-100 transition-opacity" />
            </div>

            {/* Control Buttons */}
            <div className="flex items-center justify-between">
              {/* Left Controls */}
              <div className="flex items-center gap-2">
                {/* Play/Pause */}
                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={togglePlay}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                >
                  {isPlaying ? (
                    <Pause className="w-5 h-5 text-white" />
                  ) : (
                    <Play className="w-5 h-5 text-white ml-0.5" />
                  )}
                </motion.button>

                {/* Skip Buttons */}
                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={() => skip(-10)}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                  title="Skip -10s"
                >
                  <SkipBack className="w-4 h-4 text-white" />
                </motion.button>
                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={() => skip(10)}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                  title="Skip +10s"
                >
                  <SkipForward className="w-4 h-4 text-white" />
                </motion.button>

                {/* Volume */}
                <div className="flex items-center gap-2 group/volume">
                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    onClick={toggleMute}
                    className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                  >
                    {isMuted || volume === 0 ? (
                      <VolumeX className="w-4 h-4 text-white" />
                    ) : (
                      <Volume2 className="w-4 h-4 text-white" />
                    )}
                  </motion.button>
                  <div className="w-0 overflow-hidden group-hover/volume:w-20 transition-all">
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={isMuted ? 0 : volume}
                      onChange={handleVolumeChange}
                      className="w-full h-1 bg-white/20 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full"
                    />
                  </div>
                </div>

                {/* Time Display */}
                <span className="text-xs text-white font-mono">
                  {formatTime(currentTime)} / {formatTime(duration)}
                </span>
              </div>

              {/* Right Controls */}
              <div className="flex items-center gap-2">
                {/* Playback Speed */}
                <div className="relative">
                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                    className="px-2 py-1 rounded-lg hover:bg-white/10 transition-colors text-xs text-white font-medium"
                  >
                    {playbackSpeed}x
                  </motion.button>
                  <AnimatePresence>
                    {showSpeedMenu && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className="absolute bottom-full right-0 mb-2 bg-zinc-900/95 backdrop-blur-sm border border-zinc-700 rounded-xl p-2 min-w-[80px]"
                      >
                        {PLAYBACK_SPEEDS.map((speed) => (
                          <button
                            key={speed}
                            onClick={() => changePlaybackSpeed(speed)}
                            className={cn(
                              "w-full px-3 py-1.5 rounded-lg text-xs text-left transition-colors",
                              speed === playbackSpeed
                                ? "bg-violet-600 text-white"
                                : "text-zinc-300 hover:bg-zinc-800"
                            )}
                          >
                            {speed}x
                          </button>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Picture in Picture */}
                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={togglePiP}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                  title="Picture in Picture"
                >
                  <PictureInPicture className="w-4 h-4 text-white" />
                </motion.button>

                {/* Fullscreen */}
                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={toggleFullscreen}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                  title="Fullscreen"
                >
                  {isFullscreen ? (
                    <Minimize className="w-4 h-4 text-white" />
                  ) : (
                    <Maximize className="w-4 h-4 text-white" />
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
