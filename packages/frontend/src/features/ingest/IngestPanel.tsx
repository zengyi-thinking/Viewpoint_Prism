import { useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Search, Play, RefreshCw, ExternalLink, Clock } from 'lucide-react'
import { IngestAPI } from '@/api'
import type { NetworkSearchTask } from '@/types'

/**
 * Ingest Panel - 网络视频搜索面板
 *
 * 功能：
 * - 搜索网络视频（B站、YouTube等）
 * - 显示搜索结果
 * - 导入选中视频到系统
 * - 查看导入进度
 */
export function IngestPanel() {
  const { networkSearchTask, setNetworkSearchTask, fetchSources } = useAppStore()
  const [query, setQuery] = useState('')
  const [platform, setPlatform] = useState<'bilibili' | 'youtube' | 'all'>('all')
  const [isSearching, setIsSearching] = useState(false)
  const [selectedVideos, setSelectedVideos] = useState<string[]>([])

  const handleSearch = async () => {
    if (!query.trim() || isSearching) return

    setIsSearching(true)
    try {
      const response = await IngestAPI.search({
        query,
        platform: platform === 'all' ? undefined : platform,
        max_results: 10,
      })

      setNetworkSearchTask({
        task_id: response.task_id,
        status: response.status as any,
        progress: response.progress || 0,
        message: response.message,
        results: response.results || [],
        error: response.error,
      })

      // 轮询任务状态
      const pollInterval = setInterval(async () => {
        const status = await IngestAPI.getTaskStatus(response.task_id)
        setNetworkSearchTask({
          task_id: status.task_id,
          status: status.status as any,
          progress: status.progress || 0,
          message: status.message,
          results: status.results || networkSearchTask?.results || [],
          error: status.error,
        })

        if (status.status === 'completed' || status.status === 'error') {
          clearInterval(pollInterval)
          setIsSearching(false)
        }
      }, 2000)
    } catch (error) {
      console.error('Failed to search videos:', error)
      setIsSearching(false)
    }
  }

  const handleImportSelected = async () => {
    if (selectedVideos.length === 0 || !networkSearchTask?.results) return

    const videosToImport = networkSearchTask.results.filter(v =>
      selectedVideos.includes(v.url)
    )

    for (const video of videosToImport) {
      try {
        await IngestAPI.import({ url: video.url })
      } catch (error) {
        console.error(`Failed to import ${video.url}:`, error)
      }
    }

    // 刷新视频源列表
    await fetchSources()
    setSelectedVideos([])
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="floating-panel flex flex-col h-full bg-[#121214]">
      <div className="h-10 flex items-center justify-between px-5 border-b border-zinc-800/50 bg-[#18181b]/50">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
          <Search className="w-3 h-3" />
          Network Search
        </span>
      </div>

      <div className="p-5 border-b border-zinc-800/50">
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setPlatform('all')}
            className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
              platform === 'all'
                ? 'bg-blue-500 text-white'
                : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            }`}
          >
            全部
          </button>
          <button
            onClick={() => setPlatform('bilibili')}
            className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
              platform === 'bilibili'
                ? 'bg-blue-500 text-white'
                : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            }`}
          >
            B站
          </button>
          <button
            onClick={() => setPlatform('youtube')}
            className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
              platform === 'youtube'
                ? 'bg-blue-500 text-white'
                : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            }`}
          >
            YouTube
          </button>
        </div>

        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSearching}
            placeholder="搜索网络视频..."
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 pl-3 pr-10 text-xs text-white focus:border-zinc-500 outline-none disabled:opacity-50"
          />
          <button
            onClick={handleSearch}
            disabled={isSearching || !query.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-zinc-800 rounded transition-colors disabled:opacity-50"
          >
            {isSearching ? (
              <RefreshCw className="w-4 h-4 text-zinc-400 animate-spin" />
            ) : (
              <Search className="w-4 h-4 text-zinc-400" />
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scroller p-5">
        {!networkSearchTask && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Search className="w-12 h-12 text-zinc-700 mb-4" />
            <p className="text-sm text-zinc-500 mb-2">搜索网络视频</p>
            <p className="text-xs text-zinc-600">支持 B站、YouTube 等平台</p>
          </div>
        )}

        {networkSearchTask && networkSearchTask.status === 'searching' && (
          <div className="flex flex-col items-center justify-center h-full">
            <RefreshCw className="w-8 h-8 text-zinc-600 animate-spin mb-3" />
            <p className="text-sm text-zinc-500">{networkSearchTask.message}</p>
          </div>
        )}

        {networkSearchTask && networkSearchTask.status === 'completed' && networkSearchTask.results && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-400">
                找到 {networkSearchTask.results.length} 个结果
              </span>
              {selectedVideos.length > 0 && (
                <button
                  onClick={handleImportSelected}
                  className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-xs transition-colors"
                >
                  导入选中 ({selectedVideos.length})
                </button>
              )}
            </div>

            <div className="space-y-2">
              {networkSearchTask.results.map((video, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-xl border transition-all ${
                    selectedVideos.includes(video.url)
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-zinc-800 bg-zinc-900/50 hover:border-zinc-700'
                  }`}
                >
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        if (selectedVideos.includes(video.url)) {
                          setSelectedVideos(selectedVideos.filter(v => v !== video.url))
                        } else {
                          setSelectedVideos([...selectedVideos, video.url])
                        }
                      }}
                      className={`w-16 h-12 rounded-lg bg-zinc-800 flex items-center justify-center shrink-0 transition-colors ${
                        selectedVideos.includes(video.url) ? 'ring-2 ring-blue-500' : ''
                      }`}
                    >
                      {selectedVideos.includes(video.url) ? (
                        <span className="text-blue-400 text-xs">✓</span>
                      ) : (
                        <Play className="w-4 h-4 text-zinc-600" />
                      )}
                    </button>

                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm text-white font-medium truncate mb-1">
                        {video.title}
                      </h4>
                      <div className="flex items-center gap-2 text-xs text-zinc-500">
                        <span>{video.platform}</span>
                        <span>·</span>
                        <span>{video.author}</span>
                        {video.duration && (
                          <>
                            <span>·</span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {video.duration}
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    <a
                      href={video.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 hover:bg-zinc-800 rounded-lg transition-colors shrink-0"
                    >
                      <ExternalLink className="w-4 h-4 text-zinc-500" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {networkSearchTask && networkSearchTask.status === 'error' && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-3">
              <p className="text-sm text-red-400">{networkSearchTask.error}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
