import React, { useCallback, useRef, useState, useEffect } from 'react'
import { useAppStore } from '@/stores/app-store'
import { SourceAPI } from '@/api/modules/source'
import { Upload, Trash2, Play, RefreshCw, Search, Video, CheckSquare, Square } from 'lucide-react'

interface SourcesPanelProps {
  onSelectSource?: (sourceId: string) => void
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export function SourcesPanel({ onSelectSource }: SourcesPanelProps) {
  const {
    sources,
    selectedSourceIds,
    currentSourceId,
    uploadState,
    setUploadState,
    toggleSourceSelection,
    setCurrentSource,
    fetchSources,
    uploadVideo,
    deleteSource,
    reprocessSource,
    analyzeSource,
  } = useAppStore()

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null)

  // Poll for status updates when sources are processing
  useEffect(() => {
    const hasProcessing = sources.some(s => s.status === 'processing' || s.status === 'analyzing')
    if (!hasProcessing) return

    const interval = setInterval(() => {
      fetchSources()
    }, 3000) // Poll every 3 seconds

    return () => clearInterval(interval)
  }, [sources, fetchSources])

  // Show notification and auto-hide
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [notification])

  const handleFileSelect = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const source = await uploadVideo(file)
      if (source) {
        setNotification({ type: 'success', message: `已上传: ${source.title}` })
        // Refresh sources to get updated status
        fetchSources()
      } else {
        setNotification({ type: 'error', message: '上传失败' })
      }
    } catch (error) {
      setNotification({ type: 'error', message: '上传失败' })
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [uploadVideo, fetchSources])

  const handleDrop = useCallback(async (event: React.DragEvent) => {
    event.preventDefault()
    const file = event.dataTransfer.files[0]
    if (!file || !file.type.startsWith('video/')) {
      setUploadState({ error: '请上传视频文件' })
      return
    }
    await uploadVideo(file)
  }, [uploadVideo, setUploadState])

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
  }, [])

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      fetchSources()
      return
    }
    setIsSearching(true)
    try {
      const data = await SourceAPI.search(searchQuery)
      useAppStore.getState().setSources(data.sources)
    } catch (error) {
      console.error('Search failed:', error)
    }
    setIsSearching(false)
  }, [searchQuery, fetchSources])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'done':
        return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'processing':
      case 'analyzing':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      case 'error':
        return 'bg-red-500/20 text-red-400 border-red-500/30'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'done':
        return '已完成'
      case 'processing':
        return '处理中'
      case 'analyzing':
        return '分析中'
      case 'error':
        return '错误'
      case 'uploaded':
        return '已上传'
      case 'imported':
        return '已导入'
      default:
        return status
    }
  }

  return (
    <div className="flex flex-col h-full bg-zinc-900/40">
      <div className="p-4 border-b border-zinc-800/50">
        <h2 className="text-lg font-semibold text-white mb-4">视频源</h2>

        <div
          className="border-2 border-dashed border-zinc-700 rounded-lg p-6 text-center hover:border-zinc-600 transition-colors cursor-pointer"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={handleFileSelect}
            className="hidden"
          />
          <Upload className="w-8 h-8 mx-auto text-zinc-400 mb-2" />
          <p className="text-sm text-zinc-400">
            {uploadState.isUploading
              ? `上传中 ${uploadState.progress.toFixed(0)}%`
              : '拖拽视频到此处，或点击上传'}
          </p>
          {uploadState.error && (
            <p className="text-sm text-red-400 mt-2">{uploadState.error}</p>
          )}
        </div>

        {notification && (
          <div className={`mt-3 p-3 rounded-lg flex items-center gap-2 ${
            notification.type === 'success' 
              ? 'bg-green-500/20 border border-green-500/30' 
              : 'bg-red-500/20 border border-red-500/30'
          }`}>
            <span className={notification.type === 'success' ? 'text-green-400' : 'text-red-400'}>
              {notification.type === 'success' ? '✓' : '!'}
            </span>
            <span className="text-sm text-white">{notification.message}</span>
          </div>
        )}

        <div className="mt-4 flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="搜索视频..."
              className="w-full bg-zinc-800/50 border border-zinc-700/50 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-600"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={isSearching}
            className="px-3 py-2 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg text-sm disabled:opacity-50"
          >
            {isSearching ? '搜索中...' : '搜索'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {sources.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">
            <Video className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">暂无视频源</p>
            <p className="text-xs mt-1">上传或搜索视频开始分析</p>
          </div>
        ) : (
          <div className="space-y-2">
            {sources.map((source) => (
              <div
                key={source.id}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  currentSourceId === source.id
                    ? 'bg-zinc-800/80 border-zinc-700/50'
                    : 'bg-zinc-800/30 border-zinc-700/30 hover:border-zinc-600'
                }`}
                onClick={(e) => {
                  // Don't trigger when clicking on buttons
                  if (!(e.target as HTMLElement).closest('button')) {
                    setCurrentSource(source.id)
                    onSelectSource?.(source.id)
                  }
                }}
              >
                <div className="flex items-start gap-3">
                  {/* 复选框 */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleSourceSelection(source.id)
                    }}
                    className={`flex-shrink-0 mt-0.5 rounded border ${
                      selectedSourceIds.includes(source.id)
                        ? 'bg-zinc-600 border-zinc-600 text-white'
                        : 'border-zinc-600 hover:border-zinc-500'
                    }`}
                  >
                    {selectedSourceIds.includes(source.id) ? (
                      <CheckSquare className="w-4 h-4" />
                    ) : (
                      <Square className="w-4 h-4 text-zinc-500" />
                    )}
                  </button>

                  {/* 内容区 */}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-white truncate">
                      {source.title}
                    </h3>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${getStatusColor(source.status)}`}>
                        {getStatusText(source.status)}
                      </span>
                      {source.duration && (
                        <span className="text-xs text-zinc-500">
                          {formatDuration(source.duration)}
                        </span>
                      )}
                      <span className="text-xs text-zinc-600 capitalize">
                        {source.platform}
                      </span>
                    </div>
                  </div>

                  {/* 操作按钮 */}
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (source.status === 'done' || source.status === 'error') {
                          analyzeSource(source.id)
                        } else {
                          reprocessSource(source.id)
                        }
                      }}
                      className="p-1.5 rounded hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300"
                      title={source.status === 'done' ? '重新分析' : '分析'}
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteSource(source.id)
                      }}
                      className="p-1.5 rounded hover:bg-zinc-700 text-zinc-500 hover:text-red-400"
                      title="删除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="p-2 border-t border-zinc-800/50">
        <div className="text-xs text-zinc-500 text-center">
          {sources.length} 个视频源
        </div>
      </div>
    </div>
  )
}
