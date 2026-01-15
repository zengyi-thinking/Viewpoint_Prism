import { useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Film, Sparkles, FileText, Play, RefreshCw } from 'lucide-react'
import { CreativeAPI } from '@/api'
import type { SupercutTask, DigestTask } from '@/types/modules/creative'

/**
 * Creative Panel - 创意内容生成面板
 *
 * 功能：
 * - 实体蒙太奇（Supercut）：为指定实体生成混剪视频
 * - 智能浓缩（Digest）：生成视频精华片段
 * - One Pager：单页图文总结
 */
type CreativeTab = 'supercut' | 'digest' | 'onepager'

export function CreativePanel() {
  const { sources, selectedSourceIds, nebula, setActivePlayer } = useAppStore()
  const [activeTab, setActiveTab] = useState<CreativeTab>('supercut')
  const [entityName, setEntityName] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [task, setTask] = useState<SupercutTask | DigestTask | null>(null)

  const selectedSource = selectedSourceIds.length > 0
    ? sources.find(s => s.id === selectedSourceIds[0])
    : null

  const handleCreateSupercut = async () => {
    if (!entityName.trim() || isGenerating) return

    setIsGenerating(true)
    try {
      const response = await CreativeAPI.supercut.create({ entity_name: entityName, top_k: 10 })
      setTask({
        task_id: response.task_id,
        status: response.status as any,
        progress: 0,
        message: response.message,
        entity_name: entityName,
      })

      // 轮询任务状态
      const pollInterval = setInterval(async () => {
        const status = await CreativeAPI.supercut.getStatus(response.task_id)
        setTask(status)

        if (status.status === 'completed' || status.status === 'error') {
          clearInterval(pollInterval)
          setIsGenerating(false)
          if (status.video_url) {
            setActivePlayer('supercut')
          }
        }
      }, 2000)
    } catch (error) {
      console.error('Failed to create supercut:', error)
      setIsGenerating(false)
    }
  }

  const handleCreateDigest = async () => {
    if (!selectedSource || isGenerating) return

    setIsGenerating(true)
    try {
      const response = await CreativeAPI.digest.create({
        source_id: selectedSource.id,
        include_types: ['STORY', 'COMBAT'],
      })
      setTask({
        task_id: response.task_id,
        status: response.status as any,
        progress: 0,
        message: response.message,
        source_id: selectedSource.id,
      })

      const pollInterval = setInterval(async () => {
        const status = await CreativeAPI.digest.getStatus(response.task_id)
        setTask(status)

        if (status.status === 'completed' || status.status === 'error') {
          clearInterval(pollInterval)
          setIsGenerating(false)
          if (status.video_url) {
            setActivePlayer('digest')
          }
        }
      }, 2000)
    } catch (error) {
      console.error('Failed to create digest:', error)
      setIsGenerating(false)
    }
  }

  return (
    <div className="floating-panel flex flex-col h-full bg-[#121214]">
      <div className="h-10 flex items-center justify-between px-5 border-b border-zinc-800/50 bg-[#18181b]/50">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
          <Sparkles className="w-3 h-3" />
          Creative Studio
        </span>
      </div>

      <div className="flex border-b border-zinc-800/50">
        <button
          onClick={() => setActiveTab('supercut')}
          className={`flex-1 py-3 px-4 text-xs font-medium transition-colors border-b-2 ${
            activeTab === 'supercut'
              ? 'border-blue-500 text-white'
              : 'border-transparent text-zinc-500 hover:text-zinc-400'
          }`}
        >
          <Film className="w-3 h-3 inline mr-1" />
          实体蒙太奇
        </button>
        <button
          onClick={() => setActiveTab('digest')}
          className={`flex-1 py-3 px-4 text-xs font-medium transition-colors border-b-2 ${
            activeTab === 'digest'
              ? 'border-blue-500 text-white'
              : 'border-transparent text-zinc-500 hover:text-zinc-400'
          }`}
        >
          <Sparkles className="w-3 h-3 inline mr-1" />
          智能浓缩
        </button>
        <button
          onClick={() => setActiveTab('onepager')}
          className={`flex-1 py-3 px-4 text-xs font-medium transition-colors border-b-2 ${
            activeTab === 'onepager'
              ? 'border-blue-500 text-white'
              : 'border-transparent text-zinc-500 hover:text-zinc-400'
          }`}
        >
          <FileText className="w-3 h-3 inline mr-1" />
          One Pager
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scroller p-5">
        {activeTab === 'supercut' && (
          <div className="space-y-4">
            <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
              <h3 className="text-sm font-bold text-white mb-2">实体蒙太奇</h3>
              <p className="text-xs text-zinc-400 mb-4">
                为指定实体生成混剪视频，汇总该实体在所有视频中的出现片段
              </p>

              <div className="space-y-3">
                <input
                  type="text"
                  value={entityName}
                  onChange={(e) => setEntityName(e.target.value)}
                  placeholder="输入实体名称（如：某个角色、物品、地点）"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2.5 px-3 text-xs text-white focus:border-zinc-500 outline-none"
                />

                <button
                  onClick={handleCreateSupercut}
                  disabled={isGenerating || !entityName.trim()}
                  className="w-full py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg flex items-center justify-center gap-2 text-xs transition-colors"
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      生成中...
                    </>
                  ) : (
                    <>
                      <Film className="w-3 h-3" />
                      生成实体蒙太奇
                    </>
                  )}
                </button>
              </div>
            </div>

            {task && task.task_id && (
              <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-zinc-400">生成进度</span>
                  <span className="text-xs text-zinc-500">{task.progress}%</span>
                </div>
                <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden mb-3">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
                <p className="text-xs text-zinc-500 mb-3">{task.message}</p>

                {task.status === 'completed' && task.video_url && (
                  <button
                    onClick={() => setActivePlayer('supercut')}
                    className="w-full py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg flex items-center justify-center gap-2 text-xs transition-colors"
                  >
                    <Play className="w-3 h-3" />
                    播放蒙太奇视频
                  </button>
                )}

                {task.status === 'error' && task.error && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <p className="text-xs text-red-400">{task.error}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'digest' && (
          <div className="space-y-4">
            {!selectedSource && (
              <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
                <p className="text-sm text-zinc-500 text-center">请先选择一个视频源</p>
              </div>
            )}

            {selectedSource && (
              <>
                <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
                  <h3 className="text-sm font-bold text-white mb-2">智能浓缩</h3>
                  <p className="text-xs text-zinc-400 mb-2">
                    提取视频精华片段，生成紧凑的浓缩版本
                  </p>
                  <p className="text-xs text-zinc-500">当前视频: {selectedSource.title}</p>

                  <button
                    onClick={handleCreateDigest}
                    disabled={isGenerating}
                    className="mt-4 w-full py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg flex items-center justify-center gap-2 text-xs transition-colors"
                  >
                    {isGenerating ? (
                      <>
                        <RefreshCw className="w-3 h-3 animate-spin" />
                        生成中...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3 h-3" />
                        生成智能浓缩
                      </>
                    )}
                  </button>
                </div>

                {task && task.task_id && (
                  <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs text-zinc-400">生成进度</span>
                      <span className="text-xs text-zinc-500">{task.progress}%</span>
                    </div>
                    <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden mb-3">
                      <div
                        className="h-full bg-blue-500 transition-all duration-300"
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-zinc-500">{task.message}</p>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'onepager' && (
          <div className="space-y-4">
            <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
              <h3 className="text-sm font-bold text-white mb-2">One Pager</h3>
              <p className="text-xs text-zinc-400 mb-4">
                生成单页图文总结，包含关键洞察、证据和视觉化内容
              </p>

              {selectedSourceIds.length > 0 ? (
                <button
                  disabled={isGenerating}
                  className="w-full py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg flex items-center justify-center gap-2 text-xs transition-colors"
                >
                  <FileText className="w-3 h-3" />
                  生成 One Pager
                </button>
              ) : (
                <p className="text-xs text-zinc-500 text-center">请先选择至少一个视频源</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
