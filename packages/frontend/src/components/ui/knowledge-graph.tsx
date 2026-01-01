import { useRef, useState, useEffect, useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Loader2, Maximize2, Minimize2, ZoomIn, ZoomOut, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { KnowledgeGraph, GraphNode } from '@/types'

interface KnowledgeGraphProps {
  graph: KnowledgeGraph
  onNodeClick?: (node: GraphNode, position: { x: number; y: number }) => void
  className?: string
}

// Category colors and icons
const categoryConfig = {
  boss: {
    color: '#ef4444',
    bgColor: 'rgba(239, 68, 68, 0.2)',
    borderColor: 'rgba(239, 68, 68, 0.5)',
    icon: '👑',
    label: 'Boss',
  },
  item: {
    color: '#f59e0b',
    bgColor: 'rgba(245, 158, 11, 0.2)',
    borderColor: 'rgba(245, 158, 11, 0.5)',
    icon: '⚔️',
    label: 'Item',
  },
  location: {
    color: '#10b981',
    bgColor: 'rgba(16, 185, 129, 0.2)',
    borderColor: 'rgba(16, 185, 129, 0.5)',
    icon: '📍',
    label: 'Location',
  },
  character: {
    color: '#8b5cf6',
    bgColor: 'rgba(139, 92, 246, 0.2)',
    borderColor: 'rgba(139, 92, 246, 0.5)',
    icon: '👤',
    label: 'Character',
  },
}

export function KnowledgeGraphComponent({ graph, onNodeClick, className }: KnowledgeGraphProps) {
  const chartRef = useRef<ReactECharts>(null)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [connectedNodes, setConnectedNodes] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(false)

  // Get connected nodes when hovering
  useEffect(() => {
    if (hoveredNode) {
      const connected = new Set<string>()
      graph.links.forEach((link) => {
        if (link.source === hoveredNode) connected.add(link.target)
        if (link.target === hoveredNode) connected.add(link.source)
      })
      connected.add(hoveredNode)
      setConnectedNodes(connected)
    } else {
      setConnectedNodes(new Set())
    }
  }, [hoveredNode, graph.links])

  // ECharts option with animations
  const option = useMemo(() => {
    const categories = Object.keys(categoryConfig).map((key) => ({
      name: categoryConfig[key as keyof typeof categoryConfig].label,
    }))

    return {
      animation: true,
      animationDuration: 1500,
      animationEasing: 'cubicOut',
      animationDelay: (idx: number) => idx * 50,

      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            const node = graph.nodes.find((n) => n.name === params.name)
            const category = node?.category || 'character'
            const config = categoryConfig[category as keyof typeof categoryConfig]
            return `
              <div class="p-2">
                <div class="flex items-center gap-2 mb-1">
                  <span>${config.icon}</span>
                  <span class="font-semibold">${params.name}</span>
                </div>
                <div class="text-xs text-zinc-400">${config.label}</div>
                ${node?.source_id ? `<div class="text-xs text-zinc-500 mt-1">Source: ${node.source_id}</div>` : ''}
              </div>
            `
          }
          if (params.dataType === 'edge') {
            return `${params.data.source} → ${params.data.target}`
          }
          return ''
        },
        backgroundColor: 'rgba(18, 18, 20, 0.95)',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        textStyle: {
          color: '#f4f4f5',
        },
        extraCssText: 'border-radius: 8px; backdrop-filter: blur(12px);',
      },

      legend: {
        show: true,
        data: categories.map((c) => c.name),
        textStyle: {
          color: '#a1a1aa',
        },
        top: 10,
        right: 10,
      },

      series: [
        {
          type: 'graph',
          layout: 'force',
          data: graph.nodes.map((node) => {
            const config = categoryConfig[node.category as keyof typeof categoryConfig]
            const isHovered = hoveredNode === node.name
            const isConnected = connectedNodes.has(node.name)
            const isDimmed = hoveredNode && !isConnected

            return {
              id: node.id,
              name: node.name,
              category: node.category,
              symbolSize: isHovered ? 60 : isConnected ? 45 : 35,
              itemStyle: {
                color: config.color,
                borderColor: config.borderColor,
                borderWidth: isHovered ? 3 : 1,
                opacity: isDimmed ? 0.3 : 1,
                shadowColor: config.color,
                shadowBlur: isHovered ? 20 : 0,
              },
              label: {
                show: true,
                position: 'right',
                color: isDimmed ? '#52525b' : '#f4f4f5',
                fontSize: isHovered ? 14 : 12,
                fontWeight: isHovered ? 'bold' : 'normal',
              },
            }
          }),
          links: graph.links.map((link) => {
            const isConnected =
              connectedNodes.has(link.source) && connectedNodes.has(link.target)
            return {
              source: link.source,
              target: link.target,
              value: link.relation,
              lineStyle: {
                color: isConnected ? '#8b5cf6' : '#3f3f46',
                width: isConnected ? 2 : 1,
                opacity: isConnected ? 0.8 : 0.3,
                curveness: 0.3,
              },
            }
          }),
          categories,
          roam: true,
          label: {
            show: true,
            position: 'right',
            formatter: '{b}',
          },
          lineStyle: {
            color: '#3f3f46',
            width: 1,
            curveness: 0.3,
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 3,
              color: '#8b5cf6',
            },
            itemStyle: {
              shadowBlur: 20,
              shadowColor: 'currentColor',
            },
          },
          force: {
            repulsion: 1500,
            edgeLength: [100, 300],
            gravity: 0.1,
            friction: 0.6,
            layoutAnimation: true,
          },
          scaleLimit: {
            min: 0.5,
            max: 2,
          },
          zoom: zoom,
        },
      ],
    }
  }, [graph, hoveredNode, connectedNodes, zoom])

  // Handle node click
  const onEvents = {
    click: (params: any) => {
      if (params.componentType === 'series' && params.dataType === 'node') {
        const nodeName = params.name
        const node = graph.nodes.find((n) => n.name === nodeName)
        if (node && onNodeClick) {
          const rect = (params.event as any).event
          onNodeClick(node, { x: rect.offsetX, y: rect.offsetY })
        }
      }
    },
    mouseover: (params: any) => {
      if (params.dataType === 'node') {
        setHoveredNode(params.name)
      }
    },
    mouseout: () => {
      setHoveredNode(null)
    },
  }

  // Zoom controls
  const handleZoomIn = () => {
    setZoom((z) => Math.min(2, z + 0.1))
    chartRef.current?.getEchartsInstance()?.setOption({ series: [{ zoom: Math.min(2, zoom + 0.1) }] })
  }

  const handleZoomOut = () => {
    setZoom((z) => Math.max(0.5, z - 0.1))
    chartRef.current?.getEchartsInstance()?.setOption({ series: [{ zoom: Math.max(0.5, zoom - 0.1) }] })
  }

  const handleReset = () => {
    setZoom(1)
    chartRef.current?.getEchartsInstance()?.setOption({ series: [{ zoom: 1 }] })
  }

  return (
    <div className={cn("relative", className)}>
      {/* Graph Container */}
      <div className={cn(
        "rounded-xl overflow-hidden transition-all duration-300",
        isExpanded ? "fixed inset-4 z-50" : "h-full"
      )}>
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-zinc-900/50 to-zinc-800/30" />

        {graph.nodes.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-500">
            <div className="w-16 h-16 rounded-full bg-zinc-800/50 flex items-center justify-center mb-4">
              <RefreshCw className="w-8 h-8 opacity-50" />
            </div>
            <p className="text-sm">No graph data available</p>
            <p className="text-xs mt-1">Analyze sources to generate knowledge graph</p>
          </div>
        ) : (
          <ReactECharts
            ref={chartRef}
            option={option}
            onEvents={onEvents}
            style={{ height: '100%', width: '100%' }}
            opts={{ renderer: 'svg' }}
          />
        )}

        {/* Loading overlay */}
        <AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-zinc-900/80 backdrop-blur-sm flex items-center justify-center"
            >
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-violet-400 animate-spin mx-auto mb-2" />
                <p className="text-sm text-zinc-300">Updating graph...</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Expand/Collapse Button */}
      {graph.nodes.length > 0 && (
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={() => setIsExpanded(!isExpanded)}
          className="absolute top-2 right-2 p-2 rounded-lg bg-zinc-800/80 backdrop-blur-sm border border-zinc-700 hover:bg-zinc-700 transition-colors z-10"
        >
          {isExpanded ? (
            <Minimize2 className="w-4 h-4 text-zinc-300" />
          ) : (
            <Maximize2 className="w-4 h-4 text-zinc-300" />
          )}
        </motion.button>
      )}

      {/* Zoom Controls */}
      {graph.nodes.length > 0 && (
        <div className="absolute bottom-2 right-2 flex flex-col gap-1 z-10">
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={handleZoomIn}
            className="p-2 rounded-lg bg-zinc-800/80 backdrop-blur-sm border border-zinc-700 hover:bg-zinc-700 transition-colors"
          >
            <ZoomIn className="w-4 h-4 text-zinc-300" />
          </motion.button>
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={handleZoomOut}
            className="p-2 rounded-lg bg-zinc-800/80 backdrop-blur-sm border border-zinc-700 hover:bg-zinc-700 transition-colors"
          >
            <ZoomOut className="w-4 h-4 text-zinc-300" />
          </motion.button>
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={handleReset}
            className="p-2 rounded-lg bg-zinc-800/80 backdrop-blur-sm border border-zinc-700 hover:bg-zinc-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-zinc-300" />
          </motion.button>
        </div>
      )}

      {/* Category Legend */}
      {graph.nodes.length > 0 && !isExpanded && (
        <div className="absolute bottom-2 left-2 flex flex-wrap gap-2 z-10">
          {Object.entries(categoryConfig).map(([key, config]) => (
            <div
              key={key}
              className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-zinc-800/80 backdrop-blur-sm border border-zinc-700"
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: config.color }}
              />
              <span className="text-xs text-zinc-300">{config.icon} {config.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// === Graph Node Card (for detailed view) ===
interface GraphNodeCardProps {
  node: GraphNode
  stats?: { video_count: number; occurrence_count: number }
  onClose: () => void
  onGenerateSupercut?: () => void
  taskStatus?: 'pending' | 'processing' | 'completed' | 'error'
  position: { x: number; y: number }
}

export function GraphNodeCard({
  node,
  stats,
  onClose,
  onGenerateSupercut,
  taskStatus,
  position,
}: GraphNodeCardProps) {
  const config = categoryConfig[node.category as keyof typeof categoryConfig]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: -10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, y: -10 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className="fixed z-50 w-80 glass-card border border-zinc-700 rounded-xl overflow-hidden shadow-2xl"
      style={{
        left: Math.min(position.x, window.innerWidth - 340),
        top: Math.min(position.y, window.innerHeight - 200),
      }}
    >
      {/* Header */}
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
              style={{ backgroundColor: config.bgColor, borderColor: config.borderColor, borderWidth: 1 }}
            >
              {config.icon}
            </div>
            <div>
              <h4 className="text-sm font-bold text-zinc-100">{node.name}</h4>
              <span className="text-[10px] text-zinc-500 uppercase tracking-wide">{config.label}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-zinc-800 rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-zinc-500" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Stats */}
        {stats ? (
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-zinc-100">{stats.video_count}</p>
              <p className="text-[10px] text-zinc-500">Videos</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-zinc-100">{stats.occurrence_count}</p>
              <p className="text-[10px] text-zinc-500">Occurrences</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-5 h-5 text-zinc-500 animate-spin" />
          </div>
        )}

        {/* Action */}
        {onGenerateSupercut && (
          <motion.button
            whileTap={{ scale: 0.97 }}
            whileHover={{ scale: 1.02 }}
            onClick={onGenerateSupercut}
            disabled={taskStatus === 'processing'}
            className={cn(
              "w-full py-2.5 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2",
              taskStatus === 'completed'
                ? "bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/30"
                : taskStatus === 'processing'
                ? "bg-blue-500/10 border border-blue-500/20 text-blue-400"
                : "bg-violet-500/20 border border-violet-500/30 text-violet-400 hover:bg-violet-500/30"
            )}
          >
            {taskStatus === 'completed' ? (
              <>
                <span>▶</span>
                <span>Play Supercut</span>
              </>
            ) : taskStatus === 'processing' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <span>✂️</span>
                <span>Generate Entity Supercut</span>
              </>
            )}
          </motion.button>
        )}
      </div>

      {/* Glow effect */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          boxShadow: `inset 0 0 40px ${config.color}15`,
        }}
      />
    </motion.div>
  )
}

// === Animated Graph Background ===
export function AnimatedGraphBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Floating particles */}
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-violet-500/20 rounded-full"
          initial={{
            x: Math.random() * 100 + '%',
            y: Math.random() * 100 + '%',
          }}
          animate={{
            y: [null, Math.random() * 200 - 100 + 'px'],
            opacity: [0.2, 0.5, 0.2],
          }}
          transition={{
            duration: 10 + Math.random() * 20,
            repeat: Infinity,
            repeatType: 'reverse',
            ease: 'easeInOut',
          }}
        />
      ))}

      {/* Gradient blobs */}
      <motion.div
        className="absolute -top-40 -right-40 w-80 h-80 bg-violet-500/10 rounded-full blur-3xl"
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.3, 0.5, 0.3],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
      <motion.div
        className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl"
        animate={{
          scale: [1, 1.3, 1],
          opacity: [0.2, 0.4, 0.2],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </div>
  )
}
