import { useState, useEffect, useCallback } from 'react'
import CritiqueModule from './CritiqueModule'
import ConceptMap from './ConceptMap'
import AuthenticityModule from './AuthenticityModule'

type WorkspaceView = 'home' | 'critique' | 'concept' | 'authenticity'
const CURRENT_STUDENT_ID = '20230001'
const API_BASE = 'http://127.0.0.1:8000'

const VIEW_LABELS: Record<WorkspaceView, string> = {
  home: '模块总览',
  critique: '内容纠错',
  concept: '个人知识拓扑',
  authenticity: '真实性任务工作台',
}

const DIMENSION_LABELS: Record<string, string> = {
  coverage: '覆盖度',
  correction_accuracy: '准确度',
  reasoning_quality: '推理',
  alignment_precision: '精度',
  noise_control: '控噪',
  iteration_evidence: '迭代证据',
  process_transparency: '过程透明',
  critical_engagement: '批判参与',
  reflection_quality: '反思质量',
  ai_collab_literacy: 'AI协作',
}

type DashboardDimScore = {
  key: string
  score: number
  max_score: number
  reason: string
}

type DashboardModuleScore = {
  status: string
  total_score: number | null
  dimension_scores: DashboardDimScore[]
  improvement_advice: string[]
  evaluated_at: string | null
}

type DashboardCritiqueTaskStatus = {
  task_id: number
  task_title: string
  status: string
  total_score: number | null
  evaluated_at: string | null
}

type DashboardAuthenticityTaskStatus = {
  task_id: number
  task_title: string
  status: string
  iteration_count: number
  iteration_hint: string
  total_score: number | null
  evaluated_at: string | null
}

type DashboardData = {
  student_id: string
  student_name: string
  composite_score: number | null
  critique_weight: number
  authenticity_weight: number
  critique: DashboardModuleScore
  critique_tasks: DashboardCritiqueTaskStatus[]
  authenticity: DashboardModuleScore
  authenticity_tasks: DashboardAuthenticityTaskStatus[]
  concept_status: string
}

function StatusBadge({ status, iterationHint }: { status: string; iterationHint?: string }) {
  if (status === 'evaluated')
    return <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>已评估</span>
  if (status === 'submitted') {
    if (iterationHint !== undefined) {
      const meetsMin = !iterationHint.includes('建议') && !iterationHint.includes('当前0')
      return meetsMin
        ? <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>已满足迭代要求</span>
        : <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" /></svg>未满足迭代要求</span>
    }
    return <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" /></svg>待评估</span>
  }
  return <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-400"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2a1 1 0 001 1h1a1 1 0 100-2h-.5V7a1 1 0 00-1-1z" clipRule="evenodd" /></svg>未开始</span>
}

function ConceptBadge({ status }: { status: string }) {
  if (status === 'submitted')
    return <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>已保存</span>
  return <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-400"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2a1 1 0 001 1h1a1 1 0 100-2h-.5V7a1 1 0 00-1-1z" clipRule="evenodd" /></svg>待构筑</span>
}

