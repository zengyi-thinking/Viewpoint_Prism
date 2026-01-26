import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from 'react-resizable-panels'
import { useAppStore } from '@/stores/app-store'
import { Header } from './Header'
import { VideoPlayer } from '@/components/panels/StagePanel'
import { ChatPanel } from '@/features/chat'
import { SourcesPanel } from '@/features/sources'
import { IngestPanel } from '@/features/ingest'
import { AnalysisPanel } from '@/features/analysis'
import { cn } from '@/lib/utils'
import { List, Search } from 'lucide-react'

// Resize Handle Component
function ResizeHandle({
  direction = 'vertical',
}: {
  direction?: 'vertical' | 'horizontal'
}) {
  return (
    <PanelResizeHandle
      className={cn(
        'group relative z-50 flex-shrink-0',
        direction === 'vertical'
          ? 'w-4 cursor-col-resize -mx-2'
          : 'h-4 cursor-row-resize -my-2'
      )}
    >
      <div
        className={cn(
          'absolute transition-colors duration-200 rounded-full',
          direction === 'vertical'
            ? 'left-[7px] top-[20%] bottom-[20%] w-[2px] bg-white/5 group-hover:bg-zinc-500'
            : 'top-[7px] left-[20%] right-[20%] h-[2px] bg-white/5 group-hover:bg-zinc-500'
        )}
      />
    </PanelResizeHandle>
  )
}

export default function MainLayout() {
  const { panelVisibility, leftPanelMode, setLeftPanelMode } = useAppStore()

  return (
    <div className="h-screen w-screen flex flex-col p-4 gap-4 text-sm select-none bg-[#050507]">
      {/* Header */}
      <Header />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden gap-4">
        <PanelGroup direction="horizontal" className="!h-full">
          {/* Left Panel - Sources or Ingest */}
          {panelVisibility.left && (
            <>
              <Panel
                defaultSize={20}
                minSize={15}
                maxSize={35}
                className="shrink-0"
              >
                <div className="flex flex-col h-full bg-zinc-900/40">
                  {/* Mode Toggle */}
                  <div className="p-2 border-b border-zinc-800/50 flex gap-1">
                    <button
                      onClick={() => setLeftPanelMode('sources')}
                      className={cn(
                        'flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors',
                        leftPanelMode === 'sources'
                          ? 'bg-zinc-700 text-white'
                          : 'text-zinc-400 hover:text-zinc-300 hover:bg-zinc-800/50'
                      )}
                    >
                      <List className="w-3 h-3" />
                      视频源
                    </button>
                    <button
                      onClick={() => setLeftPanelMode('ingest')}
                      className={cn(
                        'flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors',
                        leftPanelMode === 'ingest'
                          ? 'bg-zinc-700 text-white'
                          : 'text-zinc-400 hover:text-zinc-300 hover:bg-zinc-800/50'
                      )}
                    >
                      <Search className="w-3 h-3" />
                      搜索
                    </button>
                  </div>

                  {/* Panel Content */}
                  <div className="flex-1 overflow-hidden">
                    {leftPanelMode === 'sources' ? <SourcesPanel /> : <IngestPanel />}
                  </div>
                </div>
              </Panel>
              <ResizeHandle direction="vertical" />
            </>
          )}

          {/* Center Panel - Stage */}
          <Panel defaultSize={panelVisibility.right ? 60 : 80} minSize={30}>
            <PanelGroup direction="vertical" className="!h-full gap-4">
              {/* Video Player - 占据更多空间 */}
              <Panel defaultSize={panelVisibility.bottom ? 70 : 100} minSize={40} maxSize={90}>
                <div className="w-full h-full p-1">
                  <VideoPlayer />
                </div>
              </Panel>

              {/* Chat Panel */}
              {panelVisibility.bottom && (
                <>
                  <ResizeHandle direction="horizontal" />
                  <Panel defaultSize={30} minSize={20} maxSize={50}>
                    <ChatPanel />
                  </Panel>
                </>
              )}
            </PanelGroup>
          </Panel>

          {/* Right Panel - Analysis */}
          {panelVisibility.right && (
            <>
              <ResizeHandle direction="vertical" />
              <Panel
                defaultSize={30}
                minSize={20}
                maxSize={45}
                className="shrink-0"
              >
                <AnalysisPanel />
              </Panel>
            </>
          )}
        </PanelGroup>
      </div>
    </div>
  )
}
