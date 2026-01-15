import { useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { BookOpen, Image as ImageIcon, FileText, Play, RefreshCw } from 'lucide-react'
import { StoryAPI } from '@/api'
import type { WebtoonTask } from '@/types/modules/story'

/**
 * Story Panel - 漫画/博客生成面板
 *
 * 功能：
 * - 从视频内容生成条漫（webtoon）
 * - 生成图文博客
 * - 查看生成进度
 * - 浏览生成的分镜和博客内容
 */
export function StoryPanel() {
  const { sources, selectedSourceIds } = useAppStore()
  const [taskId, setTaskId] = useState<string | null>(null)
  const [task, setTask] = useState<WebtoonTask | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [activeTab, setActiveTab] = useState<'panels' | 'blog'>('panels')

  const selectedSource = selectedSourceIds.length > 0
    ? sources.find(s => s.id === selectedSourceIds[0])
    : null

  const handleStartGeneration = async () => {
    if (!selectedSource || isGenerating) return

    setIsGenerating(true)
    try {
      const response = await StoryAPI.generate({ source_id: selectedSource.id })
      setTaskId(response.task_id)
      setTask({
        task_id: response.task_id,
        status: response.status as any,
        progress: response.progress,
        message: response.message,
        panels: response.panels || [],
        total_panels: response.total_panels || 0,
        current_panel: response.current_panel || 0,
        blog_title: response.blog_title,
        blog_sections: response.blog_sections,
        error: response.error,
      })

      // 轮询任务状态
      const pollInterval = setInterval(async () => {
        const updatedTask = await StoryAPI.getTaskStatus(response.task_id)
        setTask({
          task_id: updatedTask.task_id,
          status: updatedTask.status as any,
          progress: updatedTask.progress,
          message: updatedTask.message,
          panels: updatedTask.panels || [],
          total_panels: updatedTask.total_panels || 0,
          current_panel: updatedTask.current_panel || 0,
          blog_title: updatedTask.blog_title,
          blog_sections: updatedTask.blog_sections,
          error: updatedTask.error,
        })

        if (updatedTask.status === 'completed' || updatedTask.status === 'error') {
          clearInterval(pollInterval)
          setIsGenerating(false)
        }
      }, 2000)
    } catch (error) {
      console.error('Failed to start webtoon generation:', error)
      setIsGenerating(false)
    }
  }

  return (
    <div className="floating-panel flex flex-col h-full bg-[#121214]">
      <div className="h-10 flex items-center justify-between px-5 border-b border-zinc-800/50 bg-[#18181b]/50">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
          <BookOpen className="w-3 h-3" />
          Story Generator
        </span>
        <div className="flex items-center gap-2">
          {task && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${
              task.status === 'completed' ? 'bg-green-500/20 text-green-400' :
              task.status === 'error' ? 'bg-red-500/20 text-red-400' :
              'bg-amber-500/20 text-amber-400'
            }`}>
              {task.status}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scroller p-5">
        {!selectedSource && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <BookOpen className="w-12 h-12 text-zinc-700 mb-4" />
            <p className="text-sm text-zinc-500 mb-2">未选择视频源</p>
            <p className="text-xs text-zinc-600">请先选择一个视频源来生成漫画或博客</p>
          </div>
        )}

        {selectedSource && !task && (
          <div className="space-y-4">
            <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
              <h3 className="text-sm font-bold text-white mb-2">{selectedSource.title}</h3>
              <p className="text-xs text-zinc-400">状态: {selectedSource.status}</p>
            </div>

            <button
              onClick={handleStartGeneration}
              disabled={isGenerating}
              className="w-full py-3 bg-orange-500 hover:bg-orange-600 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-xl flex items-center justify-center gap-2 text-sm transition-colors"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  正在生成...
                </>
              ) : (
                <>
                  <BookOpen className="w-4 h-4" />
                  生成漫画博客
                </>
              )}
            </button>
          </div>
        )}

        {task && (
          <div className="space-y-4">
            <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-zinc-400">生成进度</span>
                <span className="text-xs text-zinc-500">{task.progress}%</span>
              </div>
              <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden mb-3">
                <div
                  className="h-full bg-orange-500 transition-all duration-300"
                  style={{ width: `${task.progress}%` }}
                />
              </div>
              <p className="text-xs text-zinc-500">{task.message}</p>
            </div>

            {task.status === 'error' && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-xs text-red-400">{task.error}</p>
              </div>
            )}

            {task.status === 'completed' && task.panels && task.panels.length > 0 && (
              <>
                <div className="flex gap-2 mb-4">
                  <button
                    onClick={() => setActiveTab('panels')}
                    className={`flex-1 py-2 px-3 rounded-lg text-xs flex items-center justify-center gap-2 transition-colors ${
                      activeTab === 'panels'
                        ? 'bg-orange-500 text-white'
                        : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                    }`}
                  >
                    <ImageIcon className="w-3 h-3" />
                    条漫分镜 ({task.panels.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('blog')}
                    className={`flex-1 py-2 px-3 rounded-lg text-xs flex items-center justify-center gap-2 transition-colors ${
                      activeTab === 'blog'
                        ? 'bg-orange-500 text-white'
                        : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                    }`}
                  >
                    <FileText className="w-3 h-3" />
                    图文博客
                  </button>
                </div>

                {activeTab === 'panels' && (
                  <div className="space-y-3">
                    {task.panels.map((panel) => (
                      <div key={panel.panel_number} className="p-3 bg-zinc-900/50 rounded-xl border border-zinc-800">
                        <div className="flex gap-3">
                          <div className="w-24 h-32 bg-zinc-800 rounded-lg overflow-hidden shrink-0">
                            <img
                              src={panel.manga_image_url}
                              alt={panel.caption}
                              className="w-full h-full object-cover"
                            />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-zinc-500 mb-1">
                              {panel.time_formatted} - {panel.panel_number}/{task.total_panels}
                            </p>
                            <p className="text-sm text-zinc-300 mb-2">{panel.caption}</p>
                            {panel.characters && (
                              <p className="text-xs text-zinc-500">角色: {panel.characters}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'blog' && task.blog_title && (
                  <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
                    <h3 className="text-base font-bold text-white mb-3">{task.blog_title}</h3>
                    <div className="space-y-2">
                      {task.blog_sections?.map((section, idx) => (
                        <div key={idx}>
                          {section.type === 'text' && section.content && (
                            <p className="text-sm text-zinc-300 leading-relaxed">{section.content}</p>
                          )}
                          {section.type === 'panel' && task.panels[section.panel_index!] && (
                            <div className="my-3">
                              <img
                                src={task.panels[section.panel_index!].manga_image_url}
                                alt={task.panels[section.panel_index!].caption}
                                className="w-full rounded-lg"
                              />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
