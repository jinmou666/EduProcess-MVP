import React, { useCallback, useRef, useState, useMemo } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  ReactFlowProvider,
  MarkerType,
  useReactFlow,
  Panel,
  applyEdgeChanges,
  applyNodeChanges,
  ConnectionMode // 引入连接模式枚举
} from 'reactflow';
import type { Connection, Edge, Node, ReactFlowInstance, NodeChange, EdgeChange } from 'reactflow';
import 'reactflow/dist/style.css';

import MindMapNode from './MindMapNode';

// --- 数据清洗 ---
const transformToSemanticData = (nodes: Node[], edges: Edge[], studentId: string) => {
  const idToLabelMap: Record<string, string> = {};
  const concepts: string[] = [];

  nodes.forEach((node) => {
    const rawLabel = node.data.label || "";
    const label = rawLabel.trim() === "" ? "未命名节点" : rawLabel;
    idToLabelMap[node.id] = label;
    concepts.push(label);
  });

  const connections = edges
    .map((edge) => {
      const sourceLabel = idToLabelMap[edge.source];
      const targetLabel = idToLabelMap[edge.target];
      if (!sourceLabel || !targetLabel) return null;
      const isBiDirectional = edge.data?.isBiDirectional || false;
      return {
        source: sourceLabel,
        target: targetLabel,
        relation: isBiDirectional ? "bi-directional" : "connects_to"
      };
    })
    .filter((item) => item !== null);

  return {
    student_id: studentId,
    concepts: concepts,
    connections: connections as {source: string, target: string, relation: string}[]
  };
};

const initialNodes: Node[] = [
  { id: '1', type: 'mindMap', position: { x: 250, y: 50 }, data: { label: '核心交换机' } },
];

const ConceptMapContent = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const nodeTypes = useMemo(() => ({ mindMap: MindMapNode }), []);

  const [nodes, setNodes] = useNodesState(initialNodes);
  const [edges, setEdges] = useEdgesState([]);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  const { toObject } = useReactFlow();

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [setNodes]
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [setEdges]
  );

  // --- 彻底修复：连线逻辑 ---
  const onConnect = useCallback(
    (params: Connection) => {
      if (params.source === params.target) return; // 禁止自连

      setEdges((eds) => {
        // 1. 寻找反向边 (B -> A)
        // 注意：这里只看 source 和 target 节点 ID，不看 handle ID
        const inverseEdge = eds.find(
          (e) => e.source === params.target && e.target === params.source
        );

        // 2. 寻找重复边 (防止重复添加)
        const duplicate = eds.find(
           (e) => e.source === params.source && e.target === params.target
        );
        if (duplicate) return eds;

        if (inverseEdge) {
          console.log(">>> 闭环检测：升级为双向连接");

          // 移除旧的单向边
          const otherEdges = eds.filter((e) => e.id !== inverseEdge.id);

          // 创建双向边 (保留这次操作的把手位置，或者沿用旧的，这里我们选择保留旧的把手位置以防跳动，或者新建)
          // 为了简单直观，我们创建一个全新的双向边，使用当前的连接点
          const biEdge: Edge = {
            id: `bi_${inverseEdge.source}_${inverseEdge.target}`, // 保持 ID 稳定
            source: inverseEdge.source,
            sourceHandle: inverseEdge.sourceHandle, // 沿用旧边的起点
            target: inverseEdge.target,
            targetHandle: inverseEdge.targetHandle, // 沿用旧边的终点
            type: 'smoothstep',
            animated: false,
            // 双向样式
            style: { stroke: '#7c3aed', strokeWidth: 3 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#7c3aed' },
            markerStart: { type: MarkerType.ArrowClosed, color: '#7c3aed' },
            data: { isBiDirectional: true },
            interactionWidth: 20
          };
          return [...otherEdges, biEdge];

        } else {
          // 3. 正常创建单向边
          // 关键点：必须透传 sourceHandle 和 targetHandle，否则线会乱跳！
          const newEdge: Edge = {
            ...params,
            id: `edge_${params.source}_${params.target}`,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#64748b', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
            data: { isBiDirectional: false },
            interactionWidth: 20
          };
          return addEdge(newEdge, eds);
        }
      });
    },
    [setEdges]
  );

  const onDeleteSelected = useCallback(() => {
    setNodes((nds) => nds.filter((node) => !node.selected));
    setEdges((eds) => eds.filter((edge) => !edge.selected));
  }, [setNodes, setEdges]);

  const onAddNodeBtn = useCallback(() => {
    const id = `node_${+new Date()}`;
    const newNode: Node = {
      id,
      type: 'mindMap',
      position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
      data: { label: '新概念' },
    };
    setNodes((nds) => nds.concat(newNode));
  }, [setNodes]);

  const submitTopology = async () => {
    if (nodes.length < 1) {
      alert("画布为空，请添加节点！");
      return;
    }
    const cleanData = transformToSemanticData(nodes, edges, "STU_FINAL_SUBMISSION");
    const payload = {
      task_id: 1,
      student_id: cleanData.student_id,
      raw_flow_data: toObject(),
      adjacency_list: cleanData.connections
    };
    try {
      const response = await fetch('http://127.0.0.1:8000/topology/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error("后端报错");
      const res = await response.json();
      alert(`提交成功！\n文件已覆盖更新。\nSaved: ${res.saved_file}`);
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="flex h-full w-full font-sans relative">
      <div className="absolute top-4 right-8 z-50 flex gap-3">
          <button
              onClick={onAddNodeBtn}
              className="px-4 py-2 bg-green-600 text-white text-sm font-bold rounded shadow-lg hover:bg-green-700 transition"
          >
              + 添加节点
          </button>
          <button
              onClick={onDeleteSelected}
              className="px-4 py-2 bg-red-500 text-white text-sm font-bold rounded shadow-lg hover:bg-red-600 transition"
          >
              删除选中 (Delete)
          </button>
          <button
              onClick={submitTopology}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-bold rounded shadow-lg hover:bg-indigo-700 transition"
          >
              提交作业
          </button>
      </div>

      <div className="flex-grow h-full w-full bg-gray-50 relative" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode={['Backspace', 'Delete']}
          selectionOnDrag={true}
          panOnScroll={true}
          // 关键设定：自由连接模式
          connectionMode={ConnectionMode.Loose}
        >
          <Controls position="bottom-left" />
          <MiniMap style={{ height: 100 }} zoomable pannable position="bottom-right" />
          <Background gap={20} size={1} />

          <Panel position="top-center" className="bg-yellow-50 text-yellow-800 px-3 py-1 rounded text-xs opacity-90 pointer-events-none border border-yellow-200">
             💡 提示：点击连线变色后 → 按“删除选中”按钮
          </Panel>

        </ReactFlow>
      </div>
    </div>
  );
};

export default function ConceptMap() {
  return (
    <ReactFlowProvider>
      <ConceptMapContent />
    </ReactFlowProvider>
  );
}