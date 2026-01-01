import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Search, Film, FileText, Clock, Loader2, X, Trash2, RotateCcw, Globe, ArrowRight, Plus, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

export function SourcesPanel() {
  const {
    sources,
    selectedSourceIds,
    currentSourceId,
    toggleSourceSelection,
    setCurrentSource,
    language,
    uploadState,
    uploadVideo,
    fetchSources,
    deleteSource,
    reprocessSource,
    analyzeSource,  // Phase 12: Add analyzeSource action
    networkSearchTask,
    startNetworkSearch,
    setNetworkSearchTask,
  } = useAppStore()

  const [searchKeyword, setSearchKeyword] = useState('')
  const [filterText, setFilterText] = useState('')
  const [isSearchHovered, setIsSearchHovered] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Fetch sources on mount and poll for updates
  useEffect(() => {
    fetchSources()

    // Poll for status updates every 5 seconds if any source is processing/analyzing
    const interval = setInterval(() => {
      const hasProcessing = sources.some(
        (s) => s.status === 'processing' || s.status === 'analyzing' || s.status === 'uploaded'
      )
      if (hasProcessing) {
        fetchSources()
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [fetchSources, sources])

  const filteredSources = sources.filter((source) =>
    source.title.toLowerCase().includes(filterText.toLowerCase())
  )

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      await uploadVideo(file)
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleSearchSubmit = async () => {
    const keyword = searchKeyword.trim()
    if (!keyword) return

    // For web search, default to YouTube
    await startNetworkSearch('yt', keyword, 3)
    setSearchKeyword('')
  }

  const handleSearchKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      await handleSearchSubmit()
    }
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '--:--'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'imported':
        // Phase 12: New status for imported but not yet analyzed sources
        return (
          <span className="text-[9px] text-zinc-400 bg-zinc-500/10 px-1.5 py-0.5 rounded-full border border-zinc-500/20 flex items-center gap-1">
            待分析
          </span>
        )
      case 'uploaded':
        return (
          <span className="text-[9px] text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded-full flex items-center gap-1">
            <Loader2 className="w-2 h-2 animate-spin" />
            等待处理
          </span>
        )
      case 'processing':
        return (
          <span className="text-[9px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded-full flex items-center gap-1">
            <Loader2 className="w-2 h-2 animate-spin" />
            提取中
          </span>
        )
      case 'analyzing':
        return (
          <span className="text-[9px] text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded-full flex items-center gap-1">
            <Loader2 className="w-2 h-2 animate-spin" />
            AI分析中
          </span>
        )
      case 'done':
        return (
          <span className="text-[9px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full">
            就绪
          </span>
        )
      case 'error':
        return (
          <span className="text-[9px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded-full">
            错误
          </span>
        )
      default:
        return null
    }
  }

  const t = {
    zh: {
      title: 'Sources',
      addSources: '+ Add sources',
      searchPlaceholder: 'Search the web for new sources',
      deepResearch: 'Try Deep Research for an in-depth report...',
      selectAll: 'Select all sources',
      filterPlaceholder: 'Filter list...',
      noSources: '暂无视频源',
      uploadHint: '添加源以开始分析',
      uploading: '上传中...',
      webSearch: 'Web',
    },
    en: {
      title: 'Sources',
      addSources: '+ Add sources',
      searchPlaceholder: 'Search the web for new sources',
      deepResearch: 'Try Deep Research for an in-depth report...',
      selectAll: 'Select all sources',
      filterPlaceholder: 'Filter list...',
      noSources: 'No sources yet',
      uploadHint: 'Add sources to get started',
      uploading: 'Uploading...',
      webSearch: 'Web',
    },
  }

  const text = t[language]

  return (
    <aside className="floating-panel flex flex-col h-full">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Header - Fixed Title "Sources" */}
      <div className="px-5 pt-5 pb-2">
        <h2 className="text-sm font-semibold text-zinc-100 tracking-tight">
          {text.title}
        </h2>
      </div>

      {/* Add Sources Button - Full Width */}
      <div className="px-4 pb-3">
        <button
          onClick={handleUploadClick}
          disabled={uploadState.isUploading}
          className={cn(
            "w-full flex items-center justify-center gap-2 text-sm font-medium py-2.5 px-4 rounded-full transition-all",
            "bg-zinc-800 hover:bg-zinc-700 border border-zinc-700/50 hover:border-zinc-600",
            "text-zinc-300 hover:text-zinc-100",
            uploadState.isUploading && "opacity-50 cursor-not-allowed"
          )}
        >
          {uploadState.isUploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{text.uploading}</span>
            </>
          ) : (
            <>
              <Plus className="w-4 h-4" />
              <span>{text.addSources}</span>
            </>
          )}
        </button>
      </div>

      {/* Deep Research Banner (Optional) */}
      <div className="px-4 pb-3">
        <button className="w-full group relative overflow-hidden rounded-xl bg-gradient-to-r from-violet-500/10 to-purple-500/10 border border-violet-500/20 hover:border-violet-500/30 transition-all p-3">
          <div className="absolute inset-0 bg-gradient-to-r from-violet-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-violet-400" />
            <span className="text-xs text-zinc-300">{text.deepResearch}</span>
          </div>
        </button>
      </div>

      {/* Conversational Search Area - NotebookLM Style */}
      <div className="px-4 pb-3">
        <div
          className={cn(
            "relative rounded-xl bg-zinc-800/50 border transition-all",
            isSearchHovered ? "border-zinc-600 bg-zinc-800/70" : "border-zinc-700/50"
          )}
          onMouseEnter={() => setIsSearchHovered(true)}
          onMouseLeave={() => setIsSearchHovered(false)}
        >
          {/* Search Container */}
          <div className="flex items-start gap-2 p-3">
            {/* Search Icon */}
            <Search className="w-5 h-5 text-zinc-500 mt-0.5 shrink-0" />

            {/* Input Container */}
            <div className="flex-1 min-w-0">
              <input
                ref={searchInputRef}
                type="text"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                className="w-full bg-transparent border-none outline-none text-sm text-zinc-200 placeholder-zinc-500"
                placeholder={text.searchPlaceholder}
              />

              {/* Optional: Bottom Row with Quick Tags */}
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] text-zinc-500 bg-zinc-700/50 px-2 py-0.5 rounded-full">
                  {text.webSearch}
                </span>
              </div>
            </div>

            {/* Submit Button */}
            <button
              onClick={handleSearchSubmit}
              disabled={!searchKeyword.trim() || uploadState.isUploading || networkSearchTask?.status === 'searching' || networkSearchTask?.status === 'downloading' || networkSearchTask?.status === 'ingesting'}
              className={cn(
                "shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all mt-0.5",
                (searchKeyword.trim() && !uploadState.isUploading && networkSearchTask?.status !== 'searching' && networkSearchTask?.status !== 'downloading' && networkSearchTask?.status !== 'ingesting')
                  ? "bg-blue-500 hover:bg-blue-400 text-white"
                  : "bg-zinc-700 text-zinc-500 cursor-not-allowed"
              )}
            >
              {(uploadState.isUploading || networkSearchTask?.status === 'searching' || networkSearchTask?.status === 'downloading' || networkSearchTask?.status === 'ingesting') ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Network Search Task Status */}
        {networkSearchTask && (
          <div className={cn(
            "mt-2 p-2 rounded-lg border text-[11px] transition-all",
            networkSearchTask.status === 'error'
              ? "bg-red-500/10 border-red-500/20 text-red-400"
              : networkSearchTask.status === 'completed'
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : "bg-blue-500/10 border-blue-500/20 text-blue-400"
          )}>
            <div className="flex items-center gap-2">
              {(networkSearchTask.status === 'searching' ||
               networkSearchTask.status === 'downloading' ||
               networkSearchTask.status === 'ingesting' ||
               networkSearchTask.status === 'pending') ? (
                <Loader2 className="w-3 h-3 animate-spin shrink-0" />
              ) : networkSearchTask.status === 'error' ? (
                <X className="w-3 h-3 shrink-0" />
              ) : (
                <Globe className="w-3 h-3 shrink-0" />
              )}
              <span className="flex-1 truncate">{networkSearchTask.message}</span>
              {networkSearchTask.status === 'error' && (
                <button
                  onClick={() => setNetworkSearchTask(null)}
                  className="shrink-0 hover:opacity-70"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
            {networkSearchTask.status !== 'error' &&
             networkSearchTask.status !== 'completed' && (
              <div className="mt-1.5 h-0.5 bg-zinc-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-400 transition-all duration-300"
                  style={{ width: `${networkSearchTask.progress}%` }}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="w-full h-[1px] bg-zinc-800/50" />

      {/* Sources List Header with Select All */}
      <div className="px-4 py-2 flex items-center gap-2">
        <input
          type="checkbox"
          checked={selectedSourceIds.length === filteredSources.length && filteredSources.length > 0}
          onChange={(e) => {
            if (e.target.checked) {
              // Select all sources that are not 'imported' status
              filteredSources.forEach(source => {
                if (source.status !== 'imported' && !selectedSourceIds.includes(source.id)) {
                  toggleSourceSelection(source.id)
                }
              })
            } else {
              // Deselect all
              selectedSourceIds.forEach(id => {
                toggleSourceSelection(id)
              })
            }
          }}
          className="w-4 h-4 bg-zinc-800 border border-zinc-600 rounded cursor-pointer accent-zinc-500"
        />
        <span className="text-xs text-zinc-400">{text.selectAll}</span>
        <span className="text-xs text-zinc-600 ml-auto">
          {selectedSourceIds.length}/{filteredSources.length}
        </span>
      </div>

      {/* Source List */}
      <div className="flex-1 overflow-y-auto scroller px-3 pb-2 space-y-1">
        {filteredSources.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-zinc-500 py-8">
            <Film className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">{text.noSources}</p>
            <p className="text-xs mt-1 text-zinc-600">{text.uploadHint}</p>
          </div>
        ) : (
          filteredSources.map((source) => (
            <div
              key={source.id}
              onClick={() => setCurrentSource(source.id)}
              className={cn(
                'source-card p-3 flex items-center gap-3 cursor-pointer group relative rounded-lg transition-all',
                currentSourceId === source.id && 'active shadow-sm bg-zinc-800/50',
                source.status === 'imported' && 'border border-dashed border-zinc-700'
              )}
            >
              <input
                type="checkbox"
                checked={selectedSourceIds.includes(source.id)}
                onChange={(e) => {
                  e.stopPropagation()
                  if (source.status === 'imported') {
                    analyzeSource(source.id)
                  } else {
                    toggleSourceSelection(source.id)
                  }
                }}
                className={cn(
                  "w-4 h-4 bg-zinc-800 border rounded cursor-pointer shrink-0",
                  source.status === 'imported'
                    ? "border-zinc-600 border-dashed"
                    : "accent-zinc-500 border-zinc-600"
                )}
                title={
                  source.status === 'imported'
                    ? "点击开始分析"
                    : selectedSourceIds.includes(source.id)
                    ? "取消选择"
                    : "选择"
                }
              />
              <div className="w-10 h-10 rounded-lg bg-zinc-800/50 flex items-center justify-center shrink-0 border border-zinc-700/50 text-zinc-400 group-hover:text-white transition-colors group-hover:border-zinc-600">
                {source.file_type === 'video' ? (
                  <Film className="w-5 h-5" />
                ) : (
                  <FileText className="w-5 h-5" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-zinc-200 font-medium truncate group-hover:text-white">
                    {source.title}
                  </span>
                  {getStatusBadge(source.status)}
                </div>
                <div className="text-[10px] text-zinc-500 flex items-center gap-2 mt-0.5">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDuration(source.duration)}
                  </span>
                  <span className="text-zinc-600">•</span>
                  <span>{source.platform}</span>
                </div>
              </div>
              {/* Action buttons */}
              <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-all">
                {(source.status === 'done' || source.status === 'error') && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      reprocessSource(source.id)
                    }}
                    className="p-1.5 rounded-lg hover:bg-blue-500/20 text-zinc-500 hover:text-blue-400 transition-all"
                    title="重新处理视频（重新索引内容）"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteSource(source.id)
                  }}
                  className="p-1.5 rounded-lg hover:bg-red-500/20 text-zinc-500 hover:text-red-400 transition-all"
                  title="删除视频"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Filter Footer */}
      <div className="p-3 border-t border-zinc-800/50 bg-zinc-900/30">
        <div className="relative group">
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="input-industrial w-full rounded-lg py-2 px-3 text-xs text-zinc-400 focus:text-white bg-zinc-900/50 border-zinc-800/50"
            placeholder={text.filterPlaceholder}
          />
        </div>
      </div>
    </aside>
  )
}
