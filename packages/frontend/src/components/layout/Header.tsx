import { useAppStore } from '@/stores/app-store'
import {
  Layers,
  Search,
  Sparkles,
  Sliders,
  HelpCircle,
  List,
  MessageSquare,
  BarChart3,
  Zap,
  Save,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export function Header() {
  const {
    language,
    setLanguage,
    panelVisibility,
    togglePanel,
  } = useAppStore()

  return (
    <header className="floating-panel shrink-0 z-30 overflow-visible">
      {/* Row 1 */}
      <div className="px-4 py-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center text-black text-sm shadow-md shrink-0">
            <Layers className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-sm font-extrabold text-gray-100 truncate">
                Viewpoint Prism
              </span>
              <span className="text-[10px] text-zinc-400 font-mono bg-zinc-800/60 px-2 py-0.5 rounded-lg shrink-0">
                v10.0
              </span>
            </div>
            <div className="text-[11px] text-zinc-500 truncate">
              <span>Floating Islands UI</span>
              <span className="mx-2 text-zinc-700">•</span>
              <span className="text-zinc-400/80">Viewport-ready</span>
            </div>
          </div>
        </div>

        {/* Quick Search / Command */}
        <div className="flex items-center gap-2 w-full sm:w-[420px]">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-3 h-3" />
            <input
              type="text"
              className="input-industrial w-full rounded-xl py-2.5 pl-9 pr-16 bg-zinc-900/40 border-zinc-800/60 focus:border-zinc-500 select-text"
              placeholder={language === 'zh' ? '快速搜索 / Command…' : 'Quick Search / Command…'}
              aria-label="Topbar Search"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <kbd className="font-mono text-[10px] text-zinc-400 border border-white/10 bg-zinc-800/55 rounded-md px-1.5 py-0.5">
                Ctrl
              </kbd>
              <kbd className="font-mono text-[10px] text-zinc-400 border border-white/10 bg-zinc-800/55 rounded-md px-1.5 py-0.5">
                K
              </kbd>
            </div>
          </div>

          <button className="topbar-btn px-3 py-2.5 text-xs font-bold text-zinc-100 flex items-center gap-2 shadow-sm">
            <Sparkles className="w-3 h-3" />
            <span className="hidden sm:inline">Assist</span>
          </button>
        </div>

        {/* Status */}
        <div className="flex items-center justify-between sm:justify-end gap-2 w-full sm:w-auto">
          <div className="topbar-pill px-3 py-2 flex items-center gap-2 text-[11px] text-zinc-300">
            <span className="relative inline-flex h-2 w-2">
              <span className="absolute inline-flex h-2 w-2 rounded-full bg-emerald-400 opacity-75 animate-ping"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-mono">
              {language === 'zh' ? 'R1 引擎在线' : 'R1 Engine Online'}
            </span>
          </div>

          <button
            className="topbar-btn w-[34px] h-[34px] flex items-center justify-center rounded-xl text-zinc-300 hover:text-white"
            title="Settings"
          >
            <Sliders className="w-4 h-4" />
          </button>

          <button
            className="topbar-btn w-[34px] h-[34px] flex items-center justify-center rounded-xl text-zinc-300 hover:text-white"
            title="Help"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Row 2 */}
      <div className="px-4 pb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        {/* Layout toggles */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="topbar-pill flex items-center p-1 gap-1">
            <button
              onClick={() => togglePanel('left')}
              className={cn(
                'topbar-btn w-[34px] h-[34px] flex items-center justify-center rounded-xl text-[12px]',
                panelVisibility.left
                  ? 'bg-zinc-700 text-white'
                  : 'text-gray-300 hover:text-white'
              )}
              title="Toggle Left"
            >
              <List className="w-4 h-4" />
            </button>
            <div className="w-px h-[18px] bg-white/10 mx-1" />
            <button
              onClick={() => togglePanel('bottom')}
              className={cn(
                'topbar-btn w-[34px] h-[34px] flex items-center justify-center rounded-xl text-[12px]',
                panelVisibility.bottom
                  ? 'bg-zinc-700 text-white'
                  : 'text-gray-300 hover:text-white'
              )}
              title="Toggle Bottom"
            >
              <MessageSquare className="w-4 h-4" />
            </button>
            <div className="w-px h-[18px] bg-white/10 mx-1" />
            <button
              onClick={() => togglePanel('right')}
              className={cn(
                'topbar-btn w-[34px] h-[34px] flex items-center justify-center rounded-xl text-[12px]',
                panelVisibility.right
                  ? 'bg-zinc-700 text-white'
                  : 'text-gray-300 hover:text-white'
              )}
              title="Toggle Right"
            >
              <BarChart3 className="w-4 h-4" />
            </button>
          </div>

          <div className="topbar-pill px-3 py-2 text-[11px] text-zinc-400 flex items-center gap-2">
            <span>Panels</span>
            <span className="text-zinc-700">/</span>
            <span className="text-zinc-300">Resizable</span>
          </div>
        </div>

        {/* Language + actions */}
        <div className="flex items-center gap-2 flex-wrap justify-between sm:justify-end">
          <div className="topbar-pill flex overflow-hidden">
            <button
              onClick={() => setLanguage('en')}
              className={cn(
                'px-3 py-2 text-[11px] transition-colors',
                language === 'en'
                  ? 'bg-zinc-700 text-white font-bold'
                  : 'text-gray-300 hover:text-white'
              )}
            >
              EN
            </button>
            <span className="w-px bg-white/10" />
            <button
              onClick={() => setLanguage('zh')}
              className={cn(
                'px-3 py-2 text-[11px] transition-colors',
                language === 'zh'
                  ? 'bg-zinc-700 text-white font-bold'
                  : 'text-gray-300 hover:text-white'
              )}
            >
              中
            </button>
          </div>

          <button className="topbar-btn px-3 py-2 text-[11px] text-zinc-200 flex items-center gap-2">
            <Zap className="w-3 h-3 text-amber-400" />
            <span>Quick Run</span>
          </button>

          <button className="topbar-btn px-3 py-2 text-[11px] text-zinc-200 flex items-center gap-2">
            <Save className="w-3 h-3 text-zinc-400" />
            <span>Snapshot</span>
          </button>
        </div>
      </div>

      {/* Separator */}
      <div className="w-full h-px bg-white/5" />
    </header>
  )
}
