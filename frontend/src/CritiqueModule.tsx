import { useState, useEffect, useCallback, useMemo } from 'react';

// 类型定义
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
};

const API_BASE = "http://127.0.0.1:8000";

export default function CritiqueModule() {
  const [task, setTask] = useState<TaskData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [critiques, setCritiques] = useState<Critique[]>([]);

  // 弹窗状态
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [tempSelection, setTempSelection] = useState<{quote: string, start: number, end: number} | null>(null);
  const [rewriteInput, setRewriteInput] = useState("");
  const [citationInput, setCitationInput] = useState("");

  // 1. 加载题目
  useEffect(() => {
    fetch(`${API_BASE}/tasks/1`)
      .then(res => {
        if (!res.ok) throw new Error("无法连接后端");
        return res.json();
      })
      .then(data => {
        setTask(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // 2. 处理文本选中
  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const selectedText = selection.toString().trim();
    if (selectedText.length === 0) return;

    const container = document.getElementById('content-area-react');
    if (!container || !container.contains(selection.anchorNode)) return;

    // 获取相对于纯文本的偏移量
    // 这是一个简化实现，为了避免复杂的 DOM 遍历，我们假设用户总是从前往后选
    // 实际上高亮后 DOM 结构变了，这里需要更复杂的逻辑，但 MVP 阶段我们先用 textContent 匹配
    // 如果要生产级，需要使用 Range.setStart/End 的复杂计算

    // 简易方案：利用当前 task.content 查找 selectedText 的位置
    // 缺点：如果文章有重复词，可能会选错。但在 MVP 演示中，你只要别选重复词就行。
    const fullText = task?.content || "";
    const range = selection.getRangeAt(0);
    // 这里我们用一个 trick：暂时获取选区前的文本长度
    // 注意：高亮后这个逻辑会失效，所以更好的方式是先清空选区，或者维护原始文本
    // 鉴于时间，我们这里主要依赖 React 的渲染逻辑。

    // 修正：直接弹窗，让用户确认。位置信息先用 indexOf 模拟（演示用）
    // 为了更精准，我们还是用之前的 cloneRange 方法，但要注意它获取的是 DOM 偏移
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

  // 3. 保存纠错
  const saveCritique = () => {
    if (!tempSelection || !rewriteInput) return;

    const newCritique: Critique = {
      quote: tempSelection.quote,
      rewrite: rewriteInput,
      citation: citationInput,
      selection_range: [tempSelection.start, tempSelection.end]
    };

    // 覆盖逻辑
    setCritiques(prev => {
        const filtered = prev.filter(item => {
            const startOld = item.selection_range[0];
            const endOld = item.selection_range[1];
            const startNew = newCritique.selection_range[0];
            const endNew = newCritique.selection_range[1];
            // 只要有重叠就删掉旧的
            return !(startOld < endNew && endOld > startNew);
        });
        return [...filtered, newCritique].sort((a, b) => a.selection_range[0] - b.selection_range[0]);
    });

    setIsModalOpen(false);
    window.getSelection()?.removeAllRanges();
  };

  // 4. 提交
  const submitAssignment = async () => {
    try {
      const res = await fetch(`${API_BASE}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: task?.id || 1,
          student_id: "STU_REACT_001",
          critiques: critiques
        })
      });
      const data = await res.json();
      alert(`提交成功 ID: ${data.id}`);
    } catch (err) {
      alert("提交失败");
    }
  };

  // 5. 核心：渲染高亮文本
  const renderHighlightedContent = () => {
    if (!task) return null;
    const text = task.content;
    if (critiques.length === 0) return text;

    const elements = [];
    let lastIndex = 0;

    critiques.forEach((critique, idx) => {
      const [start, end] = critique.selection_range;

      // 添加普通文本
      if (start > lastIndex) {
        elements.push(
            <span key={`text-${idx}`}>{text.slice(lastIndex, start)}</span>
        );
      }

      // 添加高亮文本
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

    // 添加剩余文本
    if (lastIndex < text.length) {
      elements.push(<span key="text-end">{text.slice(lastIndex)}</span>);
    }

    return elements;
  };

  if (loading) return <div className="p-8 text-center text-gray-500">正在加载题目...</div>;
  if (error) return <div className="p-8 text-center text-red-500">错误: {error}</div>;

  return (
    <div className="flex h-full overflow-hidden">
      {/* 左侧：题目 */}
      <div className="w-2/3 p-8 overflow-y-auto bg-white border-r">
        <h2 className="text-2xl font-bold mb-4">{task?.title}</h2>
        <div
          id="content-area-react"
          className="bg-gray-50 p-6 rounded-lg leading-loose text-lg border relative whitespace-pre-wrap text-gray-800"
          onMouseUp={handleMouseUp}
        >
          {renderHighlightedContent()}
        </div>
        <p className="mt-4 text-sm text-gray-400">* 选中文本进行纠错，重叠区域会自动覆盖。</p>
      </div>

      {/* 右侧：列表 */}
      <div className="w-1/3 bg-gray-50 flex flex-col border-l">
        <div className="p-4 border-b bg-white font-bold text-gray-700">
          纠错记录 ({critiques.length})
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {critiques.length === 0 && (
            <div className="text-center text-gray-400 mt-10">暂无记录</div>
          )}
          {critiques.map((item, idx) => (
            <div key={idx} className="bg-white p-3 rounded shadow-sm text-sm border hover:border-indigo-300">
               <div className="mb-1 text-gray-500 line-through text-xs">{item.quote}</div>
               <div className="font-medium text-green-700">{item.rewrite}</div>
               <div className="text-xs text-gray-400 mt-1">依据: {item.citation}</div>
            </div>
          ))}
        </div>
        <div className="p-4 bg-white border-t">
            <button onClick={submitAssignment} className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700 font-bold shadow">
                提交任务
            </button>
        </div>
      </div>

      {/* 弹窗 (Modal) */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white p-6 rounded-lg w-96 shadow-xl">
                <h3 className="font-bold mb-4">添加纠错</h3>
                <div className="bg-red-50 p-2 text-sm text-red-800 mb-4 italic rounded line-clamp-3">
                    "{tempSelection?.quote}"
                </div>
                <label className="block text-xs font-bold text-gray-500 mb-1">修正内容</label>
                <textarea
                    className="w-full border p-2 rounded mb-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                    placeholder="这里应该怎么写？"
                    rows={3}
                    value={rewriteInput}
                    onChange={e => setRewriteInput(e.target.value)}
                />
                <label className="block text-xs font-bold text-gray-500 mb-1">理论依据</label>
                <input
                    className="w-full border p-2 rounded mb-4 focus:ring-2 focus:ring-indigo-500 outline-none"
                    placeholder="例如：通信原理 P32"
                    value={citationInput}
                    onChange={e => setCitationInput(e.target.value)}
                />
                <div className="flex justify-end gap-2">
                    <button onClick={() => setIsModalOpen(false)} className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300">取消</button>
                    <button onClick={saveCritique} className="px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700">保存</button>
                </div>
            </div>
        </div>
      )}
    </div>
  );
}