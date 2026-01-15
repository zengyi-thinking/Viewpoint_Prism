import { useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Mic, Play, RefreshCw } from 'lucide-react'
import type { Persona } from '@/types/modules/director'

/**
 * Director Panel - AI导演剪辑面板
 *
 * 功能：
 * - 选择解说人设（哈基米、大圣、专业解说）
 * - 从冲突检测中选择的冲突点
 * - 生成AI导演剪辑视频
 * - 查看生成进度和分镜
 * - 播放生成的导演剪辑视频
 */
const PERSONAS: Array<{ id: Persona; name: string; emoji: string; description: string }> = [
  { id: 'hajimi', name: '哈基米', emoji: '🐱', description: '可爱猫娘，活泼激萌' },
  { id: 'wukong', name: '大圣', emoji: '🐵', description: '齐天大圣，狂傲不羁' },
  { id: 'pro', name: '专业解说', emoji: '🎙️', description: '专业分析，冷静客观' },
]

export function DirectorPanel() {
  const {
    conflicts,
    selectedConflictId,
    directorTasks,
    startDirectorGeneration,
    pollDirectorTask,
    setActivePlayer,
  } = useAppStore()

  const [selectedPersona, setSelectedPersona] = useState<Persona>('pro')
  const [isGenerating, setIsGenerating] = useState(false)

  const selectedConflict = conflicts.find(c => c.id === selectedConflictId)
  const currentTask = selectedConflictId ? directorTasks[selectedConflictId] : undefined

  const handleStartDirector = async () => {
    if (!selectedConflict || isGenerating) return

    setIsGenerating(true)
    const taskId = await startDirectorGeneration(selectedConflictId, selectedConflict, selectedPersona)
    setIsGenerating(false)

    if (taskId) {
      // 轮询任务状态
      const pollInterval = setInterval(async () => {
        const updatedTask = await pollDirectorTask(taskId)
        if (updatedTask && (updatedTask.status === 'completed' || updatedTask.status === 'error')) {
          clearInterval(pollInterval)
        }
      }, 2000)
    }
  }

  const handlePlayVideo = () => {
    if (currentTask?.video_url) {
      setActivePlayer('director')
    }
  }

  return (
    <div className="floating-panel flex flex-col h-full bg-[#121214]">
      <div className="h-10 flex items-center justify-between px-5 border-b border-zinc-800/50 bg-[#18181b]/50">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
          <Mic className="w-3 h-3" />
          AI Director
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
        {/* Persona 选择 */}
        <div className="mb-4">
          <p className="text-xs text-zinc-400 mb-3">选择解说人设</p>
          <div className="grid grid-cols-3 gap-2">
            {PERSONAS.map(persona => (
              <button
                key={persona.id}
                onClick={() => setSelectedPersona(persona.id)}
                className={`p-3 rounded-xl border transition-all ${
                  selectedPersona === persona.id
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-zinc-700 bg-zinc-900/50 hover:border-zinc-600'
                }`}
              >
                <span className="text-2xl mb-1 block">{persona.emoji}</span>
                <span className="text-xs text-zinc-300">{persona.name}</span>
              </button>
            ))}
          </div>
        </div>

        {!selectedConflict && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Mic className="w-12 h-12 text-zinc-700 mb-4" />
            <p className="text-sm text-zinc-500 mb-2">未选择冲突点</p>
            <p className="text-xs text-zinc-600">请在分析面板中选择一个冲突点来生成导演剪辑</p>
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
                    className="h-full bg-purple-500 transition-all duration-300"
                    style={{ width: `${currentTask.progress}%` }}
                  />
                </div>
                <p className="text-xs text-zinc-500">{currentTask.message}</p>

                {currentTask.status === 'completed' && currentTask.video_url && (
                  <button
                    onClick={handlePlayVideo}
                    className="mt-4 w-full py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg flex items-center justify-center gap-2 text-sm transition-colors"
                  >
                    <Play className="w-4 h-4" />
                    播放导演剪辑
                  </button>
                )}

                {currentTask.status === 'error' && (
                  <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <p className="text-xs text-red-400">{currentTask.error}</p>
                  </div>
                )}

                {currentTask.storyboard_frames && currentTask.storyboard_frames.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs text-zinc-400 mb-2">分镜预览</p>
                    <div className="grid grid-cols-3 gap-2">
                      {currentTask.storyboard_frames.slice(0, 6).map((frame, idx) => (
                        <div key={idx} className="relative aspect-video bg-zinc-800 rounded-lg overflow-hidden">
                          <img
                            src={frame.image_url}
                            alt={frame.narration}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {currentTask.script && (
                  <div className="mt-4 p-3 bg-zinc-800/50 rounded-lg">
                    <p className="text-xs text-zinc-400 mb-2">生成的解说剧本</p>
                    <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-mono">
                      {currentTask.script}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {!currentTask && (
              <button
                onClick={handleStartDirector}
                disabled={isGenerating}
                className="w-full py-3 bg-purple-500 hover:bg-purple-600 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-xl flex items-center justify-center gap-2 text-sm transition-colors"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    正在生成导演剪辑...
                  </>
                ) : (
                  <>
                    <Mic className="w-4 h-4" />
                    生成AI导演剪辑
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
