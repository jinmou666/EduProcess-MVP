import { useState } from 'react'
import CritiqueModule from './CritiqueModule'
import ConceptMap from './ConceptMap'
import AuthenticityModule from './AuthenticityModule' // 引入新模块

function App() {
  // 新增了 'authenticity' 状态
  const [activeTab, setActiveTab] = useState<'critique' | 'concept' | 'authenticity'>('authenticity')

  return (
    <div className="w-screen h-screen flex flex-col overflow-hidden font-sans text-gray-800">
      {/* 顶部导航 */}
      <header className="bg-gray-900 text-white shadow-md z-10 shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="font-bold text-xl tracking-tight flex items-center gap-2">
            <span className="text-indigo-400">Edu</span>Process <span className="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-300">MVP</span>
          </div>
          <nav className="flex space-x-1 border p-1 rounded-lg border-gray-700 bg-gray-800">
            <button
              onClick={() => setActiveTab('critique')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'critique' ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              内容纠错
            </button>
            <button
              onClick={() => setActiveTab('concept')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'concept' ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              个人知识拓扑
            </button>
            <button
              onClick={() => setActiveTab('authenticity')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'authenticity' ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              真实性任务工作台
            </button>
          </nav>
        </div>
      </header>

      {/* 主体内容区域 */}
      <main className="flex-1 overflow-hidden relative bg-white">
        {activeTab === 'critique' && <CritiqueModule />}
        {activeTab === 'concept' && <ConceptMap />}
        {activeTab === 'authenticity' && <AuthenticityModule />}
      </main>
    </div>
  )
}

export default App