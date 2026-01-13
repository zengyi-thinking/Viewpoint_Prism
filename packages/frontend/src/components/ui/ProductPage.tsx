/**
 * ProductPage - 视界棱镜产品介绍页
 *
 * 设计风格：参考 NotebookLM
 * - 单屏展示，无需滚动
 * - 简约、干净的布局
 * - 统一的中性色调（灰白为主，蓝色点缀）
 * - 清晰的信息层次
 */

import { useState } from 'react'
import { ArrowRight, Upload, Sparkles, MessageCircle, FileText, Video, Eye, Link2, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/stores/app-store'

export function ProductPage() {
  const { setUploadState, setShowProductPage } = useAppStore()

  const handleStart = () => {
    // 隐藏产品页，触发上传
    setShowProductPage(false)
    setTimeout(() => {
      setUploadState({ isUploading: true })
    }, 100)
  }

  const features = [
    {
      icon: <MessageCircle className="w-5 h-5" />,
      title: '智能对话',
      description: '基于视频内容的自然语言问答',
    },
    {
      icon: <Eye className="w-5 h-5" />,
      title: '高光星云',
      description: '可视化关键词关系图谱',
    },
    {
      icon: <FileText className="w-5 h-5" />,
      title: '智能摘要',
      description: '自动生成结构化摘要报告',
    },
    {
      icon: <Video className="w-5 h-5" />,
      title: '影院博客',
      description: '将视频转化为图文文章',
    },
    {
      icon: <Link2 className="w-5 h-5" />,
      title: '上下文桥接',
      description: '跨视频智能关联分析',
    },
    {
      icon: <Zap className="w-5 h-5" />,
      title: '冲突检测',
      description: '自动识别观点分歧',
    },
  ]

  return (
    <div className="h-screen w-screen bg-white flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-semibold text-gray-900">视界棱镜</span>
          </div>
          <button
            onClick={handleStart}
            className="px-4 py-2 bg-gray-900 text-white text-sm rounded-lg hover:bg-gray-800 transition-colors"
          >
            开始使用
          </button>
        </div>
      </header>

      {/* Main Content - Single Screen */}
      <main className="flex-1 overflow-hidden">
        <div className="h-full max-w-7xl mx-auto px-6 py-8">
          <div className="h-full grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Column - Hero */}
            <div className="flex flex-col justify-center">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-full w-fit mb-6">
                <Sparkles className="w-4 h-4 text-gray-600" />
                <span className="text-sm text-gray-600">多源视频情报分析系统</span>
              </div>

              <h1 className="text-4xl lg:text-5xl font-bold tracking-tight text-gray-900 mb-4 leading-tight">
                将视频内容<br />转化为结构化情报
              </h1>

              <p className="text-lg text-gray-500 mb-6 leading-relaxed">
                上传视频，AI 自动提取关键信息、检测观点冲突、构建知识图谱。
                让视频内容变得可搜索、可分析、可追溯。
              </p>

              <div className="flex flex-wrap gap-3 mb-8">
                <button
                  onClick={handleStart}
                  className="px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-2"
                >
                  <Upload className="w-5 h-5" />
                  上传第一个视频
                </button>
                <button className="px-6 py-3 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 transition-colors">
                  观看演示
                </button>
              </div>

              {/* AI Trio */}
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <span>记者 - 感知层</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500" />
                  <span>编辑 - 认知层</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-yellow-500" />
                  <span>导师 - 表现层</span>
                </div>
              </div>
            </div>

            {/* Right Column - Feature Cards Grid */}
            <div className="flex items-center">
              <div className="grid grid-cols-2 gap-3 w-full">
                {features.map((feature, index) => (
                  <div
                    key={index}
                    className="p-4 bg-gray-50 border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-md transition-all cursor-pointer"
                  >
                    <div className="w-10 h-10 rounded-lg bg-white border border-gray-200 flex items-center justify-center mb-3 text-gray-700">
                      {feature.icon}
                    </div>
                    <div className="font-medium text-gray-900 mb-1">{feature.title}</div>
                    <div className="text-sm text-gray-500 leading-snug">{feature.description}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="flex-shrink-0 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between text-sm text-gray-500">
          <div>© 2024 视界棱镜</div>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-gray-900 transition-colors">隐私政策</a>
            <a href="#" className="hover:text-gray-900 transition-colors">服务条款</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
