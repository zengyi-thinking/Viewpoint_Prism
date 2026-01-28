/**
 * 注册页面组件 - Floating Islands 设计风格
 */

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { Layers } from 'lucide-react'

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register, isLoading, error } = useAuthStore()

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // 验证密码
    if (password !== confirmPassword) {
      alert('两次输入的密码不一致')
      return
    }

    if (password.length < 8) {
      alert('密码长度至少8位')
      return
    }

    try {
      await register({ username, email, password })
      // 注册成功后跳转到登录页
      navigate('/login', {
        state: { message: '注册成功，请登录' }
      })
    } catch (err) {
      // 错误已在 store 中处理
      console.error('注册失败:', err)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[--bg-app]" style={{
      backgroundImage: 'radial-gradient(circle at center, #111 0%, #050507 100%)'
    }}>
      <div className="max-w-md w-full mx-4 fade-in">
        {/* Logo 和标题 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-2xl shadow-lg mb-4">
            <Layers className="w-8 h-8 text-black" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">视界棱镜</h1>
          <p className="text-[--text-sub] text-sm">Viewpoint Prism - 多源视频情报分析系统</p>
        </div>

        {/* 注册表单 */}
        <div className="floating-panel p-8">
          <h2 className="text-xl font-semibold text-white mb-6">注册账户</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 用户名 */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-[--text-sub] mb-2">
                用户名
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
                maxLength={50}
                className="input-industrial w-full px-4 py-3"
                placeholder="3-50个字符"
              />
            </div>

            {/* 邮箱 */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[--text-sub] mb-2">
                邮箱
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input-industrial w-full px-4 py-3"
                placeholder="your@email.com"
              />
            </div>

            {/* 密码 */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-[--text-sub] mb-2">
                密码
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="input-industrial w-full px-4 py-3"
                placeholder="至少8位"
              />
            </div>

            {/* 确认密码 */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-[--text-sub] mb-2">
                确认密码
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="input-industrial w-full px-4 py-3"
                placeholder="再次输入密码"
              />
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="p-3 bg-red-900/30 border border-red-500/30 rounded-lg">
                <p className="text-sm text-red-300">{error}</p>
              </div>
            )}

            {/* 注册按钮 */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-white hover:bg-gray-100 text-black font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '注册中...' : '注册'}
            </button>
          </form>

          {/* 登录链接 */}
          <div className="mt-6 text-center">
            <p className="text-[--text-sub]">
              已有账号？{' '}
              <Link to="/login" className="text-white hover:text-gray-300 font-medium">
                立即登录
              </Link>
            </p>
          </div>
        </div>

        {/* 页脚 */}
        <div className="mt-8 text-center text-[--text-sub] text-xs">
          <p>© 2026 Viewpoint Prism. All rights reserved.</p>
        </div>
      </div>
    </div>
  )
}
