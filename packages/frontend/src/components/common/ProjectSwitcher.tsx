/**
 * 工程切换器组件 - Floating Islands 设计风格
 */

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { Layers, Settings } from 'lucide-react'

export default function ProjectSwitcher() {
  const { currentProject, projects, switchProject, loadProjects } = useAuthStore()
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    // 加载工程列表
    if (projects.length === 0) {
      loadProjects()
    }
  }, [])

  // 过滤工程列表
  const filteredProjects = projects.filter((project) =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="relative">
      {/* 当前工程按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="topbar-btn px-3 py-2 flex items-center gap-2 text-[--text-sub] hover:text-white"
      >
        <Layers className="w-4 h-4" />
        <span className="font-medium max-w-[150px] truncate text-sm">
          {currentProject?.name || '未选择工程'}
        </span>
        <svg
          className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* 下拉面板 */}
      {isOpen && (
        <>
          {/* 遮罩层 */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* 面板 */}
          <div className="absolute right-0 mt-2 w-80 floating-panel z-20">
            {/* 搜索框 */}
            <div className="p-3 border-b border-[--border]">
              <input
                type="text"
                placeholder="搜索工程..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-industrial w-full px-3 py-2 text-sm"
              />
            </div>

            {/* 工程列表 */}
            <div className="max-h-64 overflow-y-auto scroller">
              {filteredProjects.length === 0 ? (
                <div className="p-4 text-center text-[--text-sub]">
                  {searchQuery ? '没有找到匹配的工程' : '暂无工程'}
                </div>
              ) : (
                filteredProjects.map((project) => (
                  <button
                    key={project.id}
                    onClick={async () => {
                      await switchProject(project.id)
                      setIsOpen(false)
                    }}
                    className={`w-full px-4 py-3 text-left hover:bg-[--bg-element] transition-colors ${
                      currentProject?.id === project.id ? 'bg-[--bg-element]' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-white truncate text-sm">{project.name}</p>
                        {project.description && (
                          <p className="text-xs text-[--text-sub] truncate mt-0.5">{project.description}</p>
                        )}
                      </div>
                      {currentProject?.id === project.id && (
                        <svg className="w-4 h-4 text-emerald-400 ml-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>

            {/* 创建新工程和管理工程按钮 */}
            <div className="p-3 border-t border-[--border] flex gap-2">
              <button
                onClick={() => {
                  setIsOpen(false)
                  // 触发创建工程的对话框
                  window.dispatchEvent(new CustomEvent('project:create'))
                }}
                className="flex-1 py-2 px-3 bg-white hover:bg-gray-100 text-black text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>新建</span>
              </button>
              <button
                onClick={() => {
                  setIsOpen(false)
                  // 触发管理工程的对话框
                  window.dispatchEvent(new CustomEvent('project:manage'))
                }}
                className="py-2 px-3 topbar-btn text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                title="管理工程"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
