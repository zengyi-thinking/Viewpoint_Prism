/**
 * Loading 组件 - 用于 Suspense fallback
 */
import { Loader2 } from 'lucide-react'

export function Loading() {
  return (
    <div className="h-screen w-screen flex items-center justify-center bg-white">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="w-12 h-12 text-gray-900 animate-spin" />
        <p className="text-gray-600">加载中...</p>
      </div>
    </div>
  )
}
