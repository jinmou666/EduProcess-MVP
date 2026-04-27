import { useState } from 'react'
import CritiqueModule from './CritiqueModule'
import ConceptMap from './ConceptMap'
import AuthenticityModule from './AuthenticityModule'

type WorkspaceView = 'home' | 'critique' | 'concept' | 'authenticity'
const CURRENT_STUDENT_ID = '20230001'

type ModuleNav = {
  module: Exclude<WorkspaceView, 'home'>
  title: string
  summary: string
  tags: string[]
}

const MODULE_NAVS: ModuleNav[] = [
  {
    module: 'critique',
    title: '内容纠错批判',
    summary: '用于定位文本问题、提交修正方案，并给出理论依据。',
    tags: ['自动评分', '错误定位', '理论依据'],
  },
  {
    module: 'authenticity',
    title: '真实性任务工作台',
    summary: '用于记录任务推进中的版本迭代、过程证据与协作分工。',
    tags: ['版本迭代', '过程留痕', '人机协作'],
  },
  {
    module: 'concept',
    title: '个人知识拓扑',
    summary: '用于补充展示概念组织方式及节点关系的结构化表达。',
    tags: ['结构表达', '节点连线', '补充展示'],
  },
]

const MODULE_META: Record<ModuleNav['module'], { accentClass: string; cardClass: string; note?: string; cta: string }> = {
  critique: {
    accentClass: 'from-indigo-600 to-sky-500',
    cardClass: 'border-slate-900/10 bg-slate-900 text-white shadow-xl shadow-slate-900/10',
    cta: '进入批判模块',
  },
  authenticity: {
    accentClass: 'from-cyan-600 to-slate-800',
    cardClass: 'border-cyan-100 bg-white shadow-md',
    cta: '进入真实性任务',
  },
  concept: {
    accentClass: 'from-slate-300 to-slate-400',
    cardClass: 'border-slate-200 bg-slate-100/80 shadow-sm',
    note: '补充展示',
    cta: '进入拓扑模块',
  },
}

const VIEW_LABELS: Record<WorkspaceView, string> = {
  home: '模块总览',
  critique: '内容纠错',
  concept: '个人知识拓扑',
  authenticity: '真实性任务工作台',
}

function App() {
  const [activeView, setActiveView] = useState<WorkspaceView>('home')

  const renderMainContent = () => {
    if (activeView === 'critique') return <CritiqueModule onBack={() => setActiveView('home')} />
    if (activeView === 'concept') return <ConceptMap onBack={() => setActiveView('home')} />
    if (activeView === 'authenticity') return <AuthenticityModule onBack={() => setActiveView('home')} />

    return (
      <section className="h-full overflow-y-auto bg-slate-50 text-slate-800">
        <div className="mx-auto flex min-h-full w-full max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="max-w-4xl space-y-4">
              <span className="inline-flex rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                Module Navigation
              </span>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">过程性学习模块导航页</h1>
              <p className="text-sm leading-7 text-slate-600 sm:text-base">
                当前版本仅承担模块进入与切换职责，保留既有 `activeView` 导航方式及各模块内部返回逻辑，不扩展总览统计与状态板能力。
              </p>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            {MODULE_NAVS.map((module) => {
              const moduleMeta = MODULE_META[module.module]

              return (
                <article
                  key={module.module}
                  className={`overflow-hidden rounded-3xl border transition-all hover:-translate-y-1 hover:shadow-lg ${moduleMeta.cardClass}`}
                >
                  <div className={`h-2 w-full bg-gradient-to-r ${moduleMeta.accentClass}`} />
                  <div className="flex h-full flex-col gap-5 p-6">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className={`text-xl font-semibold ${module.module === 'critique' ? 'text-white' : 'text-slate-900'}`}>{module.title}</h3>
                      </div>
                      {moduleMeta.note ? <span className="rounded-full bg-white/70 px-3 py-1 text-xs font-semibold text-slate-600">{moduleMeta.note}</span> : null}
                    </div>

                    <p className={`text-sm leading-7 ${module.module === 'critique' ? 'text-slate-300' : 'text-slate-600'}`}>{module.summary}</p>

                    <div className="mt-auto flex flex-wrap gap-2">
                      {module.tags.map((tag) => (
                        <span
                          key={tag}
                          className={
                            module.module === 'critique'
                              ? 'rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium text-slate-200'
                              : 'rounded-full bg-slate-200/70 px-3 py-1 text-xs font-medium text-slate-700'
                          }
                        >
                          {tag}
                        </span>
                      ))}
                    </div>

                    <button
                      type="button"
                      onClick={() => setActiveView(module.module)}
                      className={
                        module.module === 'critique'
                          ? 'inline-flex items-center justify-center rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-100'
                          : 'inline-flex items-center justify-center rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800'
                      }
                    >
                      {moduleMeta.cta}
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      </section>
    )
  }

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-100 font-sans text-slate-800">
      <header className="z-10 shrink-0 border-b border-slate-800 bg-slate-900 text-white shadow-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <button
            type="button"
            onClick={() => setActiveView('home')}
            className="flex items-center gap-2 text-left transition-opacity hover:opacity-90"
          >
            <div className="font-bold text-xl tracking-tight">
              <span className="text-indigo-400">Edu</span>Process
            </div>
            <span className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300">MVP</span>
          </button>

          <div className="hidden flex-1 items-center justify-center md:flex">
            <div className="rounded-full border border-slate-700 bg-slate-800/90 px-4 py-1.5 text-sm text-slate-300">
              当前视图：<span className="font-medium text-white">{VIEW_LABELS[activeView]}</span>
            </div>
          </div>

          <div className="rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300">
            学生：<span className="font-medium text-white">{CURRENT_STUDENT_ID}</span>
          </div>
        </div>
      </header>

      <main className="relative flex-1 overflow-hidden bg-white">
        {renderMainContent()}
      </main>
    </div>
  )
}

export default App
