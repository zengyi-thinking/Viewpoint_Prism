import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle, XCircle, AlertCircle, Info, Loader2 } from 'lucide-react'
import { create } from 'zustand'
import { ReactNode, useEffect } from 'react'
import { cn } from '@/lib/utils'

// === Toast Types ===
export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading'
export type ToastPosition = 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'

export interface Toast {
  id: string
  type: ToastType
  title?: string
  message: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

interface ToastStore {
  toasts: Toast[]
  position: ToastPosition
  addToast: (toast: Omit<Toast, 'id'>) => string
  removeToast: (id: string) => void
  clearAll: () => void
  setPosition: (position: ToastPosition) => void
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  position: 'top-right',

  addToast: (toast) => {
    const id = Math.random().toString(36).substring(2, 9)
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }))

    if (toast.duration !== 0) {
      setTimeout(() => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }))
      }, toast.duration || 4000)
    }

    return id
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }))
  },

  clearAll: () => set({ toasts: [] }),

  setPosition: (position) => set({ position }),
}))

// === Toast Icons ===
const toastIcons = {
  success: <CheckCircle className="w-5 h-5 text-emerald-400" />,
  error: <XCircle className="w-5 h-5 text-red-400" />,
  warning: <AlertCircle className="w-5 h-5 text-amber-400" />,
  info: <Info className="w-5 h-5 text-blue-400" />,
  loading: <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />,
}

// === Toast Component ===
interface ToastProps {
  toast: Toast
  onRemove: (id: string) => void
  position: ToastPosition
}

function ToastItem({ toast, onRemove, position }: ToastProps) {
  const isTop = position.includes('top')
  const isCenter = position.includes('center')

  return (
    <motion.div
      initial={{ opacity: 0, x: isCenter ? 0 : (isTop ? 100 : -100), y: isCenter ? (isTop ? -50 : 50) : 0 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
      layout
      className={cn(
        "glass-card p-4 min-w-[320px] max-w-md shadow-xl",
        "flex items-start gap-3",
        toast.type === 'loading' && "border-blue-500/30",
        toast.type === 'success' && "border-emerald-500/30",
        toast.type === 'error' && "border-red-500/30",
        toast.type === 'warning' && "border-amber-500/30",
        toast.type === 'info' && "border-blue-500/30"
      )}
    >
      {/* Icon */}
      <div className="shrink-0 mt-0.5">{toastIcons[toast.type]}</div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {toast.title && (
          <p className="text-sm font-semibold text-zinc-100">{toast.title}</p>
        )}
        <p className="text-sm text-zinc-300 break-words">{toast.message}</p>

        {/* Action */}
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            className="mt-2 text-xs font-medium text-violet-400 hover:text-violet-300 transition-colors"
          >
            {toast.action.label}
          </button>
        )}
      </div>

      {/* Close Button */}
      {toast.type !== 'loading' && (
        <button
          onClick={() => onRemove(toast.id)}
          className="shrink-0 p-0.5 rounded-lg hover:bg-zinc-700/50 transition-colors"
        >
          <X className="w-4 h-4 text-zinc-400" />
        </button>
      )}
    </motion.div>
  )
}

// === Toast Container ===
const positionClasses: Record<ToastPosition, string> = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-center': 'top-4 left-1/2 -translate-x-1/2',
  'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
}

export function ToastContainer() {
  const { toasts, removeToast, position } = useToastStore()

  return (
    <div
      className={cn(
        "fixed z-50 flex flex-col gap-2 pointer-events-none",
        positionClasses[position]
      )}
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} onRemove={removeToast} position={position} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  )
}

// === Toast Hook ===
export function useToast() {
  const { addToast, removeToast, clearAll, setPosition } = useToastStore()

  return {
    toast: (toast: Omit<Toast, 'id'>) => addToast(toast),
    success: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) =>
      addToast({ type: 'success', message, ...options }),
    error: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) =>
      addToast({ type: 'error', message, ...options }),
    warning: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) =>
      addToast({ type: 'warning', message, ...options }),
    info: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) =>
      addToast({ type: 'info', message, ...options }),
    loading: (message: string, options?: Partial<Omit<Toast, 'id' | 'type' | 'message'>>) =>
      addToast({ type: 'loading', message, duration: 0, ...options }),
    remove: removeToast,
    clearAll,
    setPosition,
  }
}

// === Skeleton Components ===
interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded'
  width?: string | number
  height?: string | number
  animation?: 'pulse' | 'wave' | 'none'
}

