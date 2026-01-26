import { useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Search, Play, RefreshCw, ExternalLink, Clock, FileText, Download } from 'lucide-react'
import { IngestAPI } from '@/api/modules/ingest'
import type {
  SearchResultItem,
  Platform,
  ContentType
} from '@/types/modules/ingest'

/**
 * Ingest Panel - 多平台内容搜索面板
 *
 * 功能：
 * - 搜索多平台内容（B站、YouTube、arXiv论文）
 * - 显示搜索结果（视频、论文）
 * - 导入选中内容到系统
 * - 查看导入进度
 */
interface PlatformOption {
  id: Platform
  name: string
  icon: React.ReactNode
  contentType: ContentType
}

const PLATFORM_OPTIONS: PlatformOption[] = [
  {
    id: 'bilibili',
    name: 'B站',
    icon: <Play className="w-3 h-3" />,
    contentType: 'video'
  },
  {
    id: 'youtube',
    name: 'YouTube',
    icon: <Play className="w-3 h-3" />,
    contentType: 'video'
  },
  {
    id: 'arxiv',
    name: 'arXiv',
    icon: <FileText className="w-3 h-3" />,
    contentType: 'paper'
  }
]

export function IngestPanel() {
  const { networkSearchTask, setNetworkSearchTask, fetchSources } = useAppStore()
  const [query, setQuery] = useState('')
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>(['bilibili', 'youtube', 'arxiv'])
  const [contentType, setContentType] = useState<ContentType>('all')
  const [isSearching, setIsSearching] = useState(false)
  const [selectedItems, setSelectedItems] = useState<string[]>([])
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([])

  const togglePlatform = (platform: Platform) => {
    setSelectedPlatforms(prev =>
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    )
  }

  const handleSearch = async () => {
    if (!query.trim() || isSearching || selectedPlatforms.length === 0) return

    setIsSearching(true)
    setSearchResults([])

    try {
      const response = await IngestAPI.extendedSearch({
        query,
        platforms: selectedPlatforms,
        max_results: 10,
        content_type: contentType
      })

      setSearchResults(response.results)

      setNetworkSearchTask({
        task_id: `search_${Date.now()}`,
        status: 'completed',
        progress: 100,
        message: `找到 ${response.total_count} 个结果`,
        results: response.results as any,
        error: undefined
      })
    } catch (error) {
      console.error('Failed to search:', error)
      setNetworkSearchTask({
        task_id: `search_${Date.now()}`,
        status: 'error',
        progress: 0,
        message: '搜索失败',
        results: [],
        error: error instanceof Error ? error.message : '未知错误'
      })
    } finally {
      setIsSearching(false)
    }
  }

  const handleImportSelected = async () => {
    if (selectedItems.length === 0 || searchResults.length === 0) return

    const itemsToImport = searchResults.filter(item =>
      selectedItems.includes(item.id)
    )

    // Import each item using fetch API
    for (const item of itemsToImport) {
      try {
        const response = await IngestAPI.fetchContent({
          content_id: item.id,
          platform: item.platform as Platform,
          auto_analyze: true
        })

        console.log(`Import started for ${item.id}:`, response.task_id)

        // Poll for completion
        const pollImport = async () => {
          let attempts = 0
          while (attempts < 30) {
            await new Promise(resolve => setTimeout(resolve, 2000))
            try {
              const status = await IngestAPI.getTaskStatus(response.task_id)
              if (status.status === 'completed' || status.status === 'error') {
                if (status.status === 'completed') {
                  console.log(`Import completed for ${item.id}`)
                  await fetchSources()
                }
                break
              }
            } catch (e) {
              console.error('Error polling import status:', e)
              break
            }
            attempts++
          }
        }

        // Start polling in background
        pollImport()
      } catch (error) {
        console.error(`Failed to import ${item.id}:`, error)
      }
    }

    setSelectedItems([])
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const getPlatformIcon = (platform: string) => {
    const option = PLATFORM_OPTIONS.find(opt => opt.id === platform)
    return option?.icon || <Play className="w-3 h-3" />
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return ''
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-5 border-b border-zinc-800/50">
        {/* Platform selection */}
        <div className="flex flex-wrap gap-2 mb-3">
          {PLATFORM_OPTIONS.map(option => (
            <button
              key={option.id}
              onClick={() => togglePlatform(option.id)}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors flex items-center gap-1.5 ${
                selectedPlatforms.includes(option.id)
                  ? 'bg-blue-500 text-white'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              }`}
            >
              {option.icon}
              {option.name}
            </button>
          ))}
        </div>

        {/* Content type filter */}
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setContentType('all')}
            className={`px-2 py-1 rounded text-xs transition-colors ${
              contentType === 'all'
                ? 'bg-zinc-700 text-white'
                : 'text-zinc-500 hover:text-zinc-400'
            }`}
          >
            全部
          </button>
          <button
            onClick={() => setContentType('video')}
            className={`px-2 py-1 rounded text-xs transition-colors ${
              contentType === 'video'
                ? 'bg-zinc-700 text-white'
                : 'text-zinc-500 hover:text-zinc-400'
            }`}
          >
            视频
          </button>
          <button
            onClick={() => setContentType('paper')}
            className={`px-2 py-1 rounded text-xs transition-colors ${
              contentType === 'paper'
                ? 'bg-zinc-700 text-white'
                : 'text-zinc-500 hover:text-zinc-400'
            }`}
          >
            论文
          </button>
        </div>

        {/* Search input */}
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isSearching}
            placeholder="搜索视频、论文、文章..."
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 pl-3 pr-10 text-xs text-white focus:border-zinc-500 outline-none disabled:opacity-50"
          />
          <button
            onClick={handleSearch}
            disabled={isSearching || !query.trim() || selectedPlatforms.length === 0}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-zinc-800 rounded transition-colors disabled:opacity-50"
          >
            {isSearching ? (
              <RefreshCw className="w-4 h-4 text-zinc-400 animate-spin" />
            ) : (
              <Search className="w-4 h-4 text-zinc-400" />
            )}
          </button>
        </div>

        {/* Selected platforms hint */}
        {selectedPlatforms.length > 0 && (
          <div className="mt-2 text-xs text-zinc-500">
            搜索平台: {selectedPlatforms.map(p => PLATFORM_OPTIONS.find(opt => opt.id === p)?.name).join('、')}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto scroller p-5">
        {!searchResults || searchResults.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Search className="w-12 h-12 text-zinc-700 mb-4" />
            <p className="text-sm text-zinc-500 mb-2">搜索多平台内容</p>
            <p className="text-xs text-zinc-600">支持 B站、YouTube 视频和 arXiv 论文</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-400">
                找到 {searchResults.length} 个结果
              </span>
              {selectedItems.length > 0 && (
                <button
                  onClick={handleImportSelected}
                  className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-xs transition-colors flex items-center gap-1.5"
                >
                  <Download className="w-3 h-3" />
                  导入选中 ({selectedItems.length})
                </button>
              )}
            </div>

            <div className="space-y-2">
              {searchResults.map((item) => (
                <div
                  key={item.id}
                  className={`p-3 rounded-xl border transition-all ${
                    selectedItems.includes(item.id)
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-zinc-800 bg-zinc-900/50 hover:border-zinc-700'
                  }`}
                >
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        if (selectedItems.includes(item.id)) {
                          setSelectedItems(selectedItems.filter(id => id !== item.id))
                        } else {
                          setSelectedItems([...selectedItems, item.id])
                        }
                      }}
                      className={`w-16 h-12 rounded-lg bg-zinc-800 flex items-center justify-center shrink-0 transition-colors ${
                        selectedItems.includes(item.id) ? 'ring-2 ring-blue-500' : ''
                      }`}
                    >
                      {selectedItems.includes(item.id) ? (
                        <span className="text-blue-400 text-lg">✓</span>
                      ) : item.content_type === 'paper' ? (
                        <FileText className="w-5 h-5 text-zinc-600" />
                      ) : (
                        <Play className="w-4 h-4 text-zinc-600" />
                      )}
                    </button>

                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm text-white font-medium truncate mb-1">
                        {item.title}
                      </h4>
                      {item.description && (
                        <p className="text-xs text-zinc-500 line-clamp-2 mb-1">
                          {item.description}
                        </p>
                      )}
                      <div className="flex items-center gap-2 text-xs text-zinc-500 flex-wrap">
                        <span className="flex items-center gap-1">
                          {getPlatformIcon(item.platform)}
                          {item.platform}
                        </span>
                        {item.author && (
                          <>
                            <span>·</span>
                            <span>{item.author}</span>
                          </>
                        )}
                        {item.duration && (
                          <>
                            <span>·</span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {formatDuration(item.duration)}
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    <a
                      href={item.url}
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

        {networkSearchTask?.status === 'error' && (
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
