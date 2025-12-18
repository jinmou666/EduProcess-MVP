import { useState } from 'react';
import ConceptMap from './ConceptMap';
import CritiqueModule from './CritiqueModule';

function App() {
  const [activeTab, setActiveTab] = useState<'critique' | 'topology'>('critique');

  return (
    <div className="h-screen flex flex-col bg-gray-100 font-sans text-gray-900 overflow-hidden">

      {/* 顶部导航栏 - 修复：移除 max-w-7xl，改为 w-full px-8 */}
      <nav className="bg-gray-900 text-white shadow-lg z-50 flex-shrink-0 w-full">
        <div className="w-full px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center font-bold">E</div>
              <span className="font-bold text-xl tracking-tight">EduProcess</span>
            </div>

            <div className="flex space-x-4">
              <button
                onClick={() => setActiveTab('critique')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'critique'
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`}
              >
                1. AI 内容批判
              </button>

              <button
                onClick={() => setActiveTab('topology')}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'topology'
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`}
              >
                2. 拓扑构筑
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 主内容区域 - 状态保持 */}
      <div className="flex-1 relative overflow-hidden">

        {/* 模块1: 批判 */}
        <div
          className="absolute inset-0 w-full h-full bg-white"
          style={{
            display: activeTab === 'critique' ? 'block' : 'none',
            zIndex: activeTab === 'critique' ? 10 : 0
          }}
        >
          <CritiqueModule />
        </div>

        {/* 模块2: 拓扑 */}
        <div
          className="absolute inset-0 w-full h-full bg-gray-50"
          style={{
            display: activeTab === 'topology' ? 'block' : 'none',
            zIndex: activeTab === 'topology' ? 10 : 0
          }}
        >
          <ConceptMap />
        </div>

      </div>

    </div>
  );
}

export default App;