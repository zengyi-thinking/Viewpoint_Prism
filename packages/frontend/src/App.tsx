import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Loading } from '@/components/ui/Loading'
import { ProtectedRoute } from '@/components/common'

// 懒加载页面组件
const ProductPage = lazy(() => import('@/components/ui/ProductPage'))
const MainLayout = lazy(() => import('@/components/layout/MainLayout'))
const LoginPage = lazy(() => import('@/components/auth/LoginPage'))
const RegisterPage = lazy(() => import('@/components/auth/RegisterPage'))

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Routes>
          {/* 认证页面 */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* 产品介绍页面 */}
          <Route path="/product" element={<ProductPage />} />
          <Route path="/intro" element={<ProductPage />} />

          {/* 主功能界面 - 需要认证 */}
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspace"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          />

          {/* 根路径重定向到产品介绍 */}
          <Route path="/" element={<Navigate to="/product" replace />} />

          {/* 404 重定向到产品介绍 */}
          <Route path="*" element={<Navigate to="/product" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default App