export function Skeleton({
  className,
  variant = 'rectangular',
  width,
  height,
  animation = 'pulse',
}: SkeletonProps) {
  const variantClasses = {
    text: 'rounded h-4',
    circular: 'rounded-full',
    rectangular: 'rounded-md',
    rounded: 'rounded-xl',
  }

  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'shimmer',
    none: '',
  }

  return (
    <div
      className={cn(
        'skeleton bg-zinc-800',
        variantClasses[variant],
        animationClasses[animation],
        className
      )}
      style={{ width, height }}
    />
  )
}

// === Skeleton Variants ===
export function SkeletonCard() {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton variant="circular" width={40} height={40} />
        <div className="flex-1 space-y-2">
          <Skeleton variant="text" width="60%" height={16} />
          <Skeleton variant="text" width="40%" height={14} />
        </div>
      </div>
      <Skeleton variant="text" width="100%" height={14} />
      <Skeleton variant="text" width="80%" height={14} />
    </div>
  )
}

export function SkeletonList({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

export function SkeletonGraph() {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 h-[400px]">
      <div className="flex items-center justify-between mb-4">
        <Skeleton variant="text" width={120} height={20} />
        <Skeleton variant="rectangular" width={80} height={32} />
      </div>
      <div className="h-[320px] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-zinc-800 animate-pulse" />
          <Skeleton variant="text" width={150} height={16} className="mx-auto" />
        </div>
      </div>
    </div>
  )
}

// === Ripple Button Component ===
interface RippleButtonProps {
  children: ReactNode
  onClick?: (e: React.MouseEvent) => void
  className?: string
  disabled?: boolean
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

export function RippleButton({
  children,
  onClick,
  className,
  disabled = false,
  variant = 'primary',
  size = 'md',
}: RippleButtonProps) {
  const variantClasses = {
    primary: 'bg-violet-600 hover:bg-violet-500 text-white',
    secondary: 'bg-zinc-700 hover:bg-zinc-600 text-white',
    ghost: 'bg-transparent hover:bg-zinc-800 text-zinc-200',
    danger: 'bg-red-600 hover:bg-red-500 text-white',
  }

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  }

  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'relative overflow-hidden rounded-xl font-medium transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 focus:ring-offset-zinc-900',
        variantClasses[variant],
        sizeClasses[size],
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      <span className="relative z-10">{children}</span>
      <span className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 translate-x-[-100%] hover:animate-[shimmer_1s_infinite]" />
    </motion.button>
  )
}

// === Loading Overlay ===
interface LoadingOverlayProps {
  isLoading: boolean
  message?: string
  children: ReactNode
}

export function LoadingOverlay({ isLoading, message = 'Loading...', children }: LoadingOverlayProps) {
  return (
    <div className="relative">
      {children}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-zinc-900/80 backdrop-blur-sm flex items-center justify-center z-10 rounded-xl"
          >
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-violet-400 animate-spin mx-auto mb-3" />
              <p className="text-sm text-zinc-300">{message}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// === Progress Bar Component ===
interface ProgressBarProps {
  progress: number
  className?: string
  showLabel?: boolean
  label?: string
  color?: 'blue' | 'purple' | 'green' | 'amber' | 'red'
}

export function ProgressBar({
  progress,
  className,
  showLabel = false,
  label,
  color = 'purple',
}: ProgressBarProps) {
  const colorClasses = {
    blue: 'bg-blue-500',
    purple: 'bg-violet-500',
    green: 'bg-emerald-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500',
  }

  return (
    <div className={cn("w-full", className)}>
      {showLabel && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-zinc-400">{label}</span>
          <span className="text-xs text-zinc-400">{Math.round(progress)}%</span>
        </div>
      )}
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          transition={{ type: 'spring', stiffness: 100, damping: 15 }}
          className={cn("h-full progress-bar", colorClasses[color])}
        />
      </div>
    </div>
  )
}

// === Status Badge Component ===
interface StatusBadgeProps {
  status: 'online' | 'offline' | 'busy' | 'away'
  showLabel?: boolean
  className?: string
}

export function StatusBadge({ status, showLabel = false, className }: StatusBadgeProps) {
  const statusConfig = {
    online: { color: 'bg-emerald-500', label: 'Online' },
    offline: { color: 'bg-zinc-500', label: 'Offline' },
    busy: { color: 'bg-red-500', label: 'Busy' },
    away: { color: 'bg-amber-500', label: 'Away' },
  }

  const config = statusConfig[status]

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="relative flex h-2.5 w-2.5">
        <span className={cn("absolute inline-flex h-full w-full rounded-full opacity-75", config.color)} />
        <span
          className={cn(
            "relative inline-flex rounded-full h-2.5 w-2.5",
            config.color,
            status === 'online' && 'animate-ping'
          )}
        />
      </span>
      {showLabel && (
        <span className="text-xs text-zinc-400">{config.label}</span>
      )}
    </div>
  )
}
