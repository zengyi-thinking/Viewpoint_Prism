import { MainLayout } from '@/components/layout/MainLayout'
import { ToastContainer } from '@/components/ui/feedback'
import { AnimatedGraphBackground } from '@/components/ui/knowledge-graph'

function App() {
  return (
    <>
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10">
        <AnimatedGraphBackground />
      </div>

      {/* Main Layout */}
      <MainLayout />

      {/* Toast Notifications */}
      <ToastContainer />
    </>
  )
}

export default App
