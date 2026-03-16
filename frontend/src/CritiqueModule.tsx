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

const API_BASE = "http://127.0.0.1:8000";
// 🚨 全局硬编码的学生身份！必须与 init_data.py 中生成的一致
const CURRENT_STUDENT_ID = "20230001";

export default function CritiqueModule() {
  const [view, setView] = useState<'list' | 'detail'>('list');
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [task, setTask] = useState<TaskData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [critiques, setCritiques] = useState<Critique[]>([]);

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
  const handleTaskClick = async (selectedTask: TaskData) => {
    setTask(selectedTask);
    setView('detail');

    // 【核心改动：对接后端的 GET /critique/{task_id}/{student_id}】
    try {
      const res = await fetch(`${API_BASE}/critique/${selectedTask.id}/${CURRENT_STUDENT_ID}`);
      if (res.ok) {
        const data = await res.json();
        setCritiques(data.critiques_data || []);
      } else if (res.status === 404) {
        // 如果报 404，说明该学生还没做过这个任务，初始化为空数组
        setCritiques([]);
      } else {
        console.error("Failed to load past submission");
      }
    } catch (err) {
      console.error("Network error:", err);
      setCritiques([]);
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

    setIsModalOpen(false);
    window.getSelection()?.removeAllRanges();
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

      alert(`保存成功！这属于全量快照覆盖。`);
      setView('list');
    } catch (err: any) {
      alert(`保存失败: ${err.message}`);
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
            <div key={idx} className="bg-white p-4 rounded-lg shadow-sm text-sm border hover:border-indigo-300 transition-colors">
               <div className="mb-2 text-gray-500 line-through text-xs bg-red-50 p-2 rounded">
                 "{item.quote}"
               </div>
               <div className="font-medium text-green-700 mb-2">
                 👉 {item.rewrite}
               </div>
               <div className="text-xs text-gray-400 border-t pt-2 mt-2 flex items-start gap-1">
                 <span>📚</span> <span className="leading-tight">{item.citation}</span>
               </div>
            </div>
          ))}
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