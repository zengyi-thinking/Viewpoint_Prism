import { useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Swords, Play, RefreshCw } from 'lucide-react'

/**
 * Debate Panel - AI辩论视频生成面板
 *
 * 功能：
 * - 从冲突检测中选择的冲突点
 * - 生成AI辩论视频
 * - 查看生成进度
 * - 播放生成的辩论视频
 */
export function DebatePanel() {
  const {
    conflicts,
    selectedConflictId,
    debateTasks,
    startDebateGeneration,
    pollDebateTask,
    setActivePlayer,
  } = useAppStore()

  const [isGenerating, setIsGenerating] = useState(false)

  const selectedConflict = conflicts.find(c => c.id === selectedConflictId)
  const currentTask = selectedConflictId ? debateTasks[selectedConflictId] : undefined

  const handleStartDebate = async () => {
    if (!selectedConflict || isGenerating) return

    setIsGenerating(true)
    const taskId = await startDebateGeneration(selectedConflictId, selectedConflict)
    setIsGenerating(false)

    if (taskId) {
      // 轮询任务状态
      const pollInterval = setInterval(async () => {
        const updatedTask = await pollDebateTask(taskId)
        if (updatedTask && (updatedTask.status === 'completed' || updatedTask.status === 'error')) {
          clearInterval(pollInterval)
        }
      }, 2000)
    }
  }

  const handlePlayVideo = () => {
    if (currentTask?.video_url) {
      setActivePlayer('debate')
    }
  }

  return (
    <div className="floating-panel flex flex-col h-full bg-[#121214]">
      <div className="h-10 flex items-center justify-between px-5 border-b border-zinc-800/50 bg-[#18181b]/50">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
          <Swords className="w-3 h-3" />
          AI Debate
        </span>
        <div className="flex items-center gap-2">
          {currentTask && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              currentTask.status === 'completed' ? 'bg-green-500/20 text-green-400' :
              currentTask.status === 'error' ? 'bg-red-500/20 text-red-400' :
              'bg-amber-500/20 text-amber-400'
            }`}>
              {currentTask.status}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scroller p-5">
        {!selectedConflict && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Swords className="w-12 h-12 text-zinc-700 mb-4" />
            <p className="text-sm text-zinc-500 mb-2">未选择冲突点</p>
            <p className="text-xs text-zinc-600">请在分析面板中选择一个冲突点来生成辩论视频</p>
          </div>
        )}

        {selectedConflict && (
          <div className="space-y-4">
            <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
              <h3 className="text-sm font-bold text-white mb-2">{selectedConflict.topic}</h3>
              <div className="space-y-2">
                <div className="p-3 bg-zinc-800/50 rounded-lg">
                  <p className="text-xs text-zinc-400 mb-1">观点 A</p>
                  <p className="text-sm text-zinc-300">{selectedConflict.viewpoint_a.title}</p>
                </div>
                <div className="p-3 bg-zinc-800/50 rounded-lg">
                  <p className="text-xs text-zinc-400 mb-1">观点 B</p>
                  <p className="text-sm text-zinc-300">{selectedConflict.viewpoint_b.title}</p>
                </div>
              </div>
            </div>

            {currentTask && (
              <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-zinc-400">生成进度</span>
                  <span className="text-xs text-zinc-500">{currentTask.progress}%</span>
                </div>
                <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden mb-3">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${currentTask.progress}%` }}
                  />
                </div>
                <p className="text-xs text-zinc-500">{currentTask.message}</p>

                {currentTask.status === 'completed' && currentTask.video_url && (
                  <button
                    onClick={handlePlayVideo}
                    className="mt-4 w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg flex items-center justify-center gap-2 text-sm transition-colors"
                  >
                    <Play className="w-4 h-4" />
                    播放辩论视频
                  </button>
                )}

                {currentTask.status === 'error' && (
                  <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <p className="text-xs text-red-400">{currentTask.error}</p>
                  </div>
                )}

                {currentTask.script && (
                  <div className="mt-4 p-3 bg-zinc-800/50 rounded-lg">
                    <p className="text-xs text-zinc-400 mb-2">生成的辩论剧本</p>
                    <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-mono">
                      {currentTask.script}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {!currentTask && (
              <button
                onClick={handleStartDebate}
                disabled={isGenerating}
                className="w-full py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-xl flex items-center justify-center gap-2 text-sm transition-colors"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    正在创建辩论视频...
                  </>
                ) : (
                  <>
                    <Swords className="w-4 h-4" />
                    生成AI辩论
                  </>
                )}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
