import React, { useEffect, useState, useRef } from 'react';
import { Network, Sparkles, RefreshCw, Layers, ArrowRight, Info, Search } from 'lucide-react';
import { fetchKnowledgeGraph, type KnowledgeGraphResponse, type KnowledgeGraphNode } from '../services/api';

interface KnowledgeGraphViewProps {
  onSelectEntityQuery?: (query: string) => void;
}

interface VisualNode extends KnowledgeGraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  'Core Platform': '#818cf8', // Indigo
  'Voice AI': '#fb7185',      // Rose
  'LLM Synthesis': '#c084fc', // Purple
  'Knowledge Base': '#34d399',// Emerald
  'Vector Search': '#38bdf8', // Sky
  'Lexical Search': '#2dd4bf',// Teal
  'Score Fusion': '#f472b6',  // Pink
  'Precision Tuning': '#a78bfa', // Violet
  'Ingestion': '#fb923c',     // Orange
  'Safety & PII': '#f87171',  // Red
  'Self-Reflection': '#e879f9', // Fuchsia
  'Hackathon': '#facc15',     // Yellow
  'Geography': '#4ade80',     // Green
  'Economics': '#60a5fa',     // Blue
  'General': '#94a3b8'        // Slate
};

export const KnowledgeGraphView: React.FC<KnowledgeGraphViewProps> = ({ onSelectEntityQuery }) => {
  const [data, setData] = useState<KnowledgeGraphResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<VisualNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<VisualNode | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const visualNodesRef = useRef<VisualNode[]>([]);
  const draggedNodeRef = useRef<VisualNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Mutable refs to prevent stale closure inside the continuous requestAnimationFrame loop
  const dataRef = useRef<KnowledgeGraphResponse | null>(null);
  const selectedCategoryRef = useRef<string>('All');
  const searchQueryRef = useRef<string>('');
  const selectedNodeRef = useRef<VisualNode | null>(null);
  const hoveredNodeRef = useRef<VisualNode | null>(null);

  // Synchronize state changes to mutable refs
  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  useEffect(() => {
    selectedCategoryRef.current = selectedCategory;
  }, [selectedCategory]);

  useEffect(() => {
    searchQueryRef.current = searchQuery;
  }, [searchQuery]);

  useEffect(() => {
    selectedNodeRef.current = selectedNode;
  }, [selectedNode]);

  useEffect(() => {
    hoveredNodeRef.current = hoveredNode;
  }, [hoveredNode]);

  const loadGraph = () => {
    setLoading(true);
    fetchKnowledgeGraph()
      .then((res) => {
        setData(res);
        dataRef.current = res;
        initSimulation(res);
      })
      .catch((err) => console.error("Error fetching knowledge graph:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadGraph();
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const handleCategoryClick = (cat: string) => {
    setSelectedCategory(cat);
    selectedCategoryRef.current = cat;

    if (cat === 'All') {
      return;
    }

    // Auto-select and focus the first node belonging to this category
    const matchingNode = visualNodesRef.current.find(n => n.category === cat);
    if (matchingNode) {
      setSelectedNode(matchingNode);
      selectedNodeRef.current = matchingNode;
    }
  };

  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    searchQueryRef.current = query;

    if (!query.trim()) return;

    // Auto-select matching node if exact or prefix match
    const matchingNode = visualNodesRef.current.find(
      n => n.label.toLowerCase().includes(query.toLowerCase()) || n.id.toLowerCase().includes(query.toLowerCase())
    );
    if (matchingNode) {
      setSelectedNode(matchingNode);
      selectedNodeRef.current = matchingNode;
    }
  };

  const initSimulation = (graphData: KnowledgeGraphResponse) => {
    const width = 800;
    const height = 450;

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    const visualNodes: VisualNode[] = graphData.nodes.map((n, i) => {
      const isJuly = n.id === 'july';
      const angle = (i / graphData.nodes.length) * Math.PI * 2;
      const dist = isJuly ? 0 : 160 + (i % 3) * 45;
      
      const x = width / 2 + Math.cos(angle) * dist;
      const y = height / 2 + Math.sin(angle) * dist;

      return {
        ...n,
        x,
        y,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        radius: isJuly ? 28 : 14 + Math.min(10, (n.degree || 1) * 2),
        color: CATEGORY_COLORS[n.category] || '#818cf8'
      };
    });

    visualNodesRef.current = visualNodes;
    startAnimationLoop();
  };

  const startAnimationLoop = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const simulate = () => {
      const nodes = visualNodesRef.current;
      const width = canvas.width;
      const height = canvas.height;
      const currentCategory = selectedCategoryRef.current;
      const currentSearch = searchQueryRef.current.trim().toLowerCase();
      const currentSelected = selectedNodeRef.current;
      const currentHovered = hoveredNodeRef.current;
      const currentData = dataRef.current;

      // Force simulation: spring to center & node repulsion
      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        if (node === draggedNodeRef.current) continue;

        // Center pull
        const dx = width / 2 - node.x;
        const dy = height / 2 - node.y;
        node.vx += dx * 0.0004;
        node.vy += dy * 0.0004;

        // Node-node repulsion
        for (let j = i + 1; j < nodes.length; j++) {
          const other = nodes[j];
          const rx = other.x - node.x;
          const ry = other.y - node.y;
          const r = Math.sqrt(rx * rx + ry * ry) || 1;
          const minDist = node.radius + other.radius + 35;

          if (r < minDist) {
            const force = (minDist - r) / r * 0.08;
            node.vx -= rx * force;
            node.vy -= ry * force;
            other.vx += rx * force;
            other.vy += ry * force;
          }
        }

        // Apply friction & boundaries
        node.vx *= 0.92;
        node.vy *= 0.92;
        node.x += node.vx;
        node.y += node.vy;

        node.x = Math.max(node.radius + 10, Math.min(width - node.radius - 10, node.x));
        node.y = Math.max(node.radius + 10, Math.min(height - node.radius - 10, node.y));
      }

      // Clear Canvas
      ctx.clearRect(0, 0, width, height);

      // Draw Edges
      if (currentData) {
        currentData.edges.forEach((edge) => {
          const source = nodes.find(n => n.id === edge.source);
          const target = nodes.find(n => n.id === edge.target);
          if (source && target) {
            const isSourceMatching = (currentCategory === 'All' || source.category === currentCategory) &&
                                     (!currentSearch || source.label.toLowerCase().includes(currentSearch));
            const isTargetMatching = (currentCategory === 'All' || target.category === currentCategory) &&
                                     (!currentSearch || target.label.toLowerCase().includes(currentSearch));
            
            const isEdgeFiltered = !isSourceMatching && !isTargetMatching && (currentCategory !== 'All' || currentSearch);

            const isHighlighted =
              (currentSelected && (currentSelected.id === source.id || currentSelected.id === target.id)) ||
              (currentHovered && (currentHovered.id === source.id || currentHovered.id === target.id));

            ctx.save();
            ctx.beginPath();
            ctx.moveTo(source.x, source.y);
            ctx.lineTo(target.x, target.y);

            if (isHighlighted) {
              ctx.strokeStyle = 'rgba(129, 140, 248, 0.85)';
              ctx.lineWidth = 2.5;
            } else if (isEdgeFiltered) {
              ctx.strokeStyle = 'rgba(51, 65, 85, 0.15)';
              ctx.lineWidth = 0.75;
            } else {
              ctx.strokeStyle = 'rgba(99, 102, 241, 0.35)';
              ctx.lineWidth = 1.2;
            }
            ctx.stroke();

            // Draw directional marker on highlighted or active category edges
            if (isHighlighted || (isSourceMatching && isTargetMatching && currentCategory !== 'All')) {
              const mx = (source.x + target.x) / 2;
              const my = (source.y + target.y) / 2;
              ctx.fillStyle = '#818cf8';
              ctx.beginPath();
              ctx.arc(mx, my, isHighlighted ? 3.5 : 2.5, 0, Math.PI * 2);
              ctx.fill();
            }
            ctx.restore();
          }
        });
      }

      // Draw Nodes
      nodes.forEach((node) => {
        const matchesCategory = currentCategory === 'All' || node.category === currentCategory;
        const matchesSearch = !currentSearch || node.label.toLowerCase().includes(currentSearch) || node.id.toLowerCase().includes(currentSearch);
        const isMatched = matchesCategory && matchesSearch;

        const isSelected = currentSelected?.id === node.id;
        const isHovered = currentHovered?.id === node.id;

        ctx.save();
        ctx.globalAlpha = isMatched ? 1.0 : 0.18;

        // Active / Filtered category halo
        if (isMatched && (currentCategory !== 'All' || currentSearch)) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 6, 0, Math.PI * 2);
          ctx.fillStyle = `${node.color}30`;
          ctx.fill();
        }

        // Selection / Hover outer glow
        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 10, 0, Math.PI * 2);
          ctx.fillStyle = `${node.color}45`;
          ctx.fill();
        }

        // Main circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = isSelected || isHovered ? 20 : isMatched && currentCategory !== 'All' ? 12 : 5;
        ctx.fill();

        // Inner core border
        ctx.lineWidth = isSelected ? 3 : isMatched && currentCategory !== 'All' ? 2 : 1.2;
        ctx.strokeStyle = isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.85)';
        ctx.stroke();

        // Label
        ctx.shadowBlur = 0;
        ctx.fillStyle = isMatched ? '#ffffff' : '#64748b';
        ctx.font = node.id === 'july' ? 'bold 12px Inter, sans-serif' : isMatched ? '600 10px Inter, sans-serif' : '400 9px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        const displayLabel = node.label.length > 18 ? node.label.slice(0, 16) + '...' : node.label;
        ctx.fillText(displayLabel, node.x, node.y + node.radius + 12);

        ctx.restore();
      });

      animationFrameRef.current = requestAnimationFrame(simulate);
    };

    simulate();
  };

  // Mouse interaction handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * canvas.width;
    const y = ((e.clientY - rect.top) / rect.height) * canvas.height;

    const clicked = visualNodesRef.current.find(
      n => Math.hypot(n.x - x, n.y - y) <= n.radius + 8
    );

    if (clicked) {
      draggedNodeRef.current = clicked;
      setSelectedNode(clicked);
      selectedNodeRef.current = clicked;
    } else {
      setSelectedNode(null);
      selectedNodeRef.current = null;
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * canvas.width;
    const y = ((e.clientY - rect.top) / rect.height) * canvas.height;

    if (draggedNodeRef.current) {
      draggedNodeRef.current.x = x;
      draggedNodeRef.current.y = y;
      draggedNodeRef.current.vx = 0;
      draggedNodeRef.current.vy = 0;
    } else {
      const hovered = visualNodesRef.current.find(
        n => Math.hypot(n.x - x, n.y - y) <= n.radius + 8
      );
      setHoveredNode(hovered || null);
      hoveredNodeRef.current = hovered || null;
      canvas.style.cursor = hovered ? 'pointer' : 'default';
    }
  };

  const handleMouseUp = () => {
    draggedNodeRef.current = null;
  };

  const categories = data ? ['All', ...data.stats.categories] : ['All'];

  const nodeRelations = selectedNode && data
    ? data.edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
    : [];

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-8 animate-fadeIn">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Network className="w-6 h-6 text-indigo-400" />
            Interactive Knowledge Graph Map
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Entity-relational network topology extracted from MSMARCO-XI, FAISS indexes, and domain policies
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadGraph}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-all cursor-pointer"
            title="Refresh Knowledge Graph"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Control Bar: Search & Category Filter Pills */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 mb-6">
        {/* Search Filter */}
        <div className="relative flex-1 max-w-xs">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search entity node..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full bg-slate-900/90 border border-slate-800 text-xs text-white pl-9 pr-3 py-2 rounded-xl focus:outline-none focus:border-indigo-500 transition-all"
          />
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {categories.slice(0, 7).map((cat) => (
            <button
              key={cat}
              onClick={() => handleCategoryClick(cat)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all cursor-pointer ${
                selectedCategory === cat
                  ? 'bg-indigo-600 text-white shadow'
                  : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Main Canvas & Detail Sidebar Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Canvas */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-4 border border-slate-800 flex flex-col items-center justify-center relative overflow-hidden min-h-[460px]">
          <canvas
            ref={canvasRef}
            width={800}
            height={460}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className="w-full h-auto rounded-xl bg-slate-950/90"
          />

          <div className="absolute bottom-6 left-6 text-[11px] font-mono text-slate-500 pointer-events-none flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
            <span>Drag nodes to explore relations • Click node or category to inspect details</span>
          </div>
        </div>

        {/* Selected Entity Inspector Panel */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Entity Inspector</h3>
              </div>
              {selectedNode && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {selectedNode.type}
                </span>
              )}
            </div>

            {selectedNode ? (
              <div className="space-y-4">
                <div>
                  <h4 className="text-xl font-bold text-white mb-1">{selectedNode.label}</h4>
                  <span className="text-xs text-slate-400 block font-mono">Category: {selectedNode.category}</span>
                </div>

                {/* Relations list */}
                <div>
                  <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">Relational Links ({nodeRelations.length})</h5>
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {nodeRelations.map((rel, rIdx) => {
                      const isSource = rel.source === selectedNode.id;
                      const connectedId = isSource ? rel.target : rel.source;
                      return (
                        <div key={rIdx} className="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80 text-xs">
                          <div className="flex items-center justify-between text-indigo-400 font-mono mb-1">
                            <span className="capitalize">{rel.relation.replace(/_/g, ' ')}</span>
                            <ArrowRight className="w-3 h-3 text-slate-500" />
                          </div>
                          <div className="text-slate-200 font-medium">{connectedId}</div>
                          {rel.details && <div className="text-[11px] text-slate-400 mt-0.5">{rel.details}</div>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-16 text-center text-slate-500">
                <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-xs">Click on any node or category pill to view entity triples & relation provenance.</p>
              </div>
            )}
          </div>

          {/* Action: Ask About This Entity */}
          {selectedNode && onSelectEntityQuery && (
            <div className="pt-4 border-t border-slate-800 mt-4">
              <button
                onClick={() => onSelectEntityQuery(`Tell me about ${selectedNode.label} and how it works.`)}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Ask Voice RAG About "{selectedNode.label}"</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
