import React, { useState, useEffect, useCallback } from 'react';

// --- 类型定义 ---
type Critique = {
  quote: string;
  rewrite: string;
  citation: string;
  selection_range: [number, number];
};

type TaskData = {
  id: number;
  title: string;
  content: string;
  publish_date: string;
  deadline: string;
};

// === 1. 追加的类型定义 ===
type EvaluationDetail = {
  step1_match: string;
  step2_score: number;
  step2_feedback: string;
};

type EvaluationReport = {
  total_score: number;
  overall_feedback: string;
  details: EvaluationDetail[];
};

type FeedbackMessage = {
  text: string;
  type: 'success' | 'error';
};


const API_BASE = "http://127.0.0.1:8000";
// 全局硬编码的学生身份！必须与 init_data.py 中生成的一致
const CURRENT_STUDENT_ID = "20230001";

export default function CritiqueModule() {

  const [score, setScore] = useState<number | null>(null);
  const [evaluationReport, setEvaluationReport] = useState<EvaluationReport | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [view, setView] = useState<'list' | 'detail'>('list');
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [task, setTask] = useState<TaskData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [critiques, setCritiques] = useState<Critique[]>([]);
  const [selectedCritiqueIndex, setSelectedCritiqueIndex] = useState<number | null>(null);

  const [feedbackMessage, setFeedbackMessage] = useState<FeedbackMessage | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [tempSelection, setTempSelection] = useState<{quote: string, start: number, end: number} | null>(null);
  const [rewriteInput, setRewriteInput] = useState("");
  const [citationInput, setCitationInput] = useState("");

  // 1. 获取任务列表 (依然请求 /tasks)
  useEffect(() => {
    fetch(`${API_BASE}/tasks`)
      .then(res => {
        if (!res.ok) throw new Error("无法连接后端 API");
        return res.json();
      })
      .then(data => {
        setTasks(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "未设定";
    const d = new Date(dateStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  };

  // 2. 进入具体任务：拉取该学生之前的历史提交数据
  // 2. 进入具体任务：拉取该学生之前的历史提交数据
  const handleTaskClick = async (selectedTask: TaskData) => {
    setTask(selectedTask);
    setView('detail');

    // 每次进入任务时，评估结果都要求重新生成（不沿用历史评估显示）
    setScore(null);
    setEvaluationReport(null);

    // 进入任务时清空选中态
    setSelectedCritiqueIndex(null);

    try {
      const res = await fetch(`${API_BASE}/critique/${selectedTask.id}/${CURRENT_STUDENT_ID}`);
      if (res.ok) {
        const data = await res.json();
        // 原有逻辑：设置纠错记录
        setCritiques(data.critiques_data || []);
        setSelectedCritiqueIndex(null);
      } else if (res.status === 404) {
        // 如果报 404，说明还没做过这个任务
        setCritiques([]);
        setSelectedCritiqueIndex(null);
      } else {
        console.error("Failed to load past submission");
      }
    } catch (err) {
      console.error("Network error:", err);
      // 网络报错时，保险起见也全部清空
      setCritiques([]);
      setScore(null);
      setEvaluationReport(null);
    }
  };

  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const selectedText = selection.toString().trim();
    if (selectedText.length === 0) return;

    const container = document.getElementById('content-area-react');
    if (!container || !container.contains(selection.anchorNode)) return;

    const range = selection.getRangeAt(0);
    const preSelectionRange = range.cloneRange();
    preSelectionRange.selectNodeContents(container);
    preSelectionRange.setEnd(range.startContainer, range.startOffset);
    const start = preSelectionRange.toString().length;
    const end = start + selectedText.length;

    setTempSelection({ quote: selectedText, start, end });
    setIsModalOpen(true);
    setRewriteInput("");
    setCitationInput("");
  }, [task]);

  const saveCritique = () => {
    if (!tempSelection || !rewriteInput) return;

    const newCritique: Critique = {
      quote: tempSelection.quote,
      rewrite: rewriteInput,
      citation: citationInput,
      selection_range: [tempSelection.start, tempSelection.end]
    };

    setCritiques(prev => {
        const filtered = prev.filter(item => {
            const startOld = item.selection_range[0];
            const endOld = item.selection_range[1];
            const startNew = newCritique.selection_range[0];
            const endNew = newCritique.selection_range[1];
            return !(startOld < endNew && endOld > startNew);
        });
        return [...filtered, newCritique].sort((a, b) => a.selection_range[0] - b.selection_range[0]);
    });

    // 新增/覆盖纠错后取消旧选中（避免索引错位）
    setSelectedCritiqueIndex(null);

    setIsModalOpen(false);
    window.getSelection()?.removeAllRanges();
  };

  const deleteCritique = (index: number) => {
    setCritiques(prev => prev.filter((_, i) => i !== index));
    setSelectedCritiqueIndex(prev => (prev === index ? null : prev));
  };

  // 3. 提交数据：快照覆写模式
  const submitAssignment = async () => {
    try {
      // 【核心改动：使用 PUT，指向精确的 RESTful 路由，Payload 只传 critiques_data】
      const res = await fetch(`${API_BASE}/critique/${task?.id}/${CURRENT_STUDENT_ID}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          critiques_data: critiques
        })
      });

       if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || "提交失败");
       }

       setFeedbackMessage({ text: "提交成功", type: 'success' });
       setTimeout(() => setFeedbackMessage(null), 2000);
       // 提交成功后保持在当前任务详情页
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "提交失败，请检查网络连接。";
      setFeedbackMessage({ text: err instanceof Error ? `提交失败: ${message}` : message, type: 'error' });
      setTimeout(() => setFeedbackMessage(null), 4000);
    }
  };

  const generateEvaluation = async () => {
    // 防御性校验
    if (!task?.id) return;
    if (critiques.length === 0) {
      alert("当前没有可评估的纠错记录，请先添加内容。");
      return;
    }

    setIsEvaluating(true);
    try {
      // 注意：这里的 CURRENT_STUDENT_ID 需替换为你代码中实际使用的变量名
      const response = await fetch(`${API_BASE}/api/tasks/${task.id}/evaluate/${CURRENT_STUDENT_ID}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

      const data = await response.json();

      // 更新评估状态，触发 UI 重绘
      setScore(data.score ?? null);
      setEvaluationReport(data.evaluation_report ?? null);

    } catch (error) {
      console.error("Failed to generate evaluation:", error);
      alert("AI 引擎评估请求失败，请检查网络或后端状态。");
    } finally {
      setIsEvaluating(false);
    }
  };


  const renderHighlightedContent = () => {
    if (!task) return null;
    const text = task.content;
    if (critiques.length === 0) return text;

    const elements = [];
    let lastIndex = 0;

    critiques.forEach((critique, idx) => {
      const [start, end] = critique.selection_range;
      if (start > lastIndex) {
        elements.push(<span key={`text-${idx}`}>{text.slice(lastIndex, start)}</span>);
      }
      elements.push(
        <mark
            key={`mark-${idx}`}
            className="bg-yellow-200 text-gray-900 px-1 rounded cursor-pointer border-b-2 border-red-400"
            title={`修正: ${critique.rewrite}`}
        >
          {text.slice(start, end)}
        </mark>
      );
      lastIndex = end;
    });

    if (lastIndex < text.length) {
      elements.push(<span key="text-end">{text.slice(lastIndex)}</span>);
    }
    return elements;
  };

  if (loading) return <div className="p-8 text-center text-gray-500">正在加载数据...</div>;
  if (error) return <div className="p-8 text-center text-red-500">错误: {error}</div>;

  if (view === 'list') {
    return (
      <div className="h-full overflow-y-auto bg-gray-100 p-8">
        {/* 全局 Toast 反馈 UI（与知识拓扑模块提示风格对齐） */}
        {feedbackMessage && (
          <div
            className={`fixed top-4 left-1/2 transform -translate-x-1/2 z-50 px-6 py-3 rounded shadow-xl text-sm font-medium animate-fade-in-down ${
              feedbackMessage.type === 'success'
                ? 'bg-green-100 text-green-800 border border-green-300'
                : 'bg-red-100 text-red-800 border border-red-300'
            }`}
          >
            {feedbackMessage.text}
          </div>
        )}
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-800 mb-8">待完成的批判任务</h2>

          {tasks.length === 0 ? (
            <div className="text-center text-gray-500 py-10">暂无任务数据，请运行后端初始化脚本</div>
          ) : (
            <div className="space-y-4">
              {tasks.map((t, index) => (
                <div
                  key={t.id}
                  onClick={() => handleTaskClick(t)}
                  className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 cursor-pointer hover:border-indigo-500 hover:shadow-md transition-all duration-200 group"
                >
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-sm font-bold text-gray-400 uppercase tracking-wider">
                      Task {index + 1}
                    </span>
                    <span className="text-xs px-3 py-1 bg-indigo-50 text-indigo-700 font-medium rounded-full">
                      去纠错 →
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-gray-800 mb-4 group-hover:text-indigo-600 transition-colors">
                    {t.title}
                  </h3>
                  <div className="flex gap-6 text-sm text-gray-500">
                    <div className="flex items-center gap-1">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                      发布: {formatDate(t.publish_date)}
                    </div>
                    <div className="flex items-center gap-1">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                      截止: <span className="text-red-500 font-medium">{formatDate(t.deadline)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden relative">
      {/* 全局 Toast 反馈 UI（与知识拓扑模块提示风格对齐） */}
      {feedbackMessage && (
        <div
          className={`fixed top-4 left-1/2 transform -translate-x-1/2 z-50 px-6 py-3 rounded shadow-xl text-sm font-medium animate-fade-in-down ${
            feedbackMessage.type === 'success'
              ? 'bg-green-100 text-green-800 border border-green-300'
              : 'bg-red-100 text-red-800 border border-red-300'
          }`}
        >
          {feedbackMessage.text}
        </div>
      )}
      <div className="absolute top-4 left-4 z-10">
        <button
          onClick={() => setView('list')}
          className="bg-white px-4 py-2 text-sm font-bold text-gray-600 rounded-lg shadow border hover:text-indigo-600 flex items-center gap-2"
        >
          <span>← 返回列表</span>
        </button>
      </div>

      <div className="w-2/3 pt-20 px-10 pb-10 overflow-y-auto bg-white border-r">
        <div className="flex justify-between items-end mb-6">
          <h2 className="text-3xl font-bold">{task?.title}</h2>
          <div className="text-sm text-gray-400 text-right">
            <div>发布: {formatDate(task?.publish_date || '')}</div>
            <div className="text-red-400">截止: {formatDate(task?.deadline || '')}</div>
          </div>
        </div>

        <div
          id="content-area-react"
          className="bg-gray-50 p-8 rounded-xl leading-loose text-lg border border-gray-200 relative whitespace-pre-wrap text-gray-800 shadow-inner"
          onMouseUp={handleMouseUp}
        >
          {renderHighlightedContent()}
        </div>
        <p className="mt-4 text-sm text-gray-400 font-medium">* 鼠标拖拽选中文本进行纠错，重叠区域会自动覆盖。</p>
      </div>

      <div className="w-1/3 bg-gray-50 flex flex-col border-l">
        <div className="p-4 border-b bg-white font-bold text-gray-700 flex justify-between items-center">
          <span>纠错记录</span>
          <span className="bg-indigo-100 text-indigo-800 py-0.5 px-2.5 rounded-full text-xs">{critiques.length}</span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {critiques.length === 0 && (
            <div className="text-center text-gray-400 mt-20 flex flex-col items-center">
              <svg className="w-12 h-12 mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
              暂无记录<br/>请在左侧选中文本开始
            </div>
          )}
          {critiques.map((item, idx) => (
            <div
              key={idx}
              onClick={() => setSelectedCritiqueIndex(idx)}
              className={`bg-white p-4 rounded-lg shadow-sm text-sm border transition-colors cursor-pointer ${
                selectedCritiqueIndex === idx
                  ? 'border-indigo-400 ring-2 ring-indigo-100'
                  : 'hover:border-indigo-300'
              }`}
            >
               <div className="flex items-start justify-between gap-3 mb-2">
                 <div className="text-gray-500 line-through text-xs bg-red-50 p-2 rounded flex-1">
                   "{item.quote}"
                 </div>
                 <button
                   type="button"
                   onClick={(e) => {
                     e.stopPropagation();
                     deleteCritique(idx);
                   }}
                   className="shrink-0 px-3 py-1.5 text-xs font-bold rounded-lg border border-red-200 text-red-600 bg-red-50 hover:bg-red-100 hover:border-red-300 transition-colors"
                   aria-label="删除该条纠错记录"
                 >
                   删除
                 </button>
               </div>
               <div className="font-medium text-green-700 mb-2">
                 👉 {item.rewrite}
               </div>
               <div className="text-xs text-gray-400 border-t pt-2 mt-2 flex items-start gap-1">
                 <span>📚</span> <span className="leading-tight">{item.citation}</span>
               </div>
            </div>
          ))}
          {/* ================= AI 评估入口与结果面板 ================= */}
          <div className="mt-6 border-t border-gray-200 pt-6">
            {/* 触发按钮 */}
            <button
              onClick={generateEvaluation}
              disabled={isEvaluating || critiques.length === 0}
              className={`w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-bold transition-all shadow-md ${
                isEvaluating || critiques.length === 0
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed shadow-none'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-lg hover:-translate-y-0.5'
              }`}
            >
              {isEvaluating ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  正在呼叫 AI 引擎进行深度计算...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                  生成智能评估 (AI Evaluation)
                </>
              )}
            </button>

            {/* 评估结果面板卡片 */}
            {evaluationReport !== null && (
              <div className="mt-6 bg-white border border-indigo-100 rounded-2xl shadow-xl overflow-hidden animate-fade-in-up">
                {/* 卡片头部 */}
                <div className="bg-gradient-to-r from-indigo-50 to-white px-6 py-5 border-b border-indigo-50 flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="bg-indigo-100 p-2.5 rounded-lg text-indigo-600">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"></path></svg>
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-gray-800">AI 智能诊断报告</h3>
                      <p className="text-xs text-gray-500 font-medium">Undergraduate Assessment Engine</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-gray-500 mb-1">Total Score</div>
                    <div className="text-3xl font-black text-indigo-600 drop-shadow-sm">
                      {evaluationReport.total_score} <span className="text-base text-gray-400 font-bold">/ 100</span>
                    </div>
                  </div>
                </div>

                {/* 卡片主体 */}
                <div className="p-6">
                  {/* 综合反馈 */}
                  <div className="mb-6">
                    <h4 className="text-sm font-bold text-gray-700 mb-2 flex items-center gap-2">
                      <span className="w-1.5 h-4 bg-indigo-500 rounded-full inline-block"></span>
                      综合反馈 (Overall Feedback)
                    </h4>
                    <div className="bg-gray-50 rounded-xl p-4 text-sm text-gray-600 leading-relaxed border border-gray-100">
                      {evaluationReport.overall_feedback}
                    </div>
                  </div>

                  {/* 详细诊断列表 */}
                  <div>
                    <h4 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
                      <span className="w-1.5 h-4 bg-indigo-500 rounded-full inline-block"></span>
                      逻辑推演细节 (Diagnostic Details)
                    </h4>
                    <div className="space-y-4">
                      {evaluationReport.details.map((detail, index) => (
                        <div key={index} className="bg-white border border-gray-200 rounded-xl p-4 hover:border-indigo-300 transition-colors shadow-sm">
                          <div className="flex justify-between items-start mb-3">
                            <span className="bg-indigo-50 text-indigo-700 text-xs font-bold px-2.5 py-1 rounded">
                              纠错条目 {index + 1}
                            </span>
                            <span className={`text-sm font-black ${detail.step2_score >= 80 ? 'text-green-600' : detail.step2_score >= 60 ? 'text-orange-500' : 'text-red-500'}`}>
                              单项得分: {detail.step2_score}
                            </span>
                          </div>

                          <div className="space-y-3">
                            <div>
                              <span className="text-xs font-bold text-gray-400 uppercase tracking-wide block mb-1">语义匹配度分析</span>
                              <p className="text-sm text-gray-700 bg-gray-50 p-2.5 rounded border border-gray-100">
                                {detail.step1_match}
                              </p>
                            </div>
                            <div>
                              <span className="text-xs font-bold text-gray-400 uppercase tracking-wide block mb-1">扣分判定与指导</span>
                              <p className="text-sm text-gray-700 bg-indigo-50/40 p-2.5 rounded border border-indigo-50">
                                {detail.step2_feedback}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="p-4 bg-white border-t">
            <button
              onClick={submitAssignment}
              disabled={critiques.length === 0}
              className={`w-full py-3 rounded-lg font-bold shadow transition-colors ${critiques.length > 0 ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'}`}
            >
                保存此版本
            </button>
        </div>


      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
            <div className="bg-white p-6 rounded-xl w-full max-w-md shadow-2xl transform transition-all">
                <h3 className="text-xl font-bold mb-4 text-gray-800">添加内容纠错</h3>
                <div className="bg-red-50 p-3 text-sm text-red-800 mb-4 italic rounded-lg line-clamp-3 border border-red-100">
                    "{tempSelection?.quote}"
                </div>
                <label className="block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide">你的修正</label>
                <textarea
                    className="w-full border border-gray-300 p-3 rounded-lg mb-4 focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
                    placeholder="请输入正确的内容描述..."
                    rows={4}
                    value={rewriteInput}
                    onChange={e => setRewriteInput(e.target.value)}
                />
                <label className="block text-xs font-bold text-gray-500 mb-1 uppercase tracking-wide">理论依据 (Citation)</label>
                <input
                    className="w-full border border-gray-300 p-3 rounded-lg mb-6 focus:ring-2 focus:ring-indigo-500 outline-none"
                    placeholder="例如：计算机网络(第7版) P123"
                    value={citationInput}
                    onChange={e => setCitationInput(e.target.value)}
                />
                <div className="flex justify-end gap-3">
                    <button onClick={() => setIsModalOpen(false)} className="px-5 py-2 bg-gray-100 text-gray-700 font-bold rounded-lg hover:bg-gray-200 transition-colors">取消</button>
                    <button onClick={saveCritique} className="px-5 py-2 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700 transition-colors shadow-md">保存记录</button>
                </div>
            </div>
        </div>
      )}
    </div>
  );
}
