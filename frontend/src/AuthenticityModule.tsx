import { useEffect, useMemo, useRef, useState } from 'react';

type StageData = {
  stageName: string;
  humanPercent: number;
  aiPercent: number;
  tools: string[];
};

type Iteration = {
  id: string;
  version: number;
  timestamp: string;
  title: string;
  deltaNotes: string;
  deliverableUrl: string;
  stages: StageData[];
  toolsUsed: string[];
};

type AuthenticityDimensionScore = {
  key: string;
  score: number;
  max_score: number;
  reason: string;
};

type AuthenticityEvaluationReport = {
  rubric_version: string;
  total_score: number;
  overall_feedback: string;
  dimension_scores: AuthenticityDimensionScore[];
  improvement_advice: string[];
};

const MOCK_ITERATIONS: Iteration[] = [
  {
    id: 'it_3',
    version: 3,
    timestamp: '2024-11-15 14:30',
    title: '核心逻辑重构与AI润色',
    deltaNotes: '推翻了AI在V2版本中生成的过于理想化的市场预估模型。我手动引入了最新的行业研报数据限制其边界，并引导AI重新生成了风险评估段落。Claude 3.5在逻辑分析方面表现不错，而ChatGPT在文字润色上更为流畅。整体比V2提升了显著的人机协作质量。',
    deliverableUrl: 'https://github.com/stu/project/commit/v3',
    toolsUsed: ['Google Search', 'Perplexity', 'Notion AI', 'Claude 3.5', 'ChatGPT'],
    stages: [
      { stageName: '① 资料检索与破冰', humanPercent: 80, aiPercent: 20, tools: ['Google Search', 'Perplexity'] },
      { stageName: '② 框架与逻辑构建', humanPercent: 90, aiPercent: 10, tools: ['Notion AI'] },
      { stageName: '③ 内容生成', humanPercent: 40, aiPercent: 60, tools: ['Claude 3.5', 'ChatGPT'] },
      { stageName: '④ 审阅、纠错与润色', humanPercent: 70, aiPercent: 30, tools: ['ChatGPT'] },
    ]
  },
  {
    id: 'it_2',
    version: 2,
    timestamp: '2024-11-12 09:15',
    title: '初稿生成与大面积扩写',
    deltaNotes: '基于V1的框架，完全交由AI进行正文填充。使用Perplexity检索了大量行业研报和数据，然后利用ChatGPT生成初稿。发现AI在细节论证上存在明显的幻觉（凭空捏造了几个数据），但我暂时保留以观后效。',
    deliverableUrl: 'https://docs.google.com/document/d/v2',
    toolsUsed: ['Perplexity', 'ChatGPT'],
    stages: [
      { stageName: '① 资料检索与破冰', humanPercent: 40, aiPercent: 60, tools: ['Perplexity'] },
      { stageName: '② 框架与逻辑构建', humanPercent: 50, aiPercent: 50, tools: ['ChatGPT'] },
      { stageName: '③ 内容生成', humanPercent: 10, aiPercent: 90, tools: ['ChatGPT'] },
      { stageName: '④ 审阅、纠错与润色', humanPercent: 10, aiPercent: 90, tools: ['ChatGPT'] },
    ]
  },
  {
    id: 'it_1',
    version: 1,
    timestamp: '2024-11-10 16:00',
    title: '需求拆解与大纲初建',
    deltaNotes: '刚接手任务，完全靠自己理解题目要求，仅使用搜索引擎查阅了专有名词和事故统计数据，制定了初步的三级标题大纲。',
    deliverableUrl: 'https://docs.google.com/document/d/v1_autonomous_driving_risk',
    toolsUsed: ['Google Search'],
    stages: [
      { stageName: '① 资料检索与破冰', humanPercent: 95, aiPercent: 5, tools: ['Google Search'] },
      { stageName: '② 框架与逻辑构建', humanPercent: 100, aiPercent: 0, tools: [] },
      { stageName: '③ 内容生成', humanPercent: 100, aiPercent: 0, tools: [] },
      { stageName: '④ 审阅、纠错与润色', humanPercent: 100, aiPercent: 0, tools: [] },
    ]
  }
];

