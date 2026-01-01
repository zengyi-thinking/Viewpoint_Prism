import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { useEffect } from 'react'

export interface ContextBridgeData {
  summary: string
  previous_context: string
  current_context: string
  timestamp_str: string
}

interface ContextOverlayProps {
  data: ContextBridgeData | null
  visible: boolean
  onClose: () => void
}

/**
 * ContextOverlay Component
 *
 * A non-intrusive overlay that displays context bridge summaries
 * when users seek to a new timestamp in a video.
 *
 * Features:
 * - Framer Motion fade-in/fade-out animations
 * - Dark glassmorphism background with backdrop blur
 * - Positioned above the video player controls
 * - Auto-dismisses after 10 seconds
 * - Manual close button (X)
 */
export function ContextOverlay({ data, visible, onClose }: ContextOverlayProps) {
  // Auto-dismiss after 10 seconds
  useEffect(() => {
    if (visible) {
      const timer = setTimeout(() => {
        onClose()
      }, 10000)
      return () => clearTimeout(timer)
    }
  }, [visible, onClose])

  if (!data || !visible) return null

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className="absolute bottom-28 left-6 right-6 z-20 max-w-2xl"
        >
          <div className="relative bg-black/80 backdrop-blur-xl rounded-2xl border border-zinc-700/50 shadow-2xl overflow-hidden">
            {/* Animated top border with gradient */}
            <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-70" />

            {/* Header with close button */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-700/30">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest">
                  Context Bridge
                </span>
                <span className="text-[10px] text-zinc-500 ml-2">
                  {data.timestamp_str}
                </span>
              </div>
              <button
                onClick={onClose}
                className="w-6 h-6 rounded-full bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center transition-colors"
              >
                <X size={12} className="text-zinc-400" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4">
              {/* Main summary - highlighted */}
              <div className="mb-3">
                <p className="text-sm text-white font-medium leading-relaxed">
                  {data.summary}
                </p>
              </div>

              {/* Context indicators */}
              <div className="flex items-center gap-3 text-[11px] text-zinc-400">
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-zinc-600" />
                  <span>{data.previous_context}</span>
                </div>
                <span className="text-zinc-600">→</span>
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                  <span className="text-cyan-400">{data.current_context}</span>
                </div>
              </div>
            </div>

            {/* Progress bar for auto-dismiss */}
            <motion.div
              initial={{ width: '100%' }}
              animate={{ width: '0%' }}
              transition={{ duration: 10, ease: 'linear' }}
              className="absolute bottom-0 left-0 h-0.5 bg-gradient-to-r from-cyan-500/50 to-transparent"
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
