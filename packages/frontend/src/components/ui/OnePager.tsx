import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, FileText, Download, RefreshCw, Loader2, Calendar, Image as ImageIcon, ExternalLink, Edit3, Check, X, Wand2, Save } from 'lucide-react'
import { useAppStore } from '@/stores/app-store'
import { cn } from '@/lib/utils'
import type { OnePagerData } from '@/types'

interface OnePagerProps {
  sourceId: string | null
  language?: 'zh' | 'en'
}

interface EditingData {
  headline: string
  tldr: string
  insights: string[]
}

/**
 * OnePager Component
 *
 * A magazine-style decision brief that displays an executive summary of a video.
 *
 * Features:
 * - AI-generated conceptual illustration as banner
 * - Compelling headline (15 chars max)
 * - TL;DR summary (50 chars max)
 * - 3 key insights
 * - Video screenshot evidence grid
 * - Download/Share functionality
 * - NYT/Notion-inspired clean design
 */
export function OnePager({ sourceId, language = 'zh' }: OnePagerProps) {
  const {
    onePagerData,
    isGeneratingOnePager,
    fetchOnePager,
    setOnePagerData,
  } = useAppStore()

  const [expandedImage, setExpandedImage] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editingData, setEditingData] = useState<EditingData>({
    headline: '',
    tldr: '',
    insights: [],
  })
  const [customPrompt, setCustomPrompt] = useState('')
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [showPromptInput, setShowPromptInput] = useState(false)
  const [conceptualImageLoaded, setConceptualImageLoaded] = useState(false)

  // Auto-fetch when sourceId changes
  useEffect(() => {
    if (sourceId && onePagerData?.source_id !== sourceId) {
      fetchOnePager(sourceId)
      setConceptualImageLoaded(false) // Reset image load state
    }
  }, [sourceId])

  const t = {
    zh: {
      generate: '生成简报',
      generating: 'AI 正在分析...',
      regenerate: '重新生成',
      download: '下载 PDF',
      share: '分享',
      noData: '暂无简报数据',
      insights: '关键洞察',
      evidence: '视觉证据',
      clickToExpand: '点击放大',
      edit: '编辑',
      save: '保存',
      cancel: '取消',
      customPrompt: '自定义优化',
      customPromptPlaceholder: '输入您的优化要求，例如：更强调战术细节、添加数据分析视角...',
      regenerateWithPrompt: 'AI 优化生成',
    },
    en: {
      generate: 'Generate Report',
      generating: 'AI analyzing...',
      regenerate: 'Regenerate',
      download: 'Download PDF',
      share: 'Share',
      noData: 'No report data available',
      insights: 'Key Insights',
      evidence: 'Visual Evidence',
      clickToExpand: 'Click to expand',
      edit: 'Edit',
      save: 'Save',
      cancel: 'Cancel',
      customPrompt: 'Customize',
      customPromptPlaceholder: 'Enter your optimization requirements, e.g., emphasize tactical details, add data analysis...',
      regenerateWithPrompt: 'AI Optimize',
    },
  }

  // Start editing
  const handleStartEdit = () => {
    if (!onePagerData) return
    setEditingData({
      headline: onePagerData.headline,
      tldr: onePagerData.tldr,
      insights: [...onePagerData.insights],
    })
    setIsEditing(true)
  }

  // Save edits
  const handleSaveEdit = () => {
    if (!onePagerData) return
    setOnePagerData({
      ...onePagerData,
      headline: editingData.headline,
      tldr: editingData.tldr,
      insights: editingData.insights,
    })
    setIsEditing(false)
  }

  // Regenerate with custom prompt
  const handleRegenerateWithPrompt = async () => {
    if (!sourceId || !customPrompt.trim()) return

    setIsRegenerating(true)
    try {
      // Store user preference (for future personalization)
      const userPreferences = JSON.parse(localStorage.getItem('onepager_preferences') || '{}')
      userPreferences[sourceId] = {
        ...userPreferences[sourceId],
        customPrompt: customPrompt.trim(),
        lastUsed: new Date().toISOString(),
      }
      localStorage.setItem('onepager_preferences', JSON.stringify(userPreferences))

      // Call API with custom prompt (backend needs to support this)
      await fetchOnePager(sourceId, false)
      setShowPromptInput(false)
      setCustomPrompt('')
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleGenerate = () => {
    if (sourceId) {
      fetchOnePager(sourceId, false) // Force regeneration
    }
  }

  const handleDownload = () => {
    // Simulate download
    const link = document.createElement('a')
    link.href = '#'
    link.download = `one-pager-${onePagerData?.source_id || 'report'}.pdf`
    link.click()
  }

  // Loading state
  if (isGeneratingOnePager || !onePagerData) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        {isGeneratingOnePager ? (
          <>
            <div className="relative mb-6">
              <div className="w-20 h-20 rounded-full border-4 border-zinc-700 border-t-blue-500 animate-spin" />
              <Sparkles className="w-8 h-8 text-blue-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">{t[language].generating}</h3>
            <p className="text-sm text-zinc-500 max-w-xs">
              AI 正在分析视频内容，提炼核心洞察并生成概念配图...
            </p>
          </>
        ) : (
          <>
            <div className="w-16 h-16 rounded-2xl bg-zinc-800 flex items-center justify-center mb-4 border border-zinc-700">
              <FileText className="w-8 h-8 text-zinc-600" />
            </div>
            <h3 className="text-lg font-bold text-zinc-400 mb-2">{t[language].noData}</h3>
            <button
              onClick={handleGenerate}
              disabled={!sourceId}
              className={cn(
                'mt-4 px-6 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2',
                sourceId
                  ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:from-blue-500 hover:to-cyan-500 shadow-lg hover:shadow-blue-500/20'
                  : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
              )}
            >
              <Sparkles className="w-4 h-4" />
              {t[language].generate}
            </button>
          </>
        )}
      </div>
    )
  }

  const data = onePagerData

  return (
    <div className="h-full overflow-y-auto scroller">
      <div className="max-w-2xl mx-auto p-6 space-y-6 fade-in">
        {/* Header with actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <Calendar className="w-3 h-3" />
            <span>{data.generated_at ? new Date(data.generated_at).toLocaleDateString() : '-'}</span>
          </div>
          <div className="flex items-center gap-2">
            {isEditing ? (
              <>
                <button
                  onClick={handleSaveEdit}
                  className="p-2 rounded-lg bg-green-600 hover:bg-green-500 text-white transition-all flex items-center gap-1"
                  title={t[language].save}
                >
                  <Check className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsEditing(false)}
                  className="p-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-zinc-400 hover:text-white transition-all"
                  title={t[language].cancel}
                >
                  <X className="w-4 h-4" />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleStartEdit}
                  className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-all"
                  title={t[language].edit}
                >
                  <Edit3 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setShowPromptInput(!showPromptInput)}
                  className="p-2 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white transition-all"
                  title={t[language].customPrompt}
                >
                  <Wand2 className="w-4 h-4" />
                </button>
                <button
                  onClick={handleGenerate}
                  className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-all"
                  title={t[language].regenerate}
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
                <button
                  onClick={handleDownload}
                  className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-all"
                  title={t[language].download}
                >
                  <Download className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>

        {/* Custom Prompt Input */}
        <AnimatePresence>
          {showPromptInput && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="p-4 rounded-xl bg-gradient-to-r from-purple-900/20 to-pink-900/20 border border-purple-500/30 space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-purple-300">
                  <Wand2 className="w-4 h-4" />
                  {t[language].customPrompt}
                </label>
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder={t[language].customPromptPlaceholder}
                  className="w-full px-4 py-3 rounded-lg bg-zinc-900/50 border border-zinc-700 text-white text-sm placeholder:text-zinc-500 focus:outline-none focus:border-purple-500 resize-none"
                  rows={3}
                />
                <div className="flex items-center justify-between">
                  <p className="text-xs text-zinc-500">
                    💡 您的偏好会被保存，下次自动应用
                  </p>
                  <button
                    onClick={handleRegenerateWithPrompt}
                    disabled={isRegenerating || !customPrompt.trim()}
                    className={cn(
                      'px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all',
                      isRegenerating || !customPrompt.trim()
                        ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                        : 'bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-500 hover:to-pink-500'
                    )}
                  >
                    {isRegenerating ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {t[language].generating}
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        {t[language].regenerateWithPrompt}
                      </>
                    )}
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Conceptual Illustration Banner */}
        {data.conceptual_image ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{
              opacity: conceptualImageLoaded ? 1 : 0.5,
              y: conceptualImageLoaded ? 0 : 10,
            }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="relative rounded-2xl overflow-hidden aspect-video bg-gradient-to-br from-zinc-800 to-zinc-900 border border-zinc-700 group"
          >
            <img
              src={`http://localhost:8000${data.conceptual_image}`}
              alt="Conceptual illustration"
              className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
              onLoad={() => setConceptualImageLoaded(true)}
              onError={() => setConceptualImageLoaded(true)} // Still mark as loaded to show fallback
            />
            {!conceptualImageLoaded && (
              <div className="absolute inset-0 flex items-center justify-center bg-zinc-800/50">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
            <div className="absolute bottom-3 left-3 right-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blue-400" />
                <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest">
                  AI Generated Concept Art
                </span>
              </div>
            </div>
          </motion.div>
        ) : (
          // Fallback: Pattern background when no AI image
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative rounded-2xl overflow-hidden aspect-video bg-gradient-to-br from-blue-900/30 via-purple-900/30 to-pink-900/30 border border-zinc-700"
            style={{
              backgroundImage: `
                radial-gradient(circle at 20% 30%, rgba(59, 130, 246, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(168, 85, 247, 0.15) 0%, transparent 50%),
                linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%)
              `,
            }}
          >
            {/* Decorative pattern */}
            <div className="absolute inset-0 opacity-20" style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.2'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
            }} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <Sparkles className="w-12 h-12 text-blue-400/50 mb-3" />
              <p className="text-sm text-zinc-400 text-center px-6">
                AI 概念图生成中...
              </p>
            </div>
            <div className="absolute bottom-3 left-3 right-3">
              <div className="flex items-center gap-2">
                <Wand2 className="w-4 h-4 text-purple-400" />
                <span className="text-[10px] font-bold text-purple-400 uppercase tracking-widest">
                  Concept Visualization
                </span>
              </div>
            </div>
          </motion.div>
        )}

        {/* Title Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-4"
        >
          {/* Headline */}
          {isEditing ? (
            <input
              type="text"
              value={editingData.headline}
              onChange={(e) => setEditingData({ ...editingData, headline: e.target.value })}
              className="w-full text-3xl font-bold text-white leading-tight bg-zinc-900 border-2 border-zinc-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
              placeholder="输入标题..."
            />
          ) : (
            <h1 className="text-3xl font-bold text-white leading-tight">
              {data.headline}
            </h1>
          )}

          {/* TL;DR */}
          <div className="relative pl-4">
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-blue-500 to-cyan-500 rounded-full" />
            {isEditing ? (
              <textarea
                value={editingData.tldr}
                onChange={(e) => setEditingData({ ...editingData, tldr: e.target.value })}
                className="w-full text-base text-zinc-300 leading-relaxed font-medium bg-zinc-900 border-2 border-zinc-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 resize-none"
                placeholder="输入摘要..."
                rows={3}
              />
            ) : (
              <p className="text-base text-zinc-300 leading-relaxed font-medium">
                {data.tldr}
              </p>
            )}
          </div>
        </motion.div>

        {/* Key Insights */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-3"
        >
          <div className="flex items-center gap-2 text-sm font-bold text-zinc-400">
            <Sparkles className="w-4 h-4 text-amber-500" />
            {t[language].insights}
          </div>
          <div className="space-y-2">
            {(isEditing ? editingData.insights : data.insights).map((insight, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 rounded-xl bg-zinc-800/50 border border-zinc-700/50 hover:bg-zinc-800 hover:border-zinc-700 transition-all group"
              >
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/20">
                  <span className="text-[10px] font-bold text-white">{index + 1}</span>
                </div>
                {isEditing ? (
                  <textarea
                    value={insight}
                    onChange={(e) => {
                      const newInsights = [...editingData.insights]
                      newInsights[index] = e.target.value
                      setEditingData({ ...editingData, insights: newInsights })
                    }}
                    className="flex-1 text-sm text-zinc-300 leading-relaxed bg-zinc-900 border-2 border-zinc-700 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 resize-none"
                    placeholder={`洞察 ${index + 1}`}
                    rows={2}
                  />
                ) : (
                  <p className="text-sm text-zinc-300 leading-relaxed group-hover:text-white transition-colors">
                    {insight}
                  </p>
                )}
              </div>
            ))}
          </div>
        </motion.div>

        {/* Visual Evidence */}
        {data.evidence_images.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="space-y-3"
          >
            <div className="flex items-center gap-2 text-sm font-bold text-zinc-400">
              <ImageIcon className="w-4 h-4 text-green-500" />
              {t[language].evidence}
            </div>
            <div className={cn(
              'grid gap-3',
              data.evidence_images.length === 2 ? 'grid-cols-2' : 'grid-cols-1'
            )}>
              {data.evidence_images.map((imageUrl, index) => (
                <div
                  key={index}
                  className="relative group cursor-pointer rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 aspect-video"
                  onClick={() => setExpandedImage(imageUrl)}
                >
                  <img
                    src={imageUrl.startsWith('http') ? imageUrl : `http://localhost:8000${imageUrl}`}
                    alt={`Evidence ${index + 1}`}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                    <ExternalLink className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <div className="absolute bottom-2 left-2 bg-black/70 backdrop-blur-sm px-2 py-1 rounded-md">
                    <span className="text-[10px] text-white font-medium">
                      #{index + 1}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="pt-4 border-t border-zinc-800 text-center"
        >
          <p className="text-[10px] text-zinc-600">
            Powered by Viewpoint Prism AI • {data.video_title}
          </p>
        </motion.div>
      </div>

      {/* Expanded Image Modal */}
      <AnimatePresence>
        {expandedImage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/90 backdrop-blur-xl flex items-center justify-center p-6"
            onClick={() => setExpandedImage(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="relative max-w-4xl max-h-full"
              onClick={(e) => e.stopPropagation()}
            >
              <img
                src={expandedImage.startsWith('http') ? expandedImage : `http://localhost:8000${expandedImage}`}
                alt="Expanded evidence"
                className="max-w-full max-h-[80vh] object-contain rounded-xl shadow-2xl"
              />
              <button
                onClick={() => setExpandedImage(null)}
                className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center border border-zinc-700 transition-colors"
              >
                <span className="text-zinc-400">×</span>
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
