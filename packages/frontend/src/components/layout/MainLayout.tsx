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
import { AnalysisPanel } from '@/features/analysis'
import { cn } from '@/lib/utils'

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
  const { panelVisibility } = useAppStore()

  return (
    <div className="h-screen w-screen flex flex-col p-4 gap-4 text-sm select-none bg-[#050507]">
      {/* Header */}
      <Header />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden gap-4">
        <PanelGroup direction="horizontal" className="flex-1">
          {/* Left Panel - Sources */}
          {panelVisibility.left && (
            <>
              <Panel
                defaultSize={20}
                minSize={15}
                maxSize={35}
                className="shrink-0"
              >
                <SourcesPanel />
              </Panel>
              <ResizeHandle direction="vertical" />
            </>
          )}

          {/* Center Panel - Stage */}
          <Panel defaultSize={panelVisibility.right ? 60 : 80} minSize={30}>
            <PanelGroup direction="vertical" className="h-full">
              {/* Video Player - 优先给视频播放器更多空间 */}
              <Panel defaultSize={panelVisibility.bottom ? 65 : 100} minSize={50}>
                <VideoPlayer />
              </Panel>

              {/* Chat Panel */}
              {panelVisibility.bottom && (
                <>
                  <ResizeHandle direction="horizontal" />
                  <Panel defaultSize={45} minSize={25} maxSize={60}>
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
