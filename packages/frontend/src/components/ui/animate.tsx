import { motion, HTMLMotionProps, Variants } from 'framer-motion'
import { cn } from '@/lib/utils'
import { ReactNode } from 'react'

// === variants ===
export const fadeInVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
}

export const slideUpVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

export const slideDownVariants: Variants = {
  hidden: { opacity: 0, y: -20 },
  visible: { opacity: 1, y: 0 },
}

export const slideLeftVariants: Variants = {
  hidden: { opacity: 0, x: 20 },
  visible: { opacity: 1, x: 0 },
}

export const slideRightVariants: Variants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 },
}

export const scaleVariants: Variants = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: { opacity: 1, scale: 1 },
}

export const springScaleVariants: Variants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 20,
    },
  },
}

export const staggerContainerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
}

export const staggerItemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 24,
    },
  },
}

// === Components ===

interface AnimateInProps extends HTMLMotionProps<'div'> {
  children: ReactNode
  variants?: Variants
  className?: string
  delay?: number
  duration?: number
}

export function AnimateIn({
  children,
  variants = fadeInVariants,
  className,
  delay = 0,
  duration = 0.3,
  ...props
}: AnimateInProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={variants}
      transition={{ duration, delay }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}

interface StaggerListProps {
  children: ReactNode[]
  className?: string
  staggerDelay?: number
  delayChildren?: number
}

export function StaggerList({
  children,
  className,
  staggerDelay = 0.1,
  delayChildren = 0.2,
}: StaggerListProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        visible: {
          transition: {
            staggerChildren: staggerDelay,
            delayChildren,
          },
        },
      }}
      className={className}
    >
      {children.map((child, index) => (
        <motion.div
          key={index}
          variants={staggerItemVariants}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  )
}

interface PageTransitionProps {
  children: ReactNode
  className?: string
}

export function PageTransition({ children, className }: PageTransitionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 30,
        mass: 0.8,
      }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

interface ScaleInProps {
  children: ReactNode
  className?: string
  delay?: number
}

export function ScaleIn({ children, className, delay = 0 }: ScaleInProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 20,
        delay,
      }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

interface SlideInProps {
  children: ReactNode
  direction?: 'up' | 'down' | 'left' | 'right'
  className?: string
  delay?: number
  distance?: number
}

export function SlideIn({
  children,
  direction = 'up',
  className,
  delay = 0,
  distance = 20,
}: SlideInProps) {
  const variants = {
    up: { y: distance },
    down: { y: -distance },
    left: { x: distance },
    right: { x: -distance },
  }

  return (
    <motion.div
      initial={{ opacity: 0, ...variants[direction] }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      exit={{ opacity: 0, ...variants[direction] }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 30,
        delay,
      }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

interface PulseProps {
  children: ReactNode
  className?: string
  intensity?: number
}

export function Pulse({ children, className, intensity = 1.05 }: PulseProps) {
  return (
    <motion.div
      whileHover={{ scale: intensity }}
      whileTap={{ scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

interface ShimmerProps {
  children: ReactNode
  className?: string
  shimmerWidth?: number
}

export function Shimmer({ children, className, shimmerWidth = 100 }: ShimmerProps) {
  return (
    <motion.div
      className={cn('relative overflow-hidden', className)}
      whileHover="hover"
    >
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
        variants={{
          hover: {
            x: ['0%', '200%'],
            transition: {
              x: {
                repeat: Infinity,
                repeatType: 'loop',
                duration: 1.5,
                ease: 'linear',
              },
            },
          },
        }}
        style={{ width: shimmerWidth + '%' }}
      />
      {children}
    </motion.div>
  )
}

interface BounceProps {
  children: ReactNode
  className?: string
  trigger?: 'hover' | 'always'
}

export function Bounce({ children, className, trigger = 'hover' }: BounceProps) {
  const bounceAnimation = {
    scale: [1, 1.1, 1],
    transition: {
      duration: 0.3,
      times: [0, 0.5, 1],
    },
  }

  return (
    <motion.div
      className={className}
      animate={trigger === 'always' ? bounceAnimation : undefined}
      whileHover={trigger === 'hover' ? bounceAnimation : undefined}
    >
      {children}
    </motion.div>
  )
}
