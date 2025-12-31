import { useState } from 'react'
import { useAppStore } from '@/stores/app-store'
import { Zap, Network, Timeline, FileText, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactECharts from 'echarts-for-react'

export function AnalysisPanel() {
  const { activeTab, setActiveTab, conflicts, graph, timeline, isAnalyzing, fetchAnalysis, selectedSourceIds, language } = useAppStore()

  const handleGenerate = () => {
    if (selectedSourceIds.length > 0) {
      fetchAnalysis(selectedSourceIds)
    }
  }

  const tabs = [
    { id: 'studio' as const, icon: Zap, label: 'Studio' },
    { id: 'conflicts' as const, icon: Network, label: 'Conflicts' },
    { id: 'graph' as const, icon: Network, label: 'Graph' },
    { id: 'timeline' as const, icon: Timeline, label: 'Timeline' },
    { id: 'report' as const, icon: FileText, label: 'Report' },
  ]

  return (
    <div className="h-full flex flex-col bg-[#09090b]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800/50">
        <h2 className="text-sm font-semibold text-zinc-100 mb-3">Analysis</h2>

        {/* Tabs */}
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                activeTab === tab.id
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              )}
            >
              <tab.icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {selectedSourceIds.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">
            <p className="text-sm">Select sources to analyze</p>
            <p className="text-xs mt-1">Choose at least one video from the Sources panel</p>
          </div>
        ) : isAnalyzing ? (
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-violet-500 mb-3" />
            <p className="text-sm text-zinc-400">Analyzing videos...</p>
          </div>
        ) : (
          <>
            {activeTab === 'studio' && (
              <div className="space-y-4">
                <button
                  onClick={handleGenerate}
                  className="w-full py-3 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-medium transition-colors"
                >
                  Generate Analysis
                </button>
                <p className="text-xs text-zinc-500 text-center">
                  AI will detect conflicts, build knowledge graph, and extract timeline
                </p>
              </div>
            )}

            {activeTab === 'conflicts' && (
              <div className="space-y-3">
                {conflicts.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-8">No conflicts detected</p>
                ) : (
                  conflicts.map((conflict) => (
                    <div key={conflict.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                      <h3 className="text-sm font-medium text-zinc-200 mb-3">{conflict.topic}</h3>
                      <div className="space-y-2">
                        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                          <p className="text-xs text-red-400 mb-1">Viewpoint A</p>
                          <p className="text-sm text-zinc-300">{conflict.viewpoint_a.description}</p>
                        </div>
                        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                          <p className="text-xs text-blue-400 mb-1">Viewpoint B</p>
                          <p className="text-sm text-zinc-300">{conflict.viewpoint_b.description}</p>
                        </div>
                        <div className="bg-zinc-800 rounded-lg p-3">
                          <p className="text-xs text-zinc-400 mb-1">AI Verdict</p>
                          <p className="text-sm text-zinc-300">{conflict.verdict}</p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'graph' && (
              <div className="h-full min-h-[400px]">
                {graph.nodes.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-8">No graph data</p>
                ) : (
                  <ReactECharts
                    option={{
                      series: [{
                        type: 'graph',
                        layout: 'force',
                        data: graph.nodes.map(n => ({ name: n.name, category: n.category })),
                        links: graph.links,
                        categories: [
                          { name: 'boss' },
                          { name: 'item' },
                          { name: 'location' },
                          { name: 'character' }
                        ],
                        roam: true,
                        label: { show: true, position: 'right', color: '#fff' },
                        force: { repulsion: 1500, edgeLength: [100, 300], gravity: 0.1 },
                        lineStyle: { color: '#3f3f46', width: 1 }
                      }],
                      backgroundColor: 'transparent'
                    }}
                    style={{ height: '100%', width: '100%' }}
                  />
                )}
              </div>
            )}

            {activeTab === 'timeline' && (
              <div className="space-y-3">
                {timeline.length === 0 ? (
                  <p className="text-sm text-zinc-500 text-center py-8">No timeline data</p>
                ) : (
                  timeline.map((event) => (
                    <div key={event.id} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className={cn(
                          "w-3 h-3 rounded-full",
                          event.event_type === 'STORY' && "bg-amber-500",
                          event.event_type === 'COMBAT' && "bg-red-500",
                          event.event_type === 'EXPLORE' && "bg-zinc-500"
                        )} />
                        <div className="w-px h-full bg-zinc-800" />
                      </div>
                      <div className="flex-1 pb-4">
                        <span className="text-xs text-zinc-500">{event.time}</span>
                        <h4 className="text-sm font-medium text-zinc-200 mt-1">{event.title}</h4>
                        <p className="text-xs text-zinc-400 mt-1">{event.description}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'report' && (
              <div className="text-center text-zinc-500 py-8">
                <p className="text-sm">Report feature coming soon</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
