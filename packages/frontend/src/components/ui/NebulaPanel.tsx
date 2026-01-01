/**
 * NebulaPanel - Highlight Nebula 3D Visualization
 *
 * A 3D interactive knowledge galaxy where each node represents a concept.
 * Click on a node to generate a highlight reel video.
 *
 * Features:
 * - 3D force-directed graph with glowing particles
 * - Color-coded nodes by type (person/tech/location/concept)
 * - Click interaction triggers highlight reel generation
 * - Integrated video player for generated content
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import ForceGraph3D from 'react-force-graph-3d'
import SpriteText from 'three-spritetext'
import * as THREE from 'three'
import { Sparkles, Play, Pause, Download, Loader2, Search, X, Volume2, VolumeX } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/stores/app-store'

const API_BASE = 'http://localhost:8000/api'

// Types
interface NebulaNode {
  id: string
  val: number
  group: string
  x?: number
  y?: number
  z?: number
}

interface NebulaLink {
  source: string | NebulaNode
  target: string | NebulaNode
  value: number
}

interface GraphData {
  nodes: NebulaNode[]
  links: NebulaLink[]
}

interface HighlightTask {
  task_id: string
  status: 'pending' | 'searching' | 'sorting' | 'composing' | 'completed' | 'error'
  progress: number
  message: string
  video_url?: string
  concept?: string
  segment_count?: number
  error?: string
}

// Color scheme for node groups
const GROUP_COLORS: Record<string, string> = {
  person: '#ef4444',    // Red
  tech: '#06b6d4',      // Cyan
  location: '#eab308',  // Gold
  concept: '#3b82f6',   // Blue
}

/**
 * NebulaPanel Component
 */
