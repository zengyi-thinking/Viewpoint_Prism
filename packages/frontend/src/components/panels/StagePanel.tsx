import { useAppStore } from '@/stores/app-store'
import { Play, Pause, Volume2, Maximize, MessageCircle } from 'lucide-react'

export function StagePanel() {
  const { currentSourceId, currentTime, isPlaying, sources, messages, isChatting } = useAppStore()

  const currentSource = sources.find(s => s.id === currentSourceId)

  const togglePlay = () => {
    const video = document.querySelector('video') as HTMLVideoElement
    if (video) {
      if (video.paused) {
        video.play()
      } else {
        video.pause()
      }
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="h-full flex flex-col bg-[#09090b]">
      {/* Video Player Area */}
      <div className="flex-1 flex items-center justify-center relative">
        {currentSource ? (
          <div className="w-full h-full flex flex-col">
            <video
              data-source-id={currentSource.id}
              src={currentSource.url}
              className="w-full h-full object-contain"
              onTimeUpdate={(e) => {
                const video = e.target as HTMLVideoElement
                // Update currentTime in store
              }}
            />

            {/* Custom Controls */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
              {/* Progress Bar */}
              <div className="w-full h-1 bg-white/20 rounded-full mb-3 cursor-pointer">
                <div
                  className="h-full bg-white rounded-full relative"
                  style={{ width: `${(currentTime / (currentSource.duration || 1)) * 100}%` }}
                >
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg" />
                </div>
              </div>

              {/* Control Buttons */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button
                    onClick={togglePlay}
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
        )}
      </div>

      {/* Chat Area (Bottom Panel) */}
      <div className="border-t border-zinc-800/50 flex flex-col h-full">
        {/* Chat Header */}
        <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-zinc-400" />
          <h3 className="text-sm font-medium text-zinc-200">AI Chat</h3>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
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
                          className="block text-[10px] text-violet-400 hover:text-violet-300 mt-1"
                          onClick={() => {/* Seek to reference */}}
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
            onSubmit={(e) => {
              e.preventDefault()
              const input = e.currentTarget.querySelector('input')
              if (input?.value) {
                // Send message
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
