import { useEffect, useRef } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Play, Pause, Volume2, Maximize, MessageCircle, X, Download } from 'lucide-react'
import { cn } from '@/lib/utils'

export function StagePanel() {
  const {
    currentSourceId,
    currentTime,
    isPlaying,
    activePlayer,
    sources,
    messages,
    isChatting,
    debateTasks,
    directorTasks,
    supercutTasks,
    digestTask,
    setCurrentTime,
    setIsPlaying,
    setActivePlayer,
    sendChatMessage,
    setCurrentSource
  } = useAppStore()

  const mainVideoRef = useRef<HTMLVideoElement>(null)
  const creativeVideoRef = useRef<HTMLVideoElement>(null)

  const currentSource = sources.find(s => s.id === currentSourceId)

  // Get current creative video URL based on active player
  const getCreativeVideoUrl = (): string | null => {
    switch (activePlayer) {
      case 'debate':
        const debateTask = Object.values(debateTasks).find(t => t.status === 'completed')
        return debateTask?.video_url || null
      case 'director':
        const directorTask = Object.values(directorTasks).find(t => t.status === 'completed')
        return directorTask?.video_url || null
      case 'supercut':
        const supercutTask = Object.values(supercutTasks).find(t => t.status === 'completed')
        return supercutTask?.video_url || null
      case 'digest':
        return digestTask?.status === 'completed' ? digestTask.video_url : null
      default:
        return null
    }
  }

  const creativeVideoUrl = getCreativeVideoUrl()

  const togglePlay = (player: 'main' | 'creative') => {
    const video = player === 'main' ? mainVideoRef.current : creativeVideoRef.current
    if (video) {
      if (video.paused) {
        video.play()
        if (player === 'main') setIsPlaying(true)
      } else {
        video.pause()
        if (player === 'main') setIsPlaying(false)
      }
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const handleTimeUpdate = (video: HTMLVideoElement) => {
    setCurrentTime(video.currentTime)
  }

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>, player: 'main' | 'creative') => {
    const progressBar = e.currentTarget
    const rect = progressBar.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = x / rect.width

    const video = player === 'main' ? mainVideoRef.current : creativeVideoRef.current
    const duration = player === 'main' ? (currentSource?.duration || 0) : (creativeVideoRef.current?.duration || 0)

    if (video && duration) {
      video.currentTime = percentage * duration
    }
  }

  const getActiveVideoRef = () => {
    return activePlayer === 'main' ? mainVideoRef : creativeVideoRef
  }

  return (
    <div className="h-full flex flex-col bg-[#09090b]">
      {/* Video Player Area */}
      <div className="flex-1 flex items-center justify-center relative">
        {/* Main Video Player */}
        {activePlayer === 'main' ? (
          currentSource ? (
            <div className="w-full h-full flex flex-col">
              <video
                ref={mainVideoRef}
                data-source-id={currentSource.id}
                src={currentSource.url}
                className="w-full h-full object-contain"
                onTimeUpdate={(e) => handleTimeUpdate(e.target as HTMLVideoElement)}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />

              {/* Custom Controls */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                {/* Progress Bar */}
                <div
                  className="w-full h-1 bg-white/20 rounded-full mb-3 cursor-pointer relative group"
                  onClick={(e) => handleSeek(e, 'main')}
                >
                  <div
                    className="h-full bg-white rounded-full relative transition-all"
                    style={{ width: `${(currentTime / (currentSource.duration || 1)) * 100}%` }}
                  >
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </div>

                {/* Control Buttons */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => togglePlay('main')}
                      className="w-10 h-10 flex items-center justify-center rounded-full bg-white/20 hover:bg-white/30 transition-colors"
                    >
                      {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                    </button>

                    <span className="text-sm text-white font-mono">
                      {formatTime(currentTime)} / {formatTime(currentSource.duration || 0)}
                    </span>

                    <button className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors text-white">
                      <Volume2 className="w-4 h-4" />
                    </button>
                  </div>

                  <button className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors text-white">
                    <Maximize className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-zinc-500">
              <p className="text-lg mb-2">No video selected</p>
              <p className="text-sm">Select a source from the left panel to get started</p>
            </div>
          )
        ) : (
          /* Creative Video Player */
          creativeVideoUrl ? (
            <div className="w-full h-full flex flex-col relative">
              {/* Back to Main Button */}
              <button
                onClick={() => setActivePlayer('main')}
                className="absolute top-4 left-4 z-10 w-8 h-8 flex items-center justify-center rounded-full bg-black/50 hover:bg-black/70 transition-colors text-white"
              >
                <X className="w-4 h-4" />
              </button>

              <video
                ref={creativeVideoRef}
                src={creativeVideoUrl}
                className="w-full h-full object-contain"
                onTimeUpdate={(e) => handleTimeUpdate(e.target as HTMLVideoElement)}
                controls
              />

              {/* Player Type Badge */}
              <div className="absolute top-4 right-4 px-3 py-1 bg-violet-500/80 backdrop-blur-sm rounded-full">
                <span className="text-xs font-medium text-white uppercase">
                  {activePlayer}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-center text-zinc-500">
              <p className="text-lg mb-2">No creative video available</p>
              <p className="text-sm">Generate a video from the Studio tab first</p>
            </div>
          )
        )}
      </div>

      {/* Chat Area (Bottom Panel) */}
      <div className="border-t border-zinc-800/50 flex flex-col h-full max-h-[40%]">
        {/* Chat Header */}
        <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-zinc-400" />
          <h3 className="text-sm font-medium text-zinc-200">AI Chat</h3>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 scroller">
          {messages.length === 0 ? (
            <div className="text-center text-zinc-500 py-8">
              <p>Ask a question about your videos</p>
              <p className="text-sm mt-1">AI will answer with timestamp references</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                    msg.role === 'user'
                      ? 'bg-zinc-700 text-white rounded-tr-sm'
                      : 'bg-zinc-800 text-zinc-200 rounded-tl-sm'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  {msg.references && msg.references.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-white/10">
                      <p className="text-[10px] text-zinc-400">References:</p>
                      {msg.references.map((ref, i) => (
                        <button
                          key={i}
                          className="block text-[10px] text-violet-400 hover:text-violet-300 mt-1 text-left"
                          onClick={() => {
                            setActivePlayer('main')
                            const video = mainVideoRef.current
                            if (video) {
                              video.currentTime = ref.timestamp
                              setCurrentSource(ref.source_id)
                              video.play()
                            }
                          }}
                        >
                          [{ref.source_id} {Math.floor(ref.timestamp / 60)}:{(ref.timestamp % 60).toFixed(0).padStart(2, '0')}]
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {isChatting && (
            <div className="flex justify-start">
              <div className="bg-zinc-800 rounded-2xl rounded-tl-sm px-4 py-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Chat Input */}
        <div className="p-4 border-t border-zinc-800/50">
          <form
            className="flex gap-2"
            onSubmit={async (e) => {
              e.preventDefault()
              const input = e.currentTarget.querySelector('input') as HTMLInputElement
              if (input?.value) {
                await sendChatMessage(input.value)
                input.value = ''
              }
            }}
          >
            <input
              type="text"
              placeholder="Ask a question about your videos..."
              className="flex-1 bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600"
              disabled={isChatting}
            />
            <button
              type="submit"
              disabled={isChatting}
              className="px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-xl text-sm font-medium transition-colors"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
