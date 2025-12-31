import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface FeatureCardProps {
  title: string
  icon: LucideIcon
  description: string
  color: string
  glowColor: string
  onClick: () => void
  disabled?: boolean
}

export function FeatureCard({
  title,
  icon: Icon,
  description,
  color,
  glowColor,
  onClick,
  disabled = false
}: FeatureCardProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "group relative overflow-hidden rounded-2xl bg-zinc-900/50 border border-zinc-800/50 p-4 text-left transition-all",
        !disabled && "hover:border-zinc-700 hover:shadow-xl hover:shadow-zinc-900/20",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      {/* Glow effect on hover */}
      <div className={cn(
        "absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500",
        glowColor,
        disabled && "hidden"
      )} />

      {/* Content */}
      <div className="relative">
        {/* Icon */}
        <div className={cn(
          "w-12 h-12 rounded-xl flex items-center justify-center mb-3 transition-all group-hover:scale-110",
          color
        )}>
          <Icon className="w-6 h-6 text-white" />
        </div>

        {/* Title */}
        <h3 className="text-sm font-bold text-white mb-1">
          {title}
        </h3>

        {/* Description */}
        <p className="text-xs text-zinc-400 leading-relaxed">
          {description}
        </p>
      </div>
    </button>
  )
}
