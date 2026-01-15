import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Terminal, MoreHorizontal, ArrowUp, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'

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

  const relevantSources = selectedSourceIds.length > 0
    ? sources.filter(s => selectedSourceIds.includes(s.id))
    : sources

  const processingCount = relevantSources.filter(
    s => s.status === 'processing' || s.status === 'analyzing' || s.status === 'uploaded'
  ).length
  const readyCount = relevantSources.filter(s => s.status === 'done').length
  const hasProcessing = processingCount > 0
  const noReadyVideos = readyCount === 0 && relevantSources.length > 0

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

  const renderContent = (content: string) => {
    const lines = content.split('\n')
    const result: React.ReactNode[] = []

    for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
      const line = lines[lineIdx]

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

      const listMatch = line.match(/^(\d+\.|-)\s+(.*)/)
      if (listMatch) {
        result.push(
          <li key={`li-${lineIdx}`} className="text-sm text-zinc-300 ml-4 mb-1 list-disc">
            {renderInlineMarkdown(listMatch[2])}
          </li>
        )
        continue
      }

      if (line.trim() === '') {
        result.push(<br key={`br-${lineIdx}`} />)
        continue
      }

      result.push(
        <p key={`p-${lineIdx}`} className="text-sm text-zinc-300 mb-1 leading-relaxed">
          {renderInlineMarkdown(line)}
        </p>
      )
    }

    return result
  }

  const renderInlineMarkdown = (text: string): React.ReactNode => {
    const parts: React.ReactNode[] = []
    let lastIndex = 0

    const boldRegex = /\*\*([^*]+)\*\*/g
    const boldMatches: Array<{index: number, length: number, text: string}> = []
    let boldMatch
    while ((boldMatch = boldRegex.exec(text)) !== null) {
      boldMatches.push({ index: boldMatch.index, length: boldMatch[0].length, text: boldMatch[1] })
    }

    const citationRegex = /\[([^\]]+)\s+(\d{1,2}):(\d{2})\]/g
    const allMatches: Array<{index: number, length: number, type: 'bold' | 'citation', data: unknown}> = []

    for (const m of boldMatches) {
      allMatches.push({ index: m.index, length: m.length, type: 'bold', data: m.text })
    }

    let citationMatch
    citationRegex.lastIndex = 0
    while ((citationMatch = citationRegex.exec(text)) !== null) {
      allMatches.push({
        index: citationMatch.index,
        length: citationMatch[0].length,
        type: 'citation',
        data: { videoTitle: citationMatch[1], minutes: citationMatch[2], seconds: citationMatch[3] }
      })
    }

    allMatches.sort((a, b) => a.index - b.index)

    for (const match of allMatches) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index))
      }

      if (match.type === 'bold') {
        const boldText = match.data as string
        parts.push(<strong key={`bold-${match.index}`} className="font-semibold text-white">{boldText}</strong>)
      } else if (match.type === 'citation') {
        const data = match.data as { videoTitle: string; minutes: string; seconds: string }
        const timestamp = parseInt(data.minutes) * 60 + parseInt(data.seconds)
        const source = sources.find(s =>
          s.title.includes(data.videoTitle) || data.videoTitle.includes(s.title.slice(0, 10))
        )
        const sourceId = source?.id || sources[0]?.id || ''

        parts.push(
          <span
            key={`cite-${match.index}`}
            className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 text-blue-400 cursor-pointer hover:underline hover:text-blue-300 transition-colors text-xs bg-blue-500/10 rounded"
            onClick={() => sourceId && seekTo(sourceId, timestamp)}
            title={`跳转到 ${data.minutes}:${data.seconds}`}
          >
            <Clock className="w-3 h-3" />
            {data.minutes}:{data.seconds}
          </span>
        )
      }

      lastIndex = match.index + match.length
    }

    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex))
    }

    return parts.length > 0 ? parts : text
  }

  return (
    <div className="floating-panel flex flex-col h-full bg-[#121214]">
      <div className="h-10 flex items-center justify-between px-5 border-b border-zinc-800/50 bg-[#18181b]/50">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
          <Terminal className="w-3 h-3" />
          Intelligence Log
        </span>
        <MoreHorizontal className="w-4 h-4 text-zinc-600 cursor-pointer hover:text-zinc-400" />
      </div>

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

      <div className="p-4 border-t border-zinc-800/50 bg-[#18181b]/30">
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
