import React, { useCallback } from 'react';
import { Handle, Position, useReactFlow, type NodeProps } from 'reactflow';

export default function MindMapNode({ id, data, selected }: NodeProps) {
  const { setNodes } = useReactFlow();

  const onChange = useCallback((evt: React.ChangeEvent<HTMLInputElement>) => {
    const newLabel = evt.target.value;
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === id) {
          return { ...node, data: { ...node.data, label: newLabel } };
        }
        return node;
      })
    );
  }, [id, setNodes]);

  const onDelete = useCallback(() => {
    setNodes((nds) => nds.filter((node) => node.id !== id));
  }, [id, setNodes]);

  // 选中样式
  const borderClass = selected ? "border-indigo-500 ring-2 ring-indigo-200" : "border-stone-400";

  // Handle 样式：大一点，容易点中
  const handleStyle = { width: '10px', height: '10px', background: '#78716c' };

  return (
    <div className={`relative group shadow-md rounded-md bg-white border-2 min-w-[150px] transition-all ${borderClass}`}>

      {/* 关键修改：
         1. id="xxx" : 必须唯一，告诉 React Flow 这条线连的是哪个具体位置
         2. type="source" : 配合 ConceptMap 里的 connectionMode="loose"，允许任意点互连
      */}

      {/* 上 */}
      <Handle type="source" position={Position.Top} id="top" style={handleStyle} className="hover:!bg-indigo-500" />

      {/* 右 */}
      <Handle type="source" position={Position.Right} id="right" style={handleStyle} className="hover:!bg-indigo-500" />

      {/* 下 */}
      <Handle type="source" position={Position.Bottom} id="bottom" style={handleStyle} className="hover:!bg-indigo-500" />

      {/* 左 */}
      <Handle type="source" position={Position.Left} id="left" style={handleStyle} className="hover:!bg-indigo-500" />

      <div className="flex items-center p-3">
        <input
          value={data.label}
          onChange={onChange}
          className="nodrag text-center w-full text-sm font-bold text-gray-700 outline-none bg-transparent cursor-text"
          placeholder="输入名称"
        />
      </div>

      <button
        onClick={onDelete}
        className="absolute -top-3 -right-3 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer shadow-sm z-50 hover:bg-red-600"
        title="删除节点"
      >
        ✕
      </button>
    </div>
  );
}