const AVAILABLE_TOOLS = ['ChatGPT', 'Claude 3.5', 'Midjourney', 'GitHub Copilot', 'Perplexity', 'Notion AI'];

const STUDENT_ID = "20230001";
const TASK_ID = 1;
const API_BASE = "http://127.0.0.1:8000";

type AuthenticityModuleProps = {
  onBack?: () => void;
};

type CollaborationStage = {
  stageName: string;
  humanPercent: number;
  aiPercent: number;
  tools: string[];
};

const DEFAULT_COLLABORATION_MATRIX: CollaborationStage[] = [
  { stageName: '① 资料检索与破冰', humanPercent: 50, aiPercent: 50, tools: [] },
  { stageName: '② 框架与逻辑构建', humanPercent: 50, aiPercent: 50, tools: [] },
  { stageName: '③ 内容生成与开发', humanPercent: 50, aiPercent: 50, tools: [] },
  { stageName: '④ 审阅、纠错与润色', humanPercent: 50, aiPercent: 50, tools: [] },
];

const DIMENSION_LABELS: Record<string, string> = {
  iteration_evidence: '迭代证据',
  process_transparency: '过程透明度',
  critical_engagement: '批判性参与',
  reflection_quality: '反思质量',
  ai_collab_literacy: 'AI协作素养',
};

