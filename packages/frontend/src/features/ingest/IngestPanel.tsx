import { useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Search, Play, RefreshCw, ExternalLink, Clock, FileText, Download, CheckSquare, Square } from 'lucide-react'
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
  const [importingItems, setImportingItems] = useState<Set<string>>(new Set())
  const [importStatus, setImportStatus] = useState<Record<string, string>>({})

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

    // 开始导入，更新状态
    setImportingItems(new Set(selectedItems))
    setImportStatus({})
    setSelectedItems([])

    // 导入每个项目
    for (const item of itemsToImport) {
      try {
        setImportStatus(prev => ({
          ...prev,
          [item.id]: '正在导入...'
        }))

        const response = await IngestAPI.fetchContent({
          content_id: item.id,
          platform: item.platform as Platform,
          auto_analyze: true
        })

        console.log(`Import started for ${item.id}:`, response.task_id)

        // 轮询完成状态
        const pollImport = async () => {
          let attempts = 0
          while (attempts < 60) { // 最多等待2分钟
            await new Promise(resolve => setTimeout(resolve, 2000))
            try {
              const status = await IngestAPI.getTaskStatus(response.task_id)

              if (status.status === 'completed') {
                setImportStatus(prev => ({
                  ...prev,
                  [item.id]: '✓ 导入成功'
                }))

                // 移除从导入中列表
                setImportingItems(prev => {
                  const newSet = new Set(prev)
                  newSet.delete(item.id)
                  return newSet
                })

                // 刷新源列表
                await fetchSources()
                break
              } else if (status.status === 'error') {
                setImportStatus(prev => ({
                  ...prev,
                  [item.id]: '✗ 导入失败'
                }))
                setImportingItems(prev => {
                  const newSet = new Set(prev)
                  newSet.delete(item.id)
                  return newSet
                })
                break
              } else if (status.status === 'processing') {
                setImportStatus(prev => ({
                  ...prev,
                  [item.id]: `处理中... ${status.progress || 0}%`
                }))
              }
            } catch (e) {
              console.error('Error polling import status:', e)
              setImportStatus(prev => ({
                ...prev,
                [item.id]: '✗ 状态查询失败'
              }))
              break
            }
            attempts++
          }

          // 超时处理
          if (attempts >= 60) {
            setImportStatus(prev => ({
              ...prev,
              [item.id]: '⏱ 导入超时'
            }))
            setImportingItems(prev => {
              const newSet = new Set(prev)
              newSet.delete(item.id)
              return newSet
            })
          }
        }

        // 启动后台轮询
        pollImport()
      } catch (error) {
        console.error(`Failed to import ${item.id}:`, error)
        setImportStatus(prev => ({
          ...prev,
          [item.id]: '✗ 启动失败'
        }))
        setImportingItems(prev => {
          const newSet = new Set(prev)
          newSet.delete(item.id)
          return newSet
        })
      }
    }
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
            {/* 结果统计和批量操作栏 */}
            <div className="sticky top-0 bg-zinc-900/95 backdrop-blur-sm p-3 -mx-5 border-b border-zinc-800/50 z-10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-zinc-400">
                    找到 <span className="text-white font-medium">{searchResults.length}</span> 个结果
                  </span>
                  {/* 全选/取消全选按钮 */}
                  <button
                    onClick={() => {
                      if (selectedItems.length === searchResults.length) {
                        setSelectedItems([])
                      } else {
                        setSelectedItems(searchResults.map(item => item.id))
                      }
                    }}
                    className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                  >
                    {selectedItems.length === searchResults.length ? '取消全选' : '全选'}
                  </button>
                </div>

                {/* 导入按钮 - 始终显示，没有选中时禁用 */}
                <button
                  onClick={handleImportSelected}
                  disabled={selectedItems.length === 0}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                    selectedItems.length > 0
                      ? 'bg-blue-500 hover:bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                      : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                  }`}
                >
                  <Download className="w-4 h-4" />
                  {selectedItems.length > 0 ? `导入选中 (${selectedItems.length})` : '请先勾选内容'}
                </button>
              </div>

              {/* 勾选提示 */}
              {selectedItems.length === 0 && (
                <p className="text-xs text-zinc-600 mt-2">
                  💡 点击每项左侧的复选框勾选要导入的内容
                </p>
              )}
            </div>

            <div className="space-y-2">
              {searchResults.map((item) => (
                <div
                  key={item.id}
                  className={`group relative p-3 rounded-xl border transition-all ${
                    selectedItems.includes(item.id)
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-zinc-800 bg-zinc-900/50 hover:border-zinc-700'
                  }`}
                >
                  <div className="flex gap-3">
                    {/* 明显的复选框 */}
                    <button
                      onClick={() => {
                        if (importingItems.has(item.id)) return // 导入中禁止操作
                        if (selectedItems.includes(item.id)) {
                          setSelectedItems(selectedItems.filter(id => id !== item.id))
                        } else {
                          setSelectedItems([...selectedItems, item.id])
                        }
                      }}
                      disabled={importingItems.has(item.id)}
                      className={`w-12 h-12 rounded-lg bg-zinc-800 flex items-center justify-center shrink-0 transition-all ${
                        selectedItems.includes(item.id) ? 'ring-2 ring-blue-500 bg-blue-500/20' :
                        importingItems.has(item.id) ? 'opacity-50 cursor-not-allowed' :
                        'hover:bg-zinc-700'
                      }`}
                      aria-label={
                        importingItems.has(item.id) ? '导入中' :
                        selectedItems.includes(item.id) ? '取消勾选' : '勾选'
                      }
                    >
                      {selectedItems.includes(item.id) ? (
                        <CheckSquare className="w-5 h-5 text-blue-400" />
                      ) : importingItems.has(item.id) ? (
                        <RefreshCw className="w-5 h-5 text-blue-400 animate-spin" />
                      ) : (
                        <Square className="w-5 h-5 text-zinc-600" />
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
                        {/* 导入状态显示 */}
                        {importStatus[item.id] && (
                          <>
                            <span>·</span>
                            <span className={`${
                              importStatus[item.id].includes('✓') ? 'text-green-400' :
                              importStatus[item.id].includes('✗') || importStatus[item.id].includes('超时') ? 'text-red-400' :
                              'text-blue-400'
                            }`}>
                              {importStatus[item.id]}
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
