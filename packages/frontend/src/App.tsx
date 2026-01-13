import { MainLayout } from '@/components/layout/MainLayout'
import { ProductPage } from '@/components/ui/ProductPage'
import { useAppStore } from '@/stores/app-store'

function App() {
  const { sources, showProductPage } = useAppStore()

  // 根据 URL 参数决定显示哪个页面
  const urlParams = new URLSearchParams(window.location.search)
  const page = urlParams.get('page')

  // 产品介绍页面（通过 URL 参数或状态控制）
  if (page === 'product' || (showProductPage && !sources.length)) {
    return <ProductPage />
  }

  return <MainLayout />
}

export default App
