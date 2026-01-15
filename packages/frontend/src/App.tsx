import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Loading } from '@/components/ui/Loading'

// 懒加载页面组件
const ProductPage = lazy(() => import('@/components/ui/ProductPage'))
const MainLayout = lazy(() => import('@/components/layout/MainLayout'))

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Routes>
          {/* 产品介绍页面 */}
          <Route path="/product" element={<ProductPage />} />
          <Route path="/intro" element={<ProductPage />} />

          {/* 主功能界面 */}
          <Route path="/app" element={<MainLayout />} />
          <Route path="/workspace" element={<MainLayout />} />

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
