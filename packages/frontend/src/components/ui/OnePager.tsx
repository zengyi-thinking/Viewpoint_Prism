import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, FileText, RefreshCw, Loader2, Calendar, Image as ImageIcon, ExternalLink, Edit3, Check, X, Wand2, Printer } from 'lucide-react'
import { useAppStore } from '@/stores/app-store'
import { cn } from '@/lib/utils'
import type { EvidenceItem } from '@/types'

interface OnePagerProps {
  sourceIds: string[]  // Changed: accept array of source IDs
  language?: 'zh' | 'en'
}

interface EditingData {
  headline: string
  tldr: string
  insights: string[]
}

/**
 * OnePager Component - Magazine Style Edition
 *
 * A magazine-style decision brief that displays an executive summary of selected videos.
 *
 * Features:
 * - AI-generated conceptual illustration as banner
 * - Compelling headline (15 chars max)
 * - TL;DR summary (50 chars max)
 * - Insight-Evidence Pairing layout (观点-证据配对)
 * - Video screenshots with AI-generated captions (Qwen2.5-VL)
 * - PDF Export functionality
 * - NYT/Notion-inspired clean design
 */
export function OnePager({ sourceIds, language = 'zh' }: OnePagerProps) {
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
  const [isExportingPdf, setIsExportingPdf] = useState(false)
  const onePagerRef = useRef<HTMLDivElement>(null)

  // Helper to compare source ID arrays
  const sourceIdsMatch = (arr1: string[], arr2: string[]) => {
    if (arr1.length !== arr2.length) return false
    const sorted1 = [...arr1].sort()
    const sorted2 = [...arr2].sort()
    return sorted1.every((id, i) => id === sorted2[i])
  }

  // Auto-fetch when sourceIds change
  useEffect(() => {
    if (sourceIds.length > 0 && (!onePagerData || !sourceIdsMatch(sourceIds, onePagerData.source_ids))) {
      fetchOnePager(sourceIds)
      setConceptualImageLoaded(false) // Reset image load state
    }
  }, [sourceIds])

  const t = {
    zh: {
      generate: '生成简报',
      generating: 'AI 正在分析...',
      regenerate: '重新生成',
      download: '导出 PDF',
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
      exporting: '导出中...',
      exportSuccess: '导出成功',
    },
    en: {
      generate: 'Generate Report',
      generating: 'AI analyzing...',
      regenerate: 'Regenerate',
      download: 'Export PDF',
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
      exporting: 'Exporting...',
      exportSuccess: 'Export Success',
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
    if (sourceIds.length === 0 || !customPrompt.trim()) return

    setIsRegenerating(true)
    try {
      // Store user preference (for future personalization)
      const userPreferences = JSON.parse(localStorage.getItem('onepager_preferences') || '{}')
      const prefKey = sourceIds.join(',')
      userPreferences[prefKey] = {
        ...userPreferences[prefKey],
        customPrompt: customPrompt.trim(),
        lastUsed: new Date().toISOString(),
      }
      localStorage.setItem('onepager_preferences', JSON.stringify(userPreferences))

      // Call API with custom prompt (backend needs to support this)
      await fetchOnePager(sourceIds, false)
      setShowPromptInput(false)
      setCustomPrompt('')
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleGenerate = () => {
    if (sourceIds.length > 0) {
      fetchOnePager(sourceIds, false) // Force regeneration
    }
  }

  // PDF Export using html2canvas and jspdf
  const handleExportPdf = async () => {
    if (!onePagerRef.current || !onePagerData) return

    setIsExportingPdf(true)
    try {
      // Dynamic import to reduce bundle size
      const html2canvas = (await import('html2canvas')).default
      const { jsPDF } = await import('jspdf')

      // Capture the OnePager content
      const canvas = await html2canvas(onePagerRef.current, {
        scale: 2, // Higher resolution
        useCORS: true, // Handle cross-origin images
        allowTaint: true,
        backgroundColor: '#121214', // Match dark theme
        logging: false,
      })

      // Calculate dimensions for A4
      const imgWidth = 210 // A4 width in mm
      const pageHeight = 297 // A4 height in mm
      const imgHeight = (canvas.height * imgWidth) / canvas.width
      let heightLeft = imgHeight

      // Create PDF
      const pdf = new jsPDF('p', 'mm', 'a4')
      let position = 0

      // Add image to PDF (handle multi-page if needed)
      pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= pageHeight

      while (heightLeft > 0) {
        position = heightLeft - imgHeight
        pdf.addPage()
        pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight)
        heightLeft -= pageHeight
      }

      // Generate filename with date
      const date = new Date().toISOString().slice(0, 10)
      const filename = `Viewpoint_Report_${date}.pdf`

      // Download
      pdf.save(filename)
    } catch (error) {
      console.error('PDF export failed:', error)
      alert('PDF 导出失败，请重试')
    } finally {
      setIsExportingPdf(false)
    }
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
              AI 正在分析 {sourceIds.length} 个视频内容，提炼核心洞察、生成概念配图和证据解读...
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
              disabled={sourceIds.length === 0}
              className={cn(
                'mt-4 px-6 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2',
                sourceIds.length > 0
                  ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white hover:from-blue-500 hover:to-cyan-500 shadow-lg hover:shadow-blue-500/20'
                  : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
              )}
            >
              <Sparkles className="w-4 h-4" />
              {t[language].generate}
            </button>
            {sourceIds.length === 0 && (
              <p className="mt-2 text-xs text-zinc-500">请先在左侧勾选视频源</p>
            )}
          </>
        )}
      </div>
    )
  }

  const data = onePagerData
  // Use evidence_items if available, otherwise fallback to evidence_images
  const evidenceItems: EvidenceItem[] = data.evidence_items?.length > 0
    ? data.evidence_items
    : (data.evidence_images || []).map(url => ({ url, caption: '', related_insight_index: null }))

  return (
    <div className="h-full overflow-y-auto scroller">
      {/* Header with actions - outside print area */}
      <div className="sticky top-0 z-20 p-4 bg-[#121214]/95 backdrop-blur-sm border-b border-zinc-800/50">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
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
                  onClick={handleExportPdf}
                  disabled={isExportingPdf}
                  className={cn(
                    'p-2 rounded-lg transition-all flex items-center gap-1',
                    isExportingPdf
                      ? 'bg-blue-500/30 text-blue-300 cursor-wait'
                      : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white'
                  )}
                  title={t[language].download}
                >
                  {isExportingPdf ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Printer className="w-4 h-4" />
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Custom Prompt Input */}
      <AnimatePresence>
        {showPromptInput && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden px-6 pt-4"
          >
            <div className="max-w-2xl mx-auto p-4 rounded-xl bg-gradient-to-r from-purple-900/20 to-pink-900/20 border border-purple-500/30 space-y-3">
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

      {/* Main Content - PDF Export Area */}
      <div ref={onePagerRef} className="max-w-2xl mx-auto p-6 space-y-8 fade-in bg-[#121214]">
        {/* Banner: Conceptual Illustration + Headline */}
        {data.conceptual_image ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{
              opacity: conceptualImageLoaded ? 1 : 0.5,
              y: conceptualImageLoaded ? 0 : 10,
            }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="relative rounded-2xl overflow-hidden aspect-[16/9] bg-gradient-to-br from-zinc-800 to-zinc-900 border border-zinc-700 group"
          >
            <img
              src={`http://localhost:8000${data.conceptual_image}`}
              alt="Conceptual illustration"
              className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
              crossOrigin="anonymous"
              onLoad={() => setConceptualImageLoaded(true)}
              onError={() => setConceptualImageLoaded(true)}
            />
            {!conceptualImageLoaded && (
              <div className="absolute inset-0 flex items-center justify-center bg-zinc-800/50">
                <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
            {/* Headline overlay on banner */}
            <div className="absolute bottom-0 left-0 right-0 p-6">
              {isEditing ? (
                <input
                  type="text"
                  value={editingData.headline}
                  onChange={(e) => setEditingData({ ...editingData, headline: e.target.value })}
                  className="w-full text-3xl font-bold text-white leading-tight bg-zinc-900/80 border-2 border-zinc-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
                  placeholder="输入标题..."
                />
              ) : (
                <h1 className="text-3xl font-bold text-white leading-tight drop-shadow-lg">
                  {data.headline}
                </h1>
              )}
              <div className="flex items-center gap-2 mt-2">
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
            className="relative rounded-2xl overflow-hidden aspect-[16/9] bg-gradient-to-br from-blue-900/30 via-purple-900/30 to-pink-900/30 border border-zinc-700"
            style={{
              backgroundImage: `
                radial-gradient(circle at 20% 30%, rgba(59, 130, 246, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(168, 85, 247, 0.15) 0%, transparent 50%),
                linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%)
              `,
            }}
          >
            <div className="absolute inset-0 flex flex-col items-center justify-center p-6">
              {isEditing ? (
                <input
                  type="text"
                  value={editingData.headline}
                  onChange={(e) => setEditingData({ ...editingData, headline: e.target.value })}
                  className="w-full text-3xl font-bold text-white leading-tight text-center bg-zinc-900/80 border-2 border-zinc-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
                  placeholder="输入标题..."
                />
              ) : (
                <h1 className="text-3xl font-bold text-white leading-tight text-center drop-shadow-lg">
                  {data.headline}
                </h1>
              )}
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

        {/* TL;DR Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="relative pl-4"
        >
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-blue-500 to-cyan-500 rounded-full" />
          {isEditing ? (
            <textarea
              value={editingData.tldr}
              onChange={(e) => setEditingData({ ...editingData, tldr: e.target.value })}
              className="w-full text-lg text-zinc-300 leading-relaxed font-medium bg-zinc-900 border-2 border-zinc-700 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 resize-none"
              placeholder="输入摘要..."
              rows={3}
            />
          ) : (
            <p className="text-lg text-zinc-300 leading-relaxed font-medium">
              {data.tldr}
            </p>
          )}
        </motion.div>

        {/* Insight-Evidence Pairing Sections */}
        <div className="space-y-8">
          {(isEditing ? editingData.insights : data.insights).map((insight, index) => {
            // Find evidence item related to this insight
            const relatedEvidence = evidenceItems.find(
              e => e.related_insight_index === index
            ) || evidenceItems[index]

            // Alternate layout: odd = left text/right image, even = right text/left image
            const isLeftText = index % 2 === 0

            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + index * 0.1 }}
                className={cn(
                  'flex gap-6 items-stretch',
                  !isLeftText && 'flex-row-reverse'
                )}
              >
                {/* Text Section */}
                <div className="flex-1 flex flex-col justify-center">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/20">
                      <span className="text-xs font-bold text-white">{index + 1}</span>
                    </div>
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                      {t[language].insights} #{index + 1}
                    </span>
                  </div>
                  {isEditing ? (
                    <textarea
                      value={insight}
                      onChange={(e) => {
                        const newInsights = [...editingData.insights]
                        newInsights[index] = e.target.value
                        setEditingData({ ...editingData, insights: newInsights })
                      }}
                      className="w-full text-base text-zinc-300 leading-relaxed bg-zinc-900 border-2 border-zinc-700 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500 resize-none"
                      placeholder={`洞察 ${index + 1}`}
                      rows={3}
                    />
                  ) : (
                    <p className="text-base text-zinc-300 leading-relaxed">
                      {insight}
                    </p>
                  )}
                </div>

                {/* Evidence Image Section */}
                {relatedEvidence && (
                  <div className="flex-1 min-w-0">
                    <div
                      className="relative group cursor-pointer rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 shadow-lg hover:shadow-xl transition-all"
                      onClick={() => setExpandedImage(relatedEvidence.url)}
                    >
                      <div className="aspect-video">
                        <img
                          src={relatedEvidence.url.startsWith('http') ? relatedEvidence.url : `http://localhost:8000${relatedEvidence.url}`}
                          alt={`Evidence ${index + 1}`}
                          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                          crossOrigin="anonymous"
                        />
                      </div>
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                        <ExternalLink className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      {/* Caption Overlay */}
                      {relatedEvidence.caption && (
                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
                          <p className="text-xs text-zinc-300 italic leading-relaxed">
                            "{relatedEvidence.caption}"
                          </p>
                        </div>
                      )}
                      {/* Frame number badge */}
                      <div className="absolute top-2 left-2 bg-black/70 backdrop-blur-sm px-2 py-1 rounded-md">
                        <span className="text-[10px] text-white font-medium flex items-center gap-1">
                          <ImageIcon className="w-3 h-3" />
                          #{index + 1}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>

        {/* Additional Evidence (if more than insights) */}
        {evidenceItems.length > data.insights.length && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="space-y-3"
          >
            <div className="flex items-center gap-2 text-sm font-bold text-zinc-400">
              <ImageIcon className="w-4 h-4 text-green-500" />
              {t[language].evidence}
            </div>
            <div className="grid grid-cols-2 gap-3">
              {evidenceItems.slice(data.insights.length).map((item, idx) => (
                <div
                  key={idx}
                  className="relative group cursor-pointer rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800"
                  onClick={() => setExpandedImage(item.url)}
                >
                  <div className="aspect-video">
                    <img
                      src={item.url.startsWith('http') ? item.url : `http://localhost:8000${item.url}`}
                      alt={`Evidence ${data.insights.length + idx + 1}`}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                      crossOrigin="anonymous"
                    />
                  </div>
                  {item.caption && (
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                      <p className="text-[10px] text-zinc-300 italic truncate">
                        "{item.caption}"
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="pt-6 border-t border-zinc-800 text-center"
        >
          <div className="flex items-center justify-center gap-2 mb-2">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Sparkles className="w-3 h-3 text-white" />
            </div>
            <span className="text-xs font-bold text-zinc-400">Viewpoint Prism</span>
          </div>
          <p className="text-[10px] text-zinc-600">
            {data.video_titles?.join(' / ') || `${data.source_ids?.length || 0} 个视频`}
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
              {/* Find caption for expanded image */}
              {(() => {
                const item = evidenceItems.find(e => e.url === expandedImage)
                return item?.caption ? (
                  <div className="absolute bottom-0 left-0 right-0 bg-black/80 backdrop-blur-sm p-4 rounded-b-xl">
                    <p className="text-sm text-zinc-200 italic text-center">
                      "{item.caption}"
                    </p>
                  </div>
                ) : null
              })()}
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
