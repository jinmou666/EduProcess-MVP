import React, { useState, useMemo } from 'react';

// --- 类型定义 ---
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
};

// --- 模拟数据 (Mock Data) ---
const MOCK_ITERATIONS: Iteration[] = [
  {
    id: 'it_3',
    version: 3,
    timestamp: '2023-10-27 14:30',
    title: '核心逻辑重构与AI润色',
    deltaNotes: '推翻了AI在V2版本中生成的过于理想化的市场预估模型。我手动引入了最新的行业研报数据限制其边界，并引导AI重新生成了风险评估段落。',
    deliverableUrl: 'https://github.com/stu/project/commit/v3',
    stages: [
      { stageName: '① 资料检索与破冰', humanPercent: 80, aiPercent: 20, tools: ['Google Search'] },
      { stageName: '② 框架与逻辑构建', humanPercent: 90, aiPercent: 10, tools: ['Notion AI'] },
      { stageName: '③ 内容生成', humanPercent: 40, aiPercent: 60, tools: ['Claude 3.5'] },
      { stageName: '④ 润色与合规检查', humanPercent: 30, aiPercent: 70, tools: ['ChatGPT'] },
    ]
  },
  {
    id: 'it_2',
    version: 2,
    timestamp: '2023-10-26 09:15',
    title: '初稿生成与大面积扩写',
    deltaNotes: '基于V1的框架，完全交由AI进行正文填充。发现AI在细节论证上存在明显的幻觉（凭空捏造了几个数据），但我暂时保留以观后效。',
    deliverableUrl: 'https://docs.google.com/document/d/v2',
    stages: [
      { stageName: '① 资料检索与破冰', humanPercent: 40, aiPercent: 60, tools: ['Perplexity'] },
      { stageName: '② 框架与逻辑构建', humanPercent: 50, aiPercent: 50, tools: ['ChatGPT'] },
      { stageName: '③ 内容生成', humanPercent: 10, aiPercent: 90, tools: ['ChatGPT'] },
      { stageName: '④ 润色与合规检查', humanPercent: 10, aiPercent: 90, tools: ['ChatGPT'] },
    ]
  },
  {
    id: 'it_1',
    version: 1,
    timestamp: '2023-10-25 16:00',
    title: '需求拆解与大纲初建',
    deltaNotes: '刚接手任务，完全靠自己理解题目要求，仅使用搜索引擎查阅了专有名词，制定了初步的三级标题大纲。',
    deliverableUrl: 'https://docs.google.com/document/d/v1',
    stages: [
      { stageName: '① 资料检索与破冰', humanPercent: 95, aiPercent: 5, tools: ['Google Search'] },
      { stageName: '② 框架与逻辑构建', humanPercent: 100, aiPercent: 0, tools: [] },
      { stageName: '③ 内容生成', humanPercent: 100, aiPercent: 0, tools: [] },
      { stageName: '④ 润色与合规检查', humanPercent: 100, aiPercent: 0, tools: [] },
    ]
  }
];

const AVAILABLE_TOOLS = ['ChatGPT', 'Claude 3.5', 'Midjourney', 'GitHub Copilot', 'Perplexity', 'Notion AI'];

