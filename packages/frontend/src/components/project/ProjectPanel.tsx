/**
 * 工程管理面板组件 - Floating Islands 设计风格
 */

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import type { Project } from '@/types/modules/auth'
import { Layers, X, Edit, Trash2, ChevronRight } from 'lucide-react'

interface ProjectPanelProps {
  onClose?: () => void
  initialCreateMode?: boolean
}

export function ProjectPanel({ onClose, initialCreateMode = false }: ProjectPanelProps) {
  const {
    projects,
    currentProject,
    loadProjects,
    createProject,
    updateProject,
    deleteProject,
    switchProject,
    isLoading,
    error,
    setError,
  } = useAuthStore()

  const [showCreateForm, setShowCreateForm] = useState(initialCreateMode)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [formData, setFormData] = useState({ name: '', description: '' })

  useEffect(() => {
    loadProjects()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createProject(formData.name, formData.description)
      setShowCreateForm(false)
      setFormData({ name: '', description: '' })
    } catch (err) {
      // 错误已在 store 中处理
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingProject) return

    try {
      await updateProject(editingProject.id, formData.name, formData.description)
      setEditingProject(null)
      setFormData({ name: '', description: '' })
    } catch (err) {
      // 错误已在 store 中处理
    }
  }

  const handleDelete = async (projectId: string) => {
    if (!confirm('确定要删除这个工程吗？此操作不可恢复。')) {
      return
    }

    try {
      await deleteProject(projectId)
    } catch (err) {
      // 错误已在 store 中处理
    }
  }

  const openEditForm = (project: Project) => {
    setEditingProject(project)
    setFormData({ name: project.name, description: project.description || '' })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="floating-panel w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden fade-in">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[--border]">
          <div className="flex items-center gap-3">
            <Layers className="w-5 h-5 text-white" />
            <h2 className="text-xl font-semibold text-white">工程管理</h2>
          </div>
          <button
            onClick={onClose}
            className="text-[--text-sub] hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容区 */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-73px)] scroller">
          {/* 错误提示 */}
          {error && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-500/30 rounded-lg flex items-center justify-between">
              <p className="text-sm text-red-300">{error}</p>
              <button onClick={() => setError(null)} className="text-red-300 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* 创建/编辑表单 */}
          {(showCreateForm || editingProject) && (
            <div className="mb-6 p-4 bg-[--bg-element] border border-[--border] rounded-lg">
              <h3 className="text-lg font-medium text-white mb-4">
                {editingProject ? '编辑工程' : '创建新工程'}
              </h3>
              <form onSubmit={editingProject ? handleUpdate : handleCreate} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[--text-sub] mb-2">
                    工程名称
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    maxLength={100}
                    className="input-industrial w-full px-4 py-2.5"
                    placeholder="输入工程名称"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[--text-sub] mb-2">
                    描述（可选）
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className="input-industrial w-full px-4 py-2.5 resize-none"
                    placeholder="输入工程描述"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="flex-1 py-2.5 px-4 bg-white hover:bg-gray-100 text-black font-medium rounded-lg transition-colors disabled:opacity-50"
                  >
                    {isLoading ? '保存中...' : editingProject ? '保存' : '创建'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateForm(false)
                      setEditingProject(null)
                      setFormData({ name: '', description: '' })
                    }}
                    className="py-2.5 px-4 topbar-btn font-medium rounded-lg"
                  >
                    取消
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* 创建按钮 */}
          {!showCreateForm && !editingProject && (
            <button
              onClick={() => setShowCreateForm(true)}
              className="w-full mb-4 py-3 px-4 bg-white hover:bg-gray-100 text-black font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <Layers className="w-4 h-4" />
              创建新工程
            </button>
          )}

          {/* 工程列表 */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-[--text-sub] uppercase tracking-wide">我的工程</h3>
            {projects.length === 0 ? (
              <div className="text-center py-12 text-[--text-sub]">
                <Layers className="w-12 h-12 mx-auto mb-3 text-[--border]" />
                <p>暂无工程，创建一个开始使用吧</p>
              </div>
            ) : (
              projects.map((project) => (
                <div
                  key={project.id}
                  className={`p-4 rounded-lg border transition-all ${
                    currentProject?.id === project.id
                      ? 'bg-[--bg-element] border-emerald-500/50'
                      : 'bg-transparent border-[--border] hover:border-[--border-hover]'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Layers className="w-4 h-4 text-[--text-sub] flex-shrink-0" />
                        <h4 className="font-medium text-white truncate">{project.name}</h4>
                        {currentProject?.id === project.id && (
                          <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded">当前</span>
                        )}
                      </div>
                      {project.description && (
                        <p className="text-sm text-[--text-sub] line-clamp-2 mb-2">{project.description}</p>
                      )}
                      <p className="text-xs text-[--text-sub]">
                        {project.member_count} 成员 · {new Date(project.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex items-center gap-1 ml-4">
                      {currentProject?.id !== project.id && (
                        <button
                          onClick={() => switchProject(project.id)}
                          className="p-2 text-[--text-sub] hover:text-white hover:bg-[--bg-element] rounded-lg transition-colors"
                          title="切换到此工程"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => openEditForm(project)}
                        className="p-2 text-[--text-sub] hover:text-white hover:bg-[--bg-element] rounded-lg transition-colors"
                        title="编辑"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(project.id)}
                        className="p-2 text-[--text-sub] hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-colors"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