export function NebulaPanel() {
  const graphRef = useRef<any>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const { activePlayer, setActivePlayer } = useAppStore()

  // State
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] })
  const [isLoading, setIsLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<NebulaNode | null>(null)
  const [highlightTask, setHighlightTask] = useState<HighlightTask | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set())
  const [hoverNode, setHoverNode] = useState<NebulaNode | null>(null)

  // Fetch nebula structure
  const fetchNebulaData = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE}/montage/nebula?top_k=80`)
      if (response.ok) {
        const data = await response.json()
        setGraphData({
          nodes: data.nodes || [],
          links: data.links || [],
        })
      }
    } catch (error) {
      console.error('Failed to fetch nebula data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchNebulaData()
  }, [fetchNebulaData])

  // Handle node click - start highlight generation
  const handleNodeClick = useCallback(async (node: NebulaNode) => {
    setSelectedNode(node)
    setHighlightTask({
      task_id: '',
      status: 'pending',
      progress: 0,
      message: `正在点亮 "${node.id}" 的高光时刻...`,
    })

    // Trigger bloom effect
    setHighlightNodes(new Set([node.id]))
    setTimeout(() => setHighlightNodes(new Set()), 2000)

    try {
      const response = await fetch(`${API_BASE}/montage/highlight`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          concept: node.id,
          top_k: 10,
          max_duration: 90.0,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        setHighlightTask(data)

        if (data.task_id) {
          pollTask(data.task_id)
        }
      } else {
        const error = await response.json()
        setHighlightTask({
          task_id: '',
          status: 'error',
          progress: 0,
          message: error.detail || '生成失败',
          error: error.detail,
        })
      }
    } catch (error) {
      setHighlightTask({
        task_id: '',
        status: 'error',
        progress: 0,
        message: '网络连接失败',
        error: String(error),
      })
    }
  }, [])

  // Poll task status
  const pollTask = async (taskId: string) => {
    try {
      const response = await fetch(`${API_BASE}/montage/highlight/${taskId}`)
      if (response.ok) {
        const data: HighlightTask = await response.json()
        setHighlightTask(data)

        if (data.status !== 'completed' && data.status !== 'error') {
          setTimeout(() => pollTask(taskId), 2000)
        }
      }
    } catch (error) {
      console.error('Poll error:', error)
    }
  }

  // Search functionality - fly to node
  const handleSearch = useCallback(() => {
    if (!searchQuery.trim() || !graphRef.current) return

    const matchingNode = graphData.nodes.find(
      n => n.id.toLowerCase().includes(searchQuery.toLowerCase())
    )

    if (matchingNode && matchingNode.x !== undefined) {
      // Fly camera to node
      graphRef.current.cameraPosition(
        { x: matchingNode.x, y: matchingNode.y, z: matchingNode.z! + 150 },
        { x: matchingNode.x, y: matchingNode.y, z: matchingNode.z },
        2000
      )
      setHighlightNodes(new Set([matchingNode.id]))
      setTimeout(() => setHighlightNodes(new Set()), 3000)
    }
  }, [searchQuery, graphData.nodes])

  // Video controls
  const togglePlay = useCallback(() => {
    if (!videoRef.current) return

    if (isPlaying) {
      videoRef.current.pause()
    } else {
      setActivePlayer('nebula')
      videoRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }, [isPlaying, setActivePlayer])

  const toggleMute = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }, [isMuted])

  // Pause when another player becomes active
  useEffect(() => {
    if (activePlayer !== 'nebula' && activePlayer !== null && isPlaying) {
      videoRef.current?.pause()
      setIsPlaying(false)
    }
  }, [activePlayer, isPlaying])

  // Close player
  const closePlayer = useCallback(() => {
    setSelectedNode(null)
    setHighlightTask(null)
    if (videoRef.current) {
      videoRef.current.pause()
    }
    setIsPlaying(false)
  }, [])

  // Custom node rendering with enhanced glow effect
  const nodeThreeObject = useCallback((node: NebulaNode) => {
    const isHighlighted = highlightNodes.has(node.id)
    const isHovered = hoverNode?.id === node.id
    const color = GROUP_COLORS[node.group] || GROUP_COLORS.concept

    // Create a group to hold mesh and label
    const group = new THREE.Group()

    // Calculate size based on value (frequency)
    // Higher frequency = larger and brighter
    const baseRadius = Math.max(2, Math.min(8, Math.sqrt(node.val) * 0.8))
    const radius = isHighlighted || isHovered ? baseRadius * 1.3 : baseRadius

    // Create glowing sphere mesh with MeshLambertMaterial
    const geometry = new THREE.SphereGeometry(radius, 16, 16)
    const material = new THREE.MeshLambertMaterial({
      color: color,
      transparent: true,
      opacity: isHighlighted ? 1.0 : 0.85,
      emissive: new THREE.Color(color),
      emissiveIntensity: isHighlighted ? 1.5 : Math.min(1.2, node.val / 8), // CRITICAL: brightness scales with frequency
    })

    const sphere = new THREE.Mesh(geometry, material)
    group.add(sphere)

    // Add outer glow sprite for enhanced effect
    const glowSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: createGlowTexture(color, isHighlighted || isHovered),
        transparent: true,
        opacity: isHighlighted ? 0.9 : 0.6,
        blending: THREE.AdditiveBlending,
      })
    )
    const glowSize = radius * 4
    glowSprite.scale.set(glowSize, glowSize, 1)
    group.add(glowSprite)

    // Add label for high-value nodes or hovered
    if (node.val > 8 || isHovered || isHighlighted) {
      const label = new SpriteText(node.id)
      label.color = '#ffffff'
      label.textHeight = isHovered ? 5 : 4
      label.backgroundColor = 'rgba(0,0,0,0.6)'
      label.padding = 2
      label.borderRadius = 3
      label.position.y = radius + 8
      group.add(label as any)
    }

    return group
  }, [highlightNodes, hoverNode])

  // Memoize graph config with enhanced link styling
  const graphConfig = useMemo(() => ({
    backgroundColor: '#030712',
    linkColor: () => 'rgba(255, 255, 255, 0.2)', // Semi-transparent white lines
    linkWidth: 0.5, // Fixed thin line width
    linkOpacity: 0.3,
    nodeRelSize: 1,
    warmupTicks: 100,
    cooldownTicks: 0,
    // Add ambient light for MeshLambertMaterial to work
    onEngineInit: (engine: any) => {
      // Add ambient light
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
      engine.scene().add(ambientLight)

      // Add point lights for better 3D effect
      const pointLight1 = new THREE.PointLight(0x6366f1, 1.5, 1000)
      pointLight1.position.set(200, 200, 200)
      engine.scene().add(pointLight1)

      const pointLight2 = new THREE.PointLight(0x06b6d4, 1.2, 1000)
      pointLight2.position.set(-200, -100, 200)
      engine.scene().add(pointLight2)
    },
  }), [])

  return (
    <div className="relative w-full h-full bg-[#030712] overflow-hidden">
      {/* Search Bar */}
      <div className="absolute top-4 left-4 right-4 z-20 flex items-center gap-2">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="搜索概念，按 Enter 飞往..."
            className="w-full pl-10 pr-4 py-2 bg-zinc-900/80 backdrop-blur-sm border border-zinc-800 rounded-xl text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
        <button
          onClick={fetchNebulaData}
          disabled={isLoading}
          className="p-2 bg-zinc-900/80 backdrop-blur-sm border border-zinc-800 rounded-xl hover:border-zinc-700 transition-colors"
        >
          <Sparkles className={cn('w-4 h-4 text-cyan-400', isLoading && 'animate-spin')} />
        </button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-10 bg-zinc-900/80 backdrop-blur-sm border border-zinc-800 rounded-xl p-3">
        <div className="text-[10px] text-zinc-500 mb-2 uppercase tracking-wider">Node Types</div>
        <div className="flex flex-col gap-1.5 text-xs">
          {Object.entries(GROUP_COLORS).map(([group, color]) => (
            <div key={group} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
              />
              <span className="text-zinc-400 capitalize">{group}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 3D Graph */}
      {isLoading ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-3" />
            <p className="text-sm text-zinc-400">Loading Highlight Nebula...</p>
          </div>
        </div>
      ) : graphData.nodes.length === 0 ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-zinc-500">
            <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">暂无数据</p>
            <p className="text-xs mt-1">请先上传并分析视频</p>
          </div>
        </div>
      ) : (
        <ForceGraph3D
          ref={graphRef}
          graphData={graphData}
          nodeThreeObject={nodeThreeObject}
          onNodeClick={handleNodeClick}
          onNodeHover={(node) => setHoverNode(node as NebulaNode | null)}
          {...graphConfig}
        />
      )}

      {/* Highlight Player (Slide-in from right) */}
      <div
        className={cn(
          'absolute right-4 bottom-4 w-[380px] bg-zinc-900/95 backdrop-blur-xl border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl transition-all duration-300 z-30',
          selectedNode ? 'translate-x-0 opacity-100' : 'translate-x-[120%] opacity-0'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-bold text-white">
              {selectedNode?.id || 'Highlight'}
            </span>
            {selectedNode && (
              <span
                className="text-[10px] px-2 py-0.5 rounded-full uppercase"
                style={{
                  backgroundColor: `${GROUP_COLORS[selectedNode.group]}20`,
                  color: GROUP_COLORS[selectedNode.group],
                }}
              >
                {selectedNode.group}
              </span>
            )}
          </div>
          <button
            onClick={closePlayer}
            className="p-1 hover:bg-zinc-800 rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-3">
          {highlightTask?.status === 'completed' && highlightTask.video_url ? (
            // Video Player
            <div className="space-y-3">
              <div className="relative rounded-xl overflow-hidden bg-black aspect-video group/player">
                <video
                  ref={videoRef}
                  src={`http://localhost:8000${highlightTask.video_url}`}
                  className="w-full h-full object-contain"
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  onEnded={() => setIsPlaying(false)}
                />

                {/* Play overlay */}
                {!isPlaying && (
                  <div
                    onClick={togglePlay}
                    className="absolute inset-0 flex items-center justify-center bg-black/30 cursor-pointer group-hover/player:bg-black/40 transition-colors"
                  >
                    <div className="w-14 h-14 rounded-full bg-white/20 backdrop-blur flex items-center justify-center hover:bg-white/30 transition-colors">
                      <Play className="w-6 h-6 text-white ml-1" />
                    </div>
                  </div>
                )}

                {/* Controls */}
                <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover/player:opacity-100 transition-opacity">
                  <div className="flex items-center gap-2">
                    <button onClick={togglePlay} className="p-1.5 rounded-full bg-white/10 hover:bg-white/20">
                      {isPlaying ? <Pause className="w-3 h-3 text-white" /> : <Play className="w-3 h-3 text-white ml-0.5" />}
                    </button>
                    <button onClick={toggleMute} className="p-1.5 rounded-full bg-white/10 hover:bg-white/20">
                      {isMuted ? <VolumeX className="w-3 h-3 text-white" /> : <Volume2 className="w-3 h-3 text-white" />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Info */}
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>{highlightTask.segment_count || 0} 个片段</span>
                <a
                  href={`http://localhost:8000${highlightTask.video_url}`}
                  download
                  className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300"
                >
                  <Download className="w-3 h-3" />
                  下载
                </a>
              </div>
            </div>
          ) : highlightTask?.status === 'error' ? (
            // Error state
            <div className="text-center py-6">
              <div className="w-12 h-12 rounded-full bg-red-900/30 flex items-center justify-center mx-auto mb-3">
                <span className="text-xl">😵</span>
              </div>
              <p className="text-sm text-red-400">{highlightTask.message}</p>
              <button
                onClick={() => selectedNode && handleNodeClick(selectedNode)}
                className="mt-3 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-xs text-zinc-300"
              >
                重试
              </button>
            </div>
          ) : (
            // Loading state
            <div className="text-center py-8">
              <div className="relative w-16 h-16 mx-auto mb-4">
                {/* Spinning nebula effect */}
                <div
                  className="absolute inset-0 rounded-full bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 animate-spin"
                  style={{ animationDuration: '3s' }}
                />
                <div className="absolute inset-2 rounded-full bg-zinc-900" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-cyan-400" />
                </div>
              </div>
              <p className="text-sm text-cyan-300 mb-1">
                {getStatusMessage(highlightTask?.status, highlightTask?.progress || 0)}
              </p>
              <p className="text-xs text-zinc-500">{highlightTask?.message}</p>
              {/* Progress bar */}
              <div className="mt-4 w-48 h-1 bg-zinc-800 rounded-full mx-auto overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all duration-300"
                  style={{ width: `${highlightTask?.progress || 0}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Helper: Create enhanced glow texture for nodes
function createGlowTexture(color: string, intense: boolean = false): THREE.Texture {
  const canvas = document.createElement('canvas')
  canvas.width = 128 // Higher resolution for better quality
  canvas.height = 128
  const ctx = canvas.getContext('2d')!

  const centerX = 64
  const centerY = 64

  // Create radial gradient for glow - brighter core
  const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, 64)

  if (intense) {
    // Highlighted node - very bright
    gradient.addColorStop(0, '#ffffff')
    gradient.addColorStop(0.1, color)
    gradient.addColorStop(0.3, `${color}cc`)
    gradient.addColorStop(0.5, `${color}66`)
    gradient.addColorStop(0.7, `${color}22`)
    gradient.addColorStop(1, 'transparent')
  } else {
    // Normal node - still glowing
    gradient.addColorStop(0, `${color}ff`)
    gradient.addColorStop(0.2, `${color}bb`)
    gradient.addColorStop(0.4, `${color}66`)
    gradient.addColorStop(0.6, `${color}33`)
    gradient.addColorStop(1, 'transparent')
  }

  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, 128, 128)

  const texture = new THREE.CanvasTexture(canvas)
  texture.needsUpdate = true
  return texture
}

// Helper: Get status message
function getStatusMessage(status: string | undefined, progress: number): string {
  switch (status) {
    case 'searching':
      return '🔍 正在搜索相关片段...'
    case 'sorting':
      return '🎯 AI 正在编排叙事顺序...'
    case 'composing':
      return '🎬 正在合成高光视频...'
    default:
      return `✨ ${progress}% 完成`
  }
}
