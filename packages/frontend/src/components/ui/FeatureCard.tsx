import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface FeatureCardProps {
  title: string
  icon: LucideIcon
  description: string
  color: string
  glowColor: string
  onClick: () => void
}

export function FeatureCard({
  title,
  icon: Icon,
  description,
  color,
  glowColor,
  onClick
}: FeatureCardProps) {
  return (
    <button
      onClick={onClick}
      className="group relative w-full p-5 rounded-xl bg-zinc-900/80 border border-zinc-800 hover:border-zinc-700 transition-all duration-300 hover:transform hover:-translate-y-1 hover:shadow-xl"
      style={{ boxShadow: `0 0 0 1px rgba(0,0,0,0)` }}
    >
      {/* Glow effect on hover */}
      <div
        className={cn(
          'absolute inset-0 rounded-xl opacity-0 group-hover:opacity-20 transition-opacity duration-300 blur-xl',
          glowColor
        )}
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center gap-3">
        {/* Icon */}
        <div
          className={cn(
            'w-14 h-14 rounded-xl flex items-center justify-center text-white transition-transform duration-300 group-hover:scale-110',
            color
          )}
        >
          <Icon size={28} />
        </div>

        {/* Title */}
        <h3 className="text-base font-semibold text-white">
          {title}
        </h3>

        {/* Description */}
        <p className="text-sm text-zinc-400 leading-relaxed">
          {description}
        </p>
      </div>

      {/* Hover border glow */}
      <div
        className={cn(
          'absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none',
          'shadow-[inset_0_0_20px_rgba(255,255,255,0.05)]'
        )}
      />
    </button>
  )
}