function ScoreBar({ score, maxScore }: { score: number; maxScore: number }) {
  const pct = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-rose-500'
  return (
    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
      <div className={`h-2 rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function App() {
  const [activeView, setActiveView] = useState<WorkspaceView>('home')
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)

  const fetchDashboard = useCallback(() => {
    fetch(`${API_BASE}/api/dashboard/${CURRENT_STUDENT_ID}`)
      .then(res => res.ok ? res.json() : null)
      .then(data => setDashboard(data))
      .catch(() => setDashboard(null))
  }, [])

  useEffect(() => {
    if (activeView === 'home') fetchDashboard()
  }, [activeView, fetchDashboard])

  const fmtTime = (iso: string | null | undefined) => {
    if (!iso) return ''
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }

  const renderChecklist = () => {
    if (!dashboard) return null
    return (
      <div className="border border-slate-200 shadow-sm rounded-xl bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">任务完成情况</h2>

        {dashboard.critique_tasks.length > 0 && (
          <div className="mb-4">
            <div className="text-xs font-medium uppercase tracking-wider text-blue-600 mb-2">内容纠错批判</div>
            <div className="space-y-2">
              {dashboard.critique_tasks.map(t => (
                <div key={t.task_id} className="flex items-center gap-3 text-sm text-slate-900 py-1.5 px-3 rounded-lg hover:bg-slate-50">
                  <StatusBadge status={t.status} />
                  <span className="font-medium flex-1">{t.task_title}</span>
                  {t.status === 'evaluated' && t.total_score !== null && (
                    <span className="text-xs text-slate-500">{t.total_score}/100 · {fmtTime(t.evaluated_at)}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {dashboard.authenticity_tasks.length > 0 && (
          <div className="mb-4">
            <div className="text-xs font-medium uppercase tracking-wider text-blue-600 mb-2">真实性任务工作台</div>
            <div className="space-y-2">
              {dashboard.authenticity_tasks.map(t => (
                <div key={t.task_id} className="flex items-center gap-3 text-sm text-slate-900 py-1.5 px-3 rounded-lg hover:bg-slate-50">
                  <StatusBadge status={t.status} iterationHint={t.iteration_hint} />
                  <span className="font-medium flex-1">{t.task_title}</span>
                  {t.status === 'evaluated' && t.total_score !== null && (
                    <span className="text-xs text-slate-500">{t.total_score}/100 · {fmtTime(t.evaluated_at)}</span>
                  )}
                  {t.status === 'submitted' && t.iteration_hint && (
                    <span className="text-xs text-amber-600">{t.iteration_hint}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div>
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">个人知识拓扑</div>
          <div className="flex items-center gap-3 text-sm text-slate-900 py-1.5 px-3 rounded-lg">
            <ConceptBadge status={dashboard.concept_status} />
            <span className="font-medium">知识拓扑图</span>
          </div>
        </div>
      </div>
    )
  }

  const renderModuleScore = (mod: DashboardModuleScore) => {
    if (mod.status === 'not_started')
      return <div className="text-sm text-slate-400">尚未开始</div>
    if (mod.status === 'submitted')
      return <div className="text-sm text-amber-600">已提交，待评估</div>

    const score = mod.total_score ?? 0
    return (
      <div className="space-y-3">
        <div className="flex items-baseline gap-1">
          <span className="text-4xl font-bold text-slate-900">{score}</span>
          <span className="text-sm text-slate-500 font-medium">/ 100</span>
        </div>
        <ScoreBar score={score} maxScore={100} />
        {mod.dimension_scores.length > 0 && (
          <div className="grid grid-cols-5 gap-2">
            {mod.dimension_scores.map(d => {
              const pct = d.max_score > 0 ? Math.round((d.score / d.max_score) * 100) : 0
              return (
                <div key={d.key} className="text-center">
                  <div className={`text-lg font-bold ${pct >= 80 ? 'text-emerald-500' : pct >= 60 ? 'text-amber-500' : 'text-rose-500'}`}>{d.score}/{d.max_score}</div>
                  <div className="text-xs text-slate-500">{DIMENSION_LABELS[d.key] || d.key}</div>
                </div>
              )
            })}
          </div>
        )}
        {mod.evaluated_at && (
          <div className="text-xs text-slate-400">评估于 {fmtTime(mod.evaluated_at)}</div>
        )}
      </div>
    )
  }

  const renderMainContent = () => {
    if (activeView === 'critique') return <CritiqueModule onBack={() => setActiveView('home')} />
    if (activeView === 'concept') return <ConceptMap onBack={() => setActiveView('home')} />
    if (activeView === 'authenticity') return <AuthenticityModule onBack={() => setActiveView('home')} />

    return (
      <div className="h-full overflow-y-auto bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-6">

          {renderChecklist()}

          <div className="grid gap-6 lg:grid-cols-3">
            {/* 批判卡片 */}
            <article className="border border-slate-200 shadow-sm rounded-xl bg-white overflow-hidden">
              <div className="h-1.5 bg-blue-600" />
              <div className="p-6 flex flex-col gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">内容纠错批判</h2>
                  <p className="text-sm leading-relaxed text-slate-500 mt-1">定位文本问题、提交修正方案，给出理论依据</p>
                </div>
                {dashboard ? renderModuleScore(dashboard.critique) : (
                  <div className="text-sm text-slate-400 animate-pulse">加载中...</div>
                )}
                <div className="flex flex-wrap gap-2">
                  {['自动评分', '错误定位', '理论依据'].map(t => (
                    <span key={t} className="text-xs font-medium uppercase tracking-wider text-slate-500 bg-slate-100 rounded-full px-3 py-1">{t}</span>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setActiveView('critique')}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  进入批判模块
                </button>
              </div>
            </article>

            {/* 真实性卡片 */}
            <article className="border border-slate-200 shadow-sm rounded-xl bg-white overflow-hidden">
              <div className="h-1.5 bg-blue-600" />
              <div className="p-6 flex flex-col gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">真实性任务工作台</h2>
                  <p className="text-sm leading-relaxed text-slate-500 mt-1">版本迭代、过程留痕、人机协作分工</p>
                </div>
                {dashboard ? (
                  <>
                    {renderModuleScore(dashboard.authenticity)}
                    {dashboard.authenticity.status === 'submitted' && dashboard.authenticity_tasks.length > 0 && dashboard.authenticity_tasks[0].iteration_hint && (
                      <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                        {dashboard.authenticity_tasks[0].iteration_hint}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-sm text-slate-400 animate-pulse">加载中...</div>
                )}
                <div className="flex flex-wrap gap-2">
                  {['版本迭代', '过程留痕', '人机协作'].map(t => (
                    <span key={t} className="text-xs font-medium uppercase tracking-wider text-slate-500 bg-slate-100 rounded-full px-3 py-1">{t}</span>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setActiveView('authenticity')}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  进入真实性任务
                </button>
              </div>
            </article>

            {/* 拓扑卡片 */}
            <article className="border border-slate-200 shadow-sm rounded-xl bg-white overflow-hidden">
              <div className="h-1.5 bg-slate-300" />
              <div className="p-6 flex flex-col gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">个人知识拓扑</h2>
                  <p className="text-sm leading-relaxed text-slate-500 mt-1">概念组织方式及节点关系的结构化表达</p>
                </div>
                <div className="py-4">
                  {dashboard
                    ? <ConceptBadge status={dashboard.concept_status} />
                    : <span className="text-sm text-slate-400 animate-pulse">加载中...</span>
                  }
                </div>
                <div className="flex flex-wrap gap-2">
                  {['结构表达', '节点连线', '补充展示'].map(t => (
                    <span key={t} className="text-xs font-medium uppercase tracking-wider text-slate-500 bg-slate-100 rounded-full px-3 py-1">{t}</span>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setActiveView('concept')}
                  className="inline-flex items-center justify-center px-4 py-2 border border-slate-300 shadow-sm text-sm font-medium rounded-md text-slate-700 bg-white hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  进入拓扑模块
                </button>
              </div>
            </article>
          </div>

          {/* 综合评分 */}
          {dashboard && dashboard.composite_score !== null && (
            <div className="border border-slate-200 shadow-sm rounded-xl bg-white p-6 text-center">
              <div className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">
                综合评分 &mdash; 批判 &times; {Math.round(dashboard.critique_weight * 100)}% + 真实性 &times; {Math.round(dashboard.authenticity_weight * 100)}%
              </div>
              <div className="text-4xl font-bold text-slate-900">
                {dashboard.composite_score}<span className="text-lg font-semibold text-slate-400"> / 100</span>
              </div>
              {dashboard.critique.total_score !== null && dashboard.authenticity.total_score !== null && (
                <div className="text-xs text-slate-400 mt-1">
                  批判 {dashboard.critique.total_score} &times; {dashboard.critique_weight} + 真实性 {dashboard.authenticity.total_score} &times; {dashboard.authenticity_weight}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-50 font-sans text-slate-900">
      <header className="z-10 shrink-0 border-b border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto flex h-14 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <button
            type="button"
            onClick={() => setActiveView('home')}
            className="flex items-center gap-2 group"
          >
            <span className="text-xl font-bold tracking-tight text-slate-900">
              <span className="text-blue-600">Edu</span>Process
            </span>
          </button>

          <div className="hidden flex-1 items-center justify-center md:flex">
            <div className="text-sm text-slate-500">
              当前视图：<span className="font-medium text-slate-900">{VIEW_LABELS[activeView]}</span>
            </div>
          </div>

          <div className="text-sm text-slate-500">
            学生：<span className="font-medium text-slate-900">{CURRENT_STUDENT_ID}</span>
          </div>
        </div>
      </header>

      <main className="relative flex-1 overflow-hidden">
        {renderMainContent()}
      </main>
    </div>
  )
}

export default App