export default function AuthenticityModule({ onBack }: AuthenticityModuleProps) {
  const [deliverableUrl, setDeliverableUrl] = useState<string>('');
  const [collaborationMatrix, setCollaborationMatrix] = useState<CollaborationStage[]>(DEFAULT_COLLABORATION_MATRIX);
  const [feedbackMessage, setFeedbackMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [reflectionText, setReflectionText] = useState<string>('');
  const [iterations, setIterations] = useState<Iteration[]>(MOCK_ITERATIONS);
  const [hoveredIterationId, setHoveredIterationId] = useState<string | null>(null);
  const [isContextModalOpen, setIsContextModalOpen] = useState(false);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [submitStep, setSubmitStep] = useState(1);
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set([MOCK_ITERATIONS[0].id]));
  const [authEvaluationReport, setAuthEvaluationReport] = useState<AuthenticityEvaluationReport | null>(null);
  const [isAuthEvaluating, setIsAuthEvaluating] = useState<boolean>(false);
  const evalCardRef = useRef<HTMLDivElement>(null);

  const fetchIterations = async () => {
    try {
      const response = await fetch(`${API_BASE}/authenticity/${TASK_ID}/${STUDENT_ID}`);
      if (response.status === 404) return;
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data && data.length > 0) {
        const mappedIterations: Iteration[] = data.map((item: any) => {
          const dateObj = new Date(item.created_at);
          const safeTimestamp = isNaN(dateObj.getTime())
            ? "1970-01-01 00:00"
            : `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}-${String(dateObj.getDate()).padStart(2, '0')} ${String(dateObj.getHours()).padStart(2, '0')}:${String(dateObj.getMinutes()).padStart(2, '0')}`;
          return {
            id: `it_${item.id}`,
            version: item.version_number,
            timestamp: safeTimestamp,
            title: `真实性迭代版本 V${item.version_number}`,
            deltaNotes: item.reflection_log,
            deliverableUrl: item.deliverable_payload,
            toolsUsed: Array.isArray(item.tools_used) ? item.tools_used : [],
            stages: item.collaboration_matrix.map((stage: any) => ({
              stageName: stage.stageName || "未知阶段",
              humanPercent: stage.humanPercent || 0,
              aiPercent: stage.aiPercent || 0,
              tools: Array.isArray(stage.tools) ? stage.tools : []
            }))
          };
        });
        setIterations(mappedIterations);
      }
    } catch (error) {
      console.error("Failed to load iterations:", error);
    }
  };

  useEffect(() => { fetchIterations(); }, []);

  const displayIteration = useMemo(() => {
    if (hoveredIterationId) return iterations.find(it => it.id === hoveredIterationId) || iterations[0];
    return iterations[0];
  }, [hoveredIterationId, iterations]);

  const toggleCard = (id: string) => {
    const next = new Set(expandedCards);
    if (next.has(id)) next.delete(id); else next.add(id);
    setExpandedCards(next);
  };

  const submitIteration = async () => {
    if (!deliverableUrl.trim()) { alert("请填写交付物载体链接"); return; }
    if (reflectionText.trim().length < 50) { alert("反思日志至少需要50字"); return; }
    try {
      const response = await fetch(`${API_BASE}/authenticity/${TASK_ID}/${STUDENT_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deliverable_payload: deliverableUrl,
          collaboration_matrix: collaborationMatrix,
          tools_used: [...new Set(collaborationMatrix.flatMap(s => s.tools))],
          reflection_log: reflectionText,
        }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => null);
        throw new Error(err?.detail || `HTTP ${response.status}`);
      }
      setFeedbackMessage({ text: "提交成功", type: 'success' });
      setTimeout(() => setFeedbackMessage(null), 2000);
      setDeliverableUrl('');
      setReflectionText('');
      setCollaborationMatrix(DEFAULT_COLLABORATION_MATRIX);
      setSubmitStep(1);
      setIsSubmitModalOpen(false);
      setExpandedCards(new Set());
      await fetchIterations();
    } catch (error) {
      console.error("Failed to submit iteration:", error);
      setFeedbackMessage({ text: "提交失败，请检查网络或后端状态。", type: 'error' });
      setTimeout(() => setFeedbackMessage(null), 4000);
    }
  };

  const generateAuthEvaluation = async () => {
    if (iterations.length === 0) { alert("当前没有可评估的迭代记录"); return; }
    setIsAuthEvaluating(true);
    try {
      const response = await fetch(`${API_BASE}/api/authenticity/${TASK_ID}/evaluate/${STUDENT_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail || `HTTP error: ${response.status}`);
      }
      const data = await response.json();
      setAuthEvaluationReport(data);
      setFeedbackMessage({ text: "真实性评估报告已生成", type: 'success' });
      setTimeout(() => setFeedbackMessage(null), 3000);
      setTimeout(() => { evalCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 100);
    } catch (error) {
      console.error("Failed to generate authenticity evaluation:", error);
      setFeedbackMessage({ text: "评估请求失败，请检查网络或后端状态。", type: 'error' });
      setTimeout(() => setFeedbackMessage(null), 4000);
    } finally {
      setIsAuthEvaluating(false);
    }
  };

  return (
    <div className="h-full w-full bg-slate-50 flex flex-col overflow-hidden">
      {feedbackMessage && (
        <div className={`fixed top-10 left-1/2 -translate-x-1/2 z-[100] px-6 py-3 rounded-md shadow-lg text-sm font-medium border ${
          feedbackMessage.type === 'success' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-rose-50 text-rose-800 border-rose-200'
        }`}>
          {feedbackMessage.text}
        </div>
      )}

      <div className="flex-1 flex w-full h-full overflow-hidden">
        {/* 左栏：迭代轨迹时间轴 */}
        <div className="w-[60%] h-full border-r border-slate-200 bg-white overflow-y-auto px-8 pb-8">
          {onBack && (
            <button type="button" onClick={onBack}
              className="mt-4 text-slate-500 hover:text-slate-900 transition-colors text-sm font-medium flex items-center gap-1">
              ← 返回
            </button>
          )}
          <div className="flex justify-between items-center mb-8 mt-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">迭代轨迹时间轴</h2>
              <p className="text-sm text-slate-500 mt-1">Iteration Timeline</p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <button onClick={() => setIsContextModalOpen(true)}
                className="bg-white/90 backdrop-blur border border-slate-200 shadow-sm px-4 py-2 rounded-lg flex flex-col items-start hover:bg-slate-50 transition-colors">
                <span className="text-xs font-medium uppercase tracking-wider text-blue-600">Task Context</span>
                <span className="text-sm font-semibold text-slate-800">查看当前任务情境与目标</span>
              </button>
              <div className="flex gap-3">
                <button onClick={() => setIsSubmitModalOpen(true)}
                  className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 gap-1.5">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>
                  提交新迭代版本
                </button>
                <button onClick={generateAuthEvaluation}
                  disabled={isAuthEvaluating || iterations.length === 0}
                  className={`inline-flex items-center justify-center px-4 py-2 border shadow-sm text-sm font-medium rounded-md gap-1.5 ${
                    isAuthEvaluating || iterations.length === 0
                      ? 'border-slate-200 text-slate-400 bg-slate-50 cursor-not-allowed'
                      : 'border-slate-300 text-slate-700 bg-white hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                  }`}>
                  生成真实性评估
                </button>
              </div>
            </div>
          </div>

          <div className="relative border-l-2 border-slate-200 ml-4 pb-16">
            {iterations.map((iteration, index) => {
              const isNewest = index === 0;
              const isExpanded = expandedCards.has(iteration.id);
              return (
                <div key={iteration.id} className="relative mb-8 pl-8"
                  onMouseEnter={() => setHoveredIterationId(iteration.id)}
                  onMouseLeave={() => setHoveredIterationId(null)}>
                  <div className="absolute -left-[5px] top-2 w-3 h-3 rounded-full border-2 border-white shadow-sm" style={{ backgroundColor: isNewest ? '#2563eb' : '#cbd5e1' }} />
                  <div className={`border shadow-sm rounded-xl overflow-hidden transition-all ${hoveredIterationId === iteration.id ? 'border-blue-400 ring-1 ring-blue-100' : 'border-slate-200'}`}>
                    <div className="p-4 cursor-pointer flex justify-between items-center bg-slate-50" onClick={() => toggleCard(iteration.id)}>
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 text-xs font-bold rounded ${isNewest ? 'bg-blue-100 text-blue-700' : 'bg-slate-200 text-slate-600'}`}>
                          V{iteration.version}
                        </span>
                        <h3 className="text-sm font-semibold text-slate-800">{iteration.title}</h3>
                      </div>
                      <div className="flex items-center gap-3">
                        {iteration.toolsUsed.length > 0 && (
                          <div className="flex gap-1">
                            {iteration.toolsUsed.slice(0, 3).map(t => (
                              <span key={t} className="text-[10px] font-medium text-slate-500 bg-slate-100 rounded-full px-2 py-0.5">{t}</span>
                            ))}
                            {iteration.toolsUsed.length > 3 && (
                              <span className="text-[10px] font-medium text-slate-400">+{iteration.toolsUsed.length - 3}</span>
                            )}
                          </div>
                        )}
                        <svg className={`w-4 h-4 text-slate-400 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                      </div>
                    </div>
                    {isExpanded && (
                      <div className="p-4 border-t border-slate-100">
                        <div className="text-xs text-slate-400 mb-3">{iteration.timestamp}</div>
                        <div className="mb-4">
                          <div className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">迭代反思</div>
                          <div className="text-sm leading-relaxed text-slate-600 bg-amber-50/50 border border-amber-100 p-3 rounded-lg">
                            {iteration.deltaNotes}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">交付物载体</div>
                          <a href={iteration.deliverableUrl} target="_blank" rel="noreferrer"
                            className="text-sm text-blue-600 hover:text-blue-800 hover:underline font-medium break-all block truncate">
                            {iteration.deliverableUrl}
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {authEvaluationReport !== null && (
            <div ref={evalCardRef} className="border-2 border-blue-500 rounded-xl bg-white shadow-sm overflow-hidden mt-4">
              <div className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center">
                <div>
                  <h3 className="text-sm font-bold">过程真实性评估报告</h3>
                  <p className="text-xs text-blue-200 mt-0.5">Authenticity Assessment · {authEvaluationReport?.rubric_version ?? '-'}</p>
                </div>
                <div className="text-right">
                  <div className="text-xs text-blue-200">总分</div>
                  <div className="text-2xl font-bold">{authEvaluationReport?.total_score ?? '-'} <span className="text-sm text-blue-200">/ 100</span></div>
                </div>
              </div>
              <div className="p-6">
                <div className="mb-6">
                  <h4 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">综合反馈</h4>
                  <div className="text-sm leading-relaxed text-slate-600 bg-slate-50 rounded-lg p-4 border border-slate-200">
                    {authEvaluationReport?.overall_feedback ?? '（无反馈内容）'}
                  </div>
                </div>
                {Array.isArray(authEvaluationReport?.dimension_scores) && authEvaluationReport.dimension_scores.length > 0 && (
                  <div className="mb-6">
                    <h4 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-3">维度得分</h4>
                    <div className="space-y-3">
                      {authEvaluationReport.dimension_scores.map((dim) => {
                        const pct = Math.round(((dim?.score ?? 0) / (dim?.max_score || 1)) * 100);
                        const color = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-rose-500';
                        const hasReason = dim?.reason && dim.reason.trim().length > 0;
                        return (
                          <div key={dim?.key ?? 'unknown'} className="border border-slate-200 rounded-lg p-4">
                            <div className="flex justify-between items-center mb-2">
                              <span className="text-xs font-medium uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                                {DIMENSION_LABELS[dim?.key] ?? dim?.key ?? '未知维度'}
                              </span>
                              <span className={`text-sm font-bold ${pct >= 80 ? 'text-emerald-500' : pct >= 60 ? 'text-amber-500' : 'text-rose-500'}`}>
                                {dim?.score ?? 0}/{dim?.max_score ?? '?'}
                              </span>
                            </div>
                            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                              <div className={`h-2 rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
                            </div>
                            {hasReason && <p className="text-sm text-slate-500 mt-2">{dim.reason}</p>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                {Array.isArray(authEvaluationReport?.improvement_advice) && authEvaluationReport.improvement_advice.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-3">改进建议</h4>
                    <div className="space-y-2">
                      {authEvaluationReport.improvement_advice.map((advice, idx) => (
                        <div key={idx} className="flex items-start gap-2 text-sm text-slate-600">
                          <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                          <span>{advice}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 右栏：人机协作透视面板 */}
        <div className="w-[40%] h-full bg-white overflow-y-auto px-8 pt-4 pb-8 border-l border-slate-200">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-slate-800">人机协作透视</h2>
            <p className="text-sm text-slate-500 mt-1">Collaboration Analytics</p>
          </div>

          <div className="mb-6 flex items-center justify-between border-b border-slate-200 pb-4">
            <span className="text-sm text-slate-500">当前透视版本：</span>
            <span className={`px-3 py-1 rounded text-sm font-bold ${
              hoveredIterationId
                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                : 'bg-blue-50 text-blue-700 border border-blue-200'
            }`}>
              {hoveredIterationId ? `历史预览 - V${displayIteration.version}` : `最新状态 - V${displayIteration.version}`}
            </span>
          </div>

          <div className="flex-1 flex flex-col gap-6">
            {displayIteration.stages.map((stage, idx) => {
              const humanColor = stage.humanPercent > stage.aiPercent ? 'bg-blue-600' : 'bg-blue-400';
              return (
                <div key={idx}>
                  <div className="flex justify-between items-baseline mb-2">
                    <span className="text-sm font-semibold text-slate-800">{stage.stageName}</span>
                    <div className="text-xs font-medium text-slate-500 flex gap-3">
                      <span className="text-blue-600">H {stage.humanPercent}%</span>
                      <span className="text-amber-600">AI {stage.aiPercent}%</span>
                    </div>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden flex">
                    <div className={`h-2 rounded-l-full ${humanColor} transition-all duration-500`} style={{ width: `${stage.humanPercent}%` }} />
                    <div className="h-2 bg-amber-400 rounded-r-full transition-all duration-500" style={{ width: `${stage.aiPercent}%` }} />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {stage.tools.length > 0 ? stage.tools.map(tool => (
                      <span key={tool} className="text-[10px] font-medium text-slate-600 bg-slate-100 rounded-full px-2 py-0.5">
                        {tool}
                      </span>
                    )) : (
                      <span className="text-[10px] text-slate-400 italic">无工具介入</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-auto pt-6 flex justify-between text-xs text-slate-500 border-t border-slate-200">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-sm bg-blue-600 inline-block" />
              Human（人类贡献）
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-sm bg-amber-400 inline-block" />
              AI（算力辅助）
            </div>
          </div>
        </div>
      </div>

      {/* 任务情境弹窗 */}
      {isContextModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col">
            <div className="p-6 border-b border-slate-200 flex justify-between items-center bg-slate-50">
              <h3 className="text-lg font-semibold text-slate-800">任务情境与评估标准</h3>
              <button onClick={() => setIsContextModalOpen(false)} className="text-slate-400 hover:text-slate-600 transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-8 overflow-y-auto max-h-[60vh]">
              <div className="space-y-6 text-sm text-slate-600">
                <div>
                  <h4 className="text-sm font-semibold text-blue-600 mb-2">背景描述</h4>
                  <p className="leading-relaxed">本任务要求你完成一篇关于"AI技术在自动驾驶领域应用风险"的商业分析报告。你需要提交不少于3000字的文档，并附带数据支撑。</p>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-blue-600 mb-2">真实性评估标准</h4>
                  <ul className="list-disc pl-5 space-y-2">
                    <li><strong>过程透明：</strong>严禁"一键生成并直接提交"。必须展示至少3次迭代过程。</li>
                    <li><strong>人机边界：</strong>在数据支撑阶段要求极高的人工审核比例（避免AI幻觉）。</li>
                    <li><strong>反思深度：</strong>评估你发现并纠正AI错误的能力。</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 提交弹窗 */}
      {isSubmitModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 py-10">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl h-[85vh] min-h-[500px] flex flex-col overflow-hidden">
            <div className="px-8 py-5 border-b border-slate-200 flex justify-between items-center shrink-0">
              <div className="flex items-center gap-4">
                <h3 className="text-lg font-semibold text-slate-800">提交新迭代版本</h3>
                <span className="bg-blue-50 text-blue-700 text-xs font-bold px-2 py-1 rounded">V{iterations[0].version + 1}</span>
              </div>
              <button onClick={() => setIsSubmitModalOpen(false)} className="text-slate-400 hover:text-slate-600 transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="bg-slate-50 flex px-8 py-4 gap-2 border-b shrink-0">
              {[1, 2, 3].map(step => (
                <div key={step} className={`h-2 flex-1 rounded-full transition-colors ${step <= submitStep ? 'bg-blue-600' : 'bg-slate-200'}`} />
              ))}
            </div>
            <div className="p-8 flex-1 overflow-y-auto bg-white">
              {submitStep === 1 && (
                <div className="animate-fade-in max-w-xl mx-auto">
                  <h4 className="text-sm font-semibold text-slate-800 mb-6 flex items-center gap-2">
                    <span className="bg-blue-50 text-blue-600 w-6 h-6 flex justify-center items-center rounded-full text-xs font-bold">1</span>
                    交付物载体链接
                  </h4>
                  <div className="space-y-4">
                    <label className="block">
                      <span className="text-sm font-medium text-slate-700 mb-1 block">文档/代码库 URL</span>
                      <input type="url" value={deliverableUrl} onChange={(e) => setDeliverableUrl(e.target.value)}
                        className="w-full border border-slate-300 rounded-md p-3 bg-slate-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm" placeholder="https://..." />
                    </label>
                  </div>
                </div>
              )}
              {submitStep === 2 && (
                <div className="animate-fade-in max-w-2xl mx-auto">
                  <h4 className="text-sm font-semibold text-slate-800 mb-6 flex items-center gap-2">
                    <span className="bg-blue-50 text-blue-600 w-6 h-6 flex justify-center items-center rounded-full text-xs font-bold">2</span>
                    协作透明度矩阵
                  </h4>
                  <p className="text-sm text-slate-500 mb-6">请如实评估在本版本迭代的各个阶段中，你与AI的工作比重。</p>
                  <div className="space-y-6">
                    {collaborationMatrix.map((stage, index) => (
                      <div key={index} className="border border-slate-200 rounded-xl p-6 shadow-sm hover:border-blue-300 transition-colors bg-white">
                        <div className="font-semibold text-slate-800 mb-5">{stage.stageName}</div>
                        <div className="mb-6">
                          <div className="flex justify-between text-xs font-medium text-slate-500 mb-3 uppercase tracking-wider">
                            <span className="text-blue-600 bg-blue-50 px-2 py-1 rounded">Human ({stage.humanPercent}%)</span>
                            <span className="text-amber-600 bg-amber-50 px-2 py-1 rounded">AI ({stage.aiPercent}%)</span>
                          </div>
                          <input type="range" min="0" max="100" value={stage.humanPercent}
                            onChange={(e) => {
                              const newHuman = parseInt(e.target.value, 10);
                              const newMatrix = [...collaborationMatrix];
                              newMatrix[index].humanPercent = newHuman;
                              newMatrix[index].aiPercent = 100 - newHuman;
                              setCollaborationMatrix(newMatrix);
                            }}
                            className="w-full h-2.5 bg-gradient-to-r from-blue-500 to-amber-400 rounded-lg appearance-none cursor-pointer shadow-inner" />
                        </div>
                        <div>
                          <span className="text-xs font-medium uppercase tracking-wider text-slate-500 block mb-3">介入工具记录</span>
                          <div className="flex flex-wrap gap-2.5">
                            {AVAILABLE_TOOLS.map(t => (
                              <label key={t} className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
                                <input type="checkbox" checked={stage.tools.includes(t)}
                                  onChange={(e) => {
                                    const newMatrix = [...collaborationMatrix];
                                    if (e.target.checked) {
                                      newMatrix[index].tools = [...newMatrix[index].tools, t];
                                    } else {
                                      newMatrix[index].tools = newMatrix[index].tools.filter(tool => tool !== t);
                                    }
                                    setCollaborationMatrix(newMatrix);
                                  }}
                                  className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500" />
                                <span className="text-sm text-slate-700 font-medium">{t}</span>
                              </label>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {submitStep === 3 && (
                <div className="animate-fade-in max-w-xl mx-auto">
                  <h4 className="text-sm font-semibold text-slate-800 mb-6 flex items-center gap-2">
                    <span className="bg-blue-50 text-blue-600 w-6 h-6 flex justify-center items-center rounded-full text-xs font-bold">3</span>
                    强制反思验证
                  </h4>
                  <div className="border border-amber-200 bg-amber-50 rounded-xl p-6 mb-6">
                    <h5 className="font-bold text-amber-800 mb-3 flex items-center gap-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                      提交前必答
                    </h5>
                    <p className="text-sm text-amber-700 mb-5 leading-relaxed">
                      请简述此版本中，你推翻了AI的哪些错误建议？或你如何引导AI深化了结果？（不少于50字，此内容将作为关键评估依据）
                    </p>
                    <textarea value={reflectionText} onChange={(e) => setReflectionText(e.target.value)}
                      className="w-full h-48 rounded-lg border-amber-200 focus:ring-2 focus:ring-amber-500 focus:border-amber-500 p-4 text-sm resize-none shadow-sm bg-white"
                      placeholder="在这一版中，我发现AI生成的代码存在安全漏洞，主要体现在..." />
                    <div className={`text-right text-xs mt-3 font-mono font-bold ${reflectionText.trim().length >= 50 ? 'text-emerald-600' : 'text-amber-600'}`}>
                      当前字数: {reflectionText.trim().length} / 50 {reflectionText.trim().length >= 50 ? '(已达标)' : '(不达标)'}
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="px-8 py-5 border-t bg-slate-50 flex justify-between items-center shrink-0">
              <button className={`px-4 py-2 rounded-md font-medium transition-colors text-sm ${submitStep > 1 ? 'text-slate-700 bg-white border border-slate-300 hover:bg-slate-50' : 'text-transparent cursor-default'}`}
                onClick={() => submitStep > 1 && setSubmitStep(s => s - 1)}>
                上一步
              </button>
              {submitStep < 3 ? (
                <button className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  onClick={() => setSubmitStep(s => s + 1)}>
                  下一步 →
                </button>
              ) : (
                <button className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-emerald-500 hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500"
                  onClick={submitIteration}>
                  确认归档此版本
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}