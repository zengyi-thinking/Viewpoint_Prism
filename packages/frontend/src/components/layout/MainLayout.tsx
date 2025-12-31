import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from 'react-resizable-panels'
import { Header } from './Header'
import { SourcesPanel } from '@/components/panels/SourcesPanel'
import { StagePanel } from '@/components/panels/StagePanel'
import { AnalysisPanel } from '@/components/panels/AnalysisPanel'
import { useAppStore } from '@/stores/app-store'

export function MainLayout() {
  const { panelVisibility } = useAppStore()

  return (
    <div className="h-screen w-screen bg-[#09090b] overflow-hidden flex flex-col">
      <Header />

      <PanelGroup direction="horizontal" className="flex-1">
        {/* Left Panel - Sources */}
        {panelVisibility.left && (
          <>
            <Panel defaultSize={20} minSize={15} maxSize={30} className="min-w-[200px]">
              <SourcesPanel />
            </Panel>
            <PanelResizeHandle className="w-px bg-zinc-800/50 hover:bg-zinc-700 transition-colors" />
          </>
        )}

        {/* Center Panel - Stage */}
        <Panel defaultSize={50} minSize={30}>
          <PanelGroup direction="vertical">
            <Panel defaultSize={65} minSize={40} className="overflow-hidden">
              <StagePanel />
            </Panel>
            {panelVisibility.bottom && (
              <>
                <PanelResizeHandle className="h-px bg-zinc-800/50 hover:bg-zinc-700 transition-colors" />
                <Panel defaultSize={35} minSize={20} className="overflow-hidden">
                  {/* Chat panel is inside StagePanel */}
                </Panel>
              </>
            )}
          </PanelGroup>
        </Panel>

        {/* Right Panel - Analysis */}
        {panelVisibility.right && (
          <>
            <PanelResizeHandle className="w-px bg-zinc-800/50 hover:bg-zinc-700 transition-colors" />
            <Panel defaultSize={30} minSize={25} maxSize={40} className="min-w-[300px]">
              <AnalysisPanel />
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  )
}