export default function AuthenticityModule() {
  const [iterations, setIterations] = useState<Iteration[]>(MOCK_ITERATIONS);
  const [hoveredIterationId, setHoveredIterationId] = useState<string | null>(null);

  const [isContextModalOpen, setIsContextModalOpen] = useState(false);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);

  const [submitStep, setSubmitStep] = useState(1);
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set([MOCK_ITERATIONS[0].id]));

  const displayIteration = useMemo(() => {
    if (hoveredIterationId) {
      return iterations.find(it => it.id === hoveredIterationId) || iterations[0];
    }
    return iterations[0];
  }, [hoveredIterationId, iterations]);

  const toggleCard = (id: string) => {
    const next = new Set(expandedCards);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpandedCards(next);
  };

  return (
    <div className="h-full w-full bg-gray-50 flex flex-col relative overflow-hidden">

      {/* 顶部全局悬浮按钮 */}
      <div className="absolute top-6 left-6 z-20">
        <button
          onClick={() => setIsContextModalOpen(true)}
          className="bg-white/90 backdrop-blur border-l-4 border-indigo-600 shadow-lg px-5 py-3 rounded-r-xl flex flex-col items-start hover:bg-indigo-50 transition-colors group"
        >
          <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider mb-1">Task Context</span>
          <span className="text-sm font-semibold text-gray-800 group-hover:text-indigo-800">查看当前任务情境与目标</span>
        </button>
      </div>

      <div className="flex-1 flex w-full h-full overflow-hidden">

        {/* ================= 左栏：迭代轨迹时间轴 (60%) ================= */}
        <div className="w-[60%] h-full border-r border-gray-200 bg-white relative flex flex-col pt-24 px-12 overflow-y-auto">

          <div className="flex justify-between items-center mb-10">
            <div>
              <h2 className="text-2xl font-black text-gray-900">迭代轨迹时间轴</h2>
              <p className="text-sm text-gray-500 mt-1">Iteration Timeline</p>
            </div>
            <button
              onClick={() => setIsSubmitModalOpen(true)}
              className="bg-indigo-600 text-white px-6 py-3 rounded-full font-bold shadow-lg shadow-indigo-200 hover:bg-indigo-700 hover:shadow-xl hover:-translate-y-0.5 transition-all flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"></path></svg>
              提交新迭代版本
            </button>
          </div>

          <div className="relative border-l-2 border-indigo-100 ml-[100px] pb-20">
            {iterations.map((iteration, index) => {
              const isNewest = index === 0;
              const isExpanded = expandedCards.has(iteration.id);

              return (
                <div
                  key={iteration.id}
                  className="relative mb-12"
                  onMouseEnter={() => setHoveredIterationId(iteration.id)}
                  onMouseLeave={() => setHoveredIterationId(null)}
                >
                  <div className="absolute -left-[120px] top-1 w-[100px] text-right">
                    <div className="text-xs font-bold text-gray-400">
                      {iteration.timestamp.split(' ')[0]}
                    </div>
                    <div className="text-sm font-black text-gray-700">
                      {iteration.timestamp.split(' ')[1]}
                    </div>
                  </div>

                  <div className={`absolute -left-[9px] top-2 w-4 h-4 rounded-full border-4 border-white shadow ${isNewest ? 'bg-indigo-500' : 'bg-gray-300'}`}></div>

                  <div className={`ml-8 bg-white border rounded-xl shadow-sm transition-all duration-300 overflow-hidden ${hoveredIterationId === iteration.id ? 'border-indigo-400 shadow-md ring-2 ring-indigo-50' : 'border-gray-200 hover:border-gray-300'}`}>
                    <div
                      className="p-5 cursor-pointer flex justify-between items-center bg-gray-50/50"
                      onClick={() => toggleCard(iteration.id)}
                    >
                      <div className="flex items-center gap-3">
                        <span className={`px-2.5 py-1 text-xs font-black rounded ${isNewest ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-200 text-gray-600'}`}>
                          V{iteration.version}
                        </span>
                        <h3 className="text-lg font-bold text-gray-800">{iteration.title}</h3>
                      </div>
                      <svg className={`w-5 h-5 text-gray-400 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                    </div>

                    <div className={`transition-all duration-300 ${isExpanded ? 'max-h-[500px] opacity-100 border-t border-gray-100' : 'max-h-0 opacity-0'} overflow-hidden`}>
                      <div className="p-5">
                        <div className="mb-4">
                          <div className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                            迭代反思日志 (Delta Notes)
                          </div>
                          <div className="text-sm text-gray-700 bg-orange-50/50 p-4 rounded-lg leading-relaxed border border-orange-100/50">
                            {iteration.deltaNotes}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
                            交付物载体
                          </div>
                          <a href={iteration.deliverableUrl} target="_blank" rel="noreferrer" className="text-sm text-indigo-600 hover:text-indigo-800 hover:underline font-medium break-all block truncate">
                            {iteration.deliverableUrl}
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ================= 右栏：人机协作透视面板 (40%) ================= */}
        <div className="w-[40%] h-full bg-slate-900 text-white flex flex-col px-10 pt-24 pb-12 relative overflow-y-auto">
          <div className="absolute top-[-20%] right-[-10%] w-96 h-96 bg-indigo-500 rounded-full blur-[120px] opacity-20 pointer-events-none"></div>

          <div>
            <h2 className="text-2xl font-black mb-1">人机协作透视</h2>
            <p className="text-slate-400 text-sm mb-10">Collaboration Analytics</p>
          </div>

          <div className="mb-8 flex items-center justify-between border-b border-slate-700 pb-4">
            <span className="text-sm font-medium text-slate-300">当前透视版本：</span>
            <span className={`px-3 py-1 rounded text-sm font-bold transition-all ${hoveredIterationId ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'}`}>
              {hoveredIterationId ? `历史预览 - V${displayIteration.version}` : `最新状态 - V${displayIteration.version}`}
            </span>
          </div>

          <div className="flex-1 flex flex-col space-y-8">
            {displayIteration.stages.map((stage, idx) => (
              <div key={idx} className="group">
                <div className="flex justify-between items-end mb-2">
                  <span className="text-sm font-bold text-slate-200">{stage.stageName}</span>
                  <div className="text-xs font-mono text-slate-400 flex gap-3">
                    <span className="text-indigo-300">H: {stage.humanPercent}%</span>
                    <span className="text-orange-300">AI: {stage.aiPercent}%</span>
                  </div>
                </div>

                <div className="w-full h-4 rounded-full bg-slate-800 flex overflow-hidden shadow-inner">
                  <div
                    className="h-full bg-indigo-500 transition-all duration-700 ease-out relative"
                    style={{ width: `${stage.humanPercent}%` }}
                  >
                    <div className="absolute inset-0 bg-white/20 w-full h-full transform -skew-x-12 translate-x-full group-hover:translate-x-0 transition-transform duration-1000"></div>
                  </div>
                  <div
                    className="h-full bg-orange-400 transition-all duration-700 ease-out"
                    style={{ width: `${stage.aiPercent}%` }}
                  ></div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {stage.tools.length > 0 ? stage.tools.map(tool => (
                    <span key={tool} className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      {tool}
                    </span>
                  )) : (
                    <span className="text-[10px] text-slate-500 italic">无工具介入</span>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-auto pt-8 flex justify-between text-xs text-slate-500 border-t border-slate-800">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-sm bg-indigo-500 inline-block"></span>
              Human (人类贡献)
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-sm bg-orange-400 inline-block"></span>
              AI (算力辅助)
            </div>
          </div>
        </div>
      </div>

      {/* ================= 模态弹窗 1：任务情境 ================= */}
      {isContextModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-indigo-50/50">
              <h3 className="text-xl font-black text-gray-800">任务情境与评估标准</h3>
              <button onClick={() => setIsContextModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>
            <div className="p-8 overflow-y-auto max-h-[60vh]">
              <div className="prose prose-sm md:prose-base text-gray-600">
                <h4 className="text-indigo-600 font-bold mb-2">背景描述</h4>
                <p>本任务要求你完成一篇关于“AI技术在自动驾驶领域应用风险”的商业分析报告。你需要提交不少于3000字的文档，并附带数据支撑。</p>
                <h4 className="text-indigo-600 font-bold mt-6 mb-2">真实性评估标准 (Rubrics)</h4>
                <ul className="list-disc pl-5 space-y-2">
                  <li><strong>过程透明：</strong>严禁“一键生成并直接提交”。必须展示至少3次迭代过程。</li>
                  <li><strong>人机边界：</strong>在数据支撑阶段要求极高的人工审核比例（避免AI幻觉）。</li>
                  <li><strong>反思深度：</strong>评估你发现并纠正AI错误的能力。</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= 模态弹窗 2：多步提交 (已修复边界溢出) ================= */}
      {isSubmitModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-sm p-4 py-10">
          {/* 【残酷诊断定位】这里就是病根！
            之前这里缺乏严格的高度约束（只有 min-h）。
            现在我用 `h-[85vh]` 将弹窗锁死在屏幕高度的 85%，确保它绝对不会溢出可视区域。
            内部容器使用 flex-col 和 flex-1 overflow-y-auto 自动接管滚动条逻辑。
          */}
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl h-[85vh] min-h-[500px] flex flex-col overflow-hidden">

            {/* Header (固定不滚动) */}
            <div className="px-8 py-5 border-b border-gray-100 flex justify-between items-center shrink-0">
              <div className="flex items-center gap-4">
                <h3 className="text-xl font-black text-gray-800">提交新迭代版本</h3>
                <span className="bg-indigo-100 text-indigo-700 text-xs font-bold px-2 py-1 rounded">V{iterations[0].version + 1}</span>
              </div>
              <button onClick={() => setIsSubmitModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>

            {/* Stepper indicator (固定不滚动) */}
            <div className="bg-gray-50 flex px-8 py-4 gap-2 border-b shrink-0">
              {[1, 2, 3].map(step => (
                <div key={step} className={`h-2 flex-1 rounded-full transition-colors ${step <= submitStep ? 'bg-indigo-600' : 'bg-gray-200'}`}></div>
              ))}
            </div>

            {/* Form Body (核心改动：flex-1 和 overflow-y-auto 配合定高的父级生效) */}
            <div className="p-8 flex-1 overflow-y-auto relative bg-white">

              {submitStep === 1 && (
                <div className="animate-fade-in max-w-xl mx-auto">
                  <h4 className="text-lg font-bold mb-6 flex items-center gap-2"><span className="bg-indigo-100 text-indigo-600 w-6 h-6 flex justify-center items-center rounded-full text-sm">1</span> 交付物载体链接</h4>
                  <div className="space-y-4">
                    <label className="block">
                      <span className="text-sm font-semibold text-gray-700 mb-1 block">版本概要标题</span>
                      <input type="text" className="w-full border-gray-300 rounded-lg p-3 bg-gray-50 border focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="例如：重写第二章节逻辑..." />
                    </label>
                    <label className="block">
                      <span className="text-sm font-semibold text-gray-700 mb-1 block">文档/代码库 URL</span>
                      <input type="url" className="w-full border-gray-300 rounded-lg p-3 bg-gray-50 border focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="https://..." />
                    </label>
                    <div className="mt-6 border-2 border-dashed border-gray-300 rounded-xl p-10 flex flex-col items-center justify-center text-gray-400 bg-gray-50 hover:bg-gray-100 cursor-pointer transition-colors">
                      <svg className="w-10 h-10 mb-2 text-indigo-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                      <span className="font-semibold text-gray-600">点击或拖拽文件到此处上传作为附件</span>
                    </div>
                  </div>
                </div>
              )}

              {submitStep === 2 && (
                <div className="animate-fade-in max-w-2xl mx-auto">
                  <h4 className="text-lg font-bold mb-6 flex items-center gap-2"><span className="bg-indigo-100 text-indigo-600 w-6 h-6 flex justify-center items-center rounded-full text-sm">2</span> 协作透明度矩阵 (Collaboration Matrix)</h4>
                  <p className="text-sm text-gray-500 mb-6">请如实评估在本版本迭代的各个阶段中，你与AI的工作比重。</p>

                  <div className="space-y-6">
                    {MOCK_ITERATIONS[0].stages.map((stage, idx) => (
                      <div key={idx} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm hover:border-indigo-300 transition-colors">
                        <div className="font-bold text-gray-800 mb-5">{stage.stageName}</div>

                        <div className="mb-6">
                          <div className="flex justify-between text-xs font-bold text-gray-400 mb-3 uppercase tracking-wider">
                            <span className="text-indigo-600 bg-indigo-50 px-2 py-1 rounded">Human (100%)</span>
                            <span className="text-orange-500 bg-orange-50 px-2 py-1 rounded">AI (100%)</span>
                          </div>
                          <input
                            type="range"
                            min="0" max="100"
                            defaultValue="50"
                            className="w-full h-2.5 bg-gradient-to-r from-indigo-500 to-orange-400 rounded-lg appearance-none cursor-pointer shadow-inner"
                          />
                        </div>

                        <div>
                          <span className="text-xs font-bold text-gray-500 block mb-3 uppercase tracking-wider">介入工具记录 (Tools)</span>
                          <div className="flex flex-wrap gap-2.5">
                            {AVAILABLE_TOOLS.map(t => (
                              <label key={t} className="flex items-center gap-2 bg-gray-50 border border-gray-200 px-3 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
                                <input type="checkbox" className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500" />
                                <span className="text-sm text-gray-700 font-medium">{t}</span>
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
                  <h4 className="text-lg font-bold mb-6 flex items-center gap-2"><span className="bg-indigo-100 text-indigo-600 w-6 h-6 flex justify-center items-center rounded-full text-sm">3</span> 强制反思验证 (Forced Reflection)</h4>
                  <div className="bg-orange-50 border border-orange-200 rounded-xl p-6 mb-6">
                    <h5 className="font-bold text-orange-800 mb-3 flex items-center gap-2 text-lg">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                      提交前必答
                    </h5>
                    <p className="text-sm text-orange-700 mb-5 leading-relaxed">
                      请简述此版本中，你推翻了AI的哪些错误建议？或你如何引导AI深化了结果？（不少于 50 字，此内容将作为关键评估依据）
                    </p>
                    <textarea
                      className="w-full h-48 rounded-xl border-orange-300 focus:ring-2 focus:ring-orange-500 focus:border-orange-500 p-4 text-sm resize-none shadow-sm"
                      placeholder="在这一版中，我发现AI生成的代码存在安全漏洞，主要体现在..."
                    ></textarea>
                    <div className="text-right text-xs text-orange-600 mt-3 font-mono font-bold">当前字数: 0 / 50 (不达标)</div>
                  </div>
                </div>
              )}

            </div>

            {/* Footer Actions (固定不滚动) */}
            <div className="px-8 py-5 border-t bg-gray-50 flex justify-between items-center shrink-0">
              <button
                className={`px-6 py-2.5 rounded-lg font-bold transition-colors ${submitStep > 1 ? 'text-gray-600 hover:bg-gray-200' : 'text-transparent cursor-default'}`}
                onClick={() => submitStep > 1 && setSubmitStep(s => s - 1)}
              >
                上一步
              </button>

              {submitStep < 3 ? (
                <button
                  className="bg-indigo-600 text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-indigo-200 hover:bg-indigo-700 hover:-translate-y-0.5 transition-all"
                  onClick={() => setSubmitStep(s => s + 1)}
                >
                  下一步 →
                </button>
              ) : (
                <button
                  className="bg-green-600 text-white px-8 py-2.5 rounded-lg font-bold shadow-lg shadow-green-200 hover:bg-green-700 hover:-translate-y-0.5 transition-all"
                  onClick={() => {
                    alert('注意：这只是前端原型展示。你还需要编写后端的 models.py 以保存这些迭代数据！');
                    setIsSubmitModalOpen(false);
                    setSubmitStep(1);
                  }}
                >
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