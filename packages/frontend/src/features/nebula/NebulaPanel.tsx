import { useState, useEffect } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Sparkles, Play, RefreshCw, Search } from 'lucide-react'
import { NebulaAPI } from '@/api'
import type { NebulaNode, NebulaLink, ConceptItem } from '@/types/modules/nebula'

/**
 * Nebula Panel - 知识星云面板
 *
 * 功能：
 * - 显示视频中提取的概念/实体网络
 * - 可视化节点关系图
 * - 选择实体生成高光蒙太奇
 * - 查看实体统计信息
 */
export function NebulaPanel() {
  const { sources, selectedSourceIds, openEntityCard, setActivePlayer } = useAppStore()
  const [nodes, setNodes] = useState<NebulaNode[]>([])
  const [links, setLinks] = useState<NebulaLink[]>([])
  const [concepts, setConcepts] = useState<ConceptItem[]>([])
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskProgress, setTaskProgress] = useState(0)
  const [isGenerating, setIsGenerating] = useState(false)

  const effectiveSourceIds = selectedSourceIds.length > 0 ? selectedSourceIds : sources.map(s => s.id)

  // 加载概念列表
  useEffect(() => {
    const loadConcepts = async () => {
      try {
        const response = await NebulaAPI.getConcepts(50)
        setConcepts(response.concepts)
      } catch (error) {
        console.error('Failed to load concepts:', error)
      }
    }

    if (effectiveSourceIds.length > 0) {
      loadConcepts()
    }
  }, [effectiveSourceIds])

  // 加载星云结构
  useEffect(() => {
    const loadStructure = async () => {
      setIsLoading(true)
      try {
        const response = await NebulaAPI.getStructure(effectiveSourceIds)
        setNodes(response.nodes)
        setLinks(response.links)
      } catch (error) {
        console.error('Failed to load nebula structure:', error)
      } finally {
        setIsLoading(false)
      }
    }

    if (effectiveSourceIds.length > 0) {
      loadStructure()
    }
  }, [effectiveSourceIds])

  // 处理节点点击
  const handleNodeClick = (node: NebulaNode) => {
    openEntityCard({
      id: node.id,
      name: node.name,
      category: node.category as any,
      timestamp: undefined,
      source_id: node.source_ids[0],
    }, { x: 0, y: 0 })
  }

  // 生成高光视频
  const handleCreateHighlight = async (concept: string) => {
    if (isGenerating) return

    setIsGenerating(true)
    setTaskProgress(0)
    setSelectedConcept(concept)

    try {
      const response = await NebulaAPI.createHighlight({ concept, top_k: 10 })
      setTaskId(response.task_id)

      // 轮询任务状态
      const pollInterval = setInterval(async () => {
        const status = await NebulaAPI.getHighlightStatus(response.task_id)
        setTaskProgress(status.progress || 0)

        if (status.status === 'completed') {
          clearInterval(pollInterval)
          setIsGenerating(false)
          if (status.video_url) {
            setActivePlayer('nebula')
          }
        } else if (status.status === 'error') {
          clearInterval(pollInterval)
          setIsGenerating(false)
        }
      }, 2000)
    } catch (error) {
      console.error('Failed to create highlight:', error)
      setIsGenerating(false)
    }
  }

  return (
    <div className="floating-panel flex flex-col h-full bg-[#121214]">
      <div className="h-10 flex items-center justify-between px-5 border-b border-zinc-800/50 bg-[#18181b]/50">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
          <Sparkles className="w-3 h-3" />
          Knowledge Nebula
        </span>
        {isGenerating && (
          <span className="text-[10px] text-amber-400">生成中... {taskProgress}%</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto scroller p-5">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <RefreshCw className="w-6 h-6 text-zinc-600 animate-spin" />
          </div>
        )}

        {!isLoading && nodes.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Sparkles className="w-12 h-12 text-zinc-700 mb-4" />
            <p className="text-sm text-zinc-500 mb-2">暂无知识星云数据</p>
            <p className="text-xs text-zinc-600">请先分析视频以提取实体和概念</p>
          </div>
        )}

        {!isLoading && nodes.length > 0 && (
          <div className="space-y-4">
            {/* 概念搜索/选择 */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                placeholder="搜索概念..."
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2 pl-10 pr-4 text-xs text-white focus:border-zinc-500 outline-none"
              />
            </div>

            {/* 高频概念列表 */}
            <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
              <h3 className="text-xs font-bold text-white mb-3">高频概念</h3>
              <div className="flex flex-wrap gap-2">
                {concepts.slice(0, 15).map((concept) => (
                  <button
                    key={concept.name}
                    onClick={() => handleCreateHighlight(concept.name)}
                    disabled={isGenerating}
                    className={`px-3 py-1.5 rounded-full text-xs transition-colors ${
                      isGenerating && selectedConcept === concept.name
                        ? 'bg-purple-500/20 text-purple-400 cursor-wait'
                        : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white'
                    }`}
                  >
                    {concept.name}
                    <span className="ml-1 text-zinc-500">({concept.weight})</span>
                  </button>
                ))}
              </div>
            </div>

            {/* 知识图谱节点 */}
            <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
              <h3 className="text-xs font-bold text-white mb-3">
                知识节点 ({nodes.length})
              </h3>
              <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto">
                {nodes.map((node) => (
                  <button
                    key={node.id}
                    onClick={() => handleNodeClick(node)}
                    className="p-3 bg-zinc-800/50 rounded-lg text-left hover:bg-zinc-700 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-zinc-300 truncate">{node.name}</span>
                      <span className="text-[10px] text-zinc-500">{node.value}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        node.category === 'boss' ? 'bg-red-500/20 text-red-400' :
                        node.category === 'item' ? 'bg-blue-500/20 text-blue-400' :
                        node.category === 'location' ? 'bg-green-500/20 text-green-400' :
                        'bg-purple-500/20 text-purple-400'
                      }`}>
                        {node.category}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* 关系边 */}
            {links.length > 0 && (
              <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
                <h3 className="text-xs font-bold text-white mb-3">
                  实体关系 ({links.length})
                </h3>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {links.slice(0, 20).map((link, idx) => {
                    const sourceNode = nodes.find(n => n.id === link.source)
                    const targetNode = nodes.find(n => n.id === link.target)
                    return (
                      <div key={idx} className="flex items-center gap-2 text-xs text-zinc-400">
                        <span className="text-zinc-300">{sourceNode?.name || link.source}</span>
                        <span className="text-zinc-600">→</span>
                        <span className="text-zinc-300">{targetNode?.name || link.target}</span>
                        <span className="text-zinc-600">({link.value})</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {taskId && (
              <div className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-zinc-400">高光视频生成</span>
                  <span className="text-xs text-zinc-500">{taskProgress}%</span>
                </div>
                <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500 transition-all duration-300"
                    style={{ width: `${taskProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
