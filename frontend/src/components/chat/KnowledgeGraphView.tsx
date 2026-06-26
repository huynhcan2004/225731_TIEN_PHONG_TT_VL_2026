import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import { ArrowLeft, Share2, Download } from 'lucide-react';
import { useLanguageTheme } from '../../context/LanguageThemeContext';

const ForceGraph: any = ForceGraph2D;

const KnowledgeGraphView: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { graphData } = location.state || { graphData: { nodes: [], links: [] } };
  const { currentBg, t } = useLanguageTheme();

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden text-slate-100 relative" style={{ backgroundColor: currentBg.bodyBg }}>
      
      {/* Cyber Grid Background */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none z-0" 
           style={{ backgroundImage: 'radial-gradient(#1b8961 1px, transparent 1px)', backgroundSize: '32px 32px' }}>
      </div>

      {/* Header điều khiển */}
      <header className="h-16 border-b border-emerald-500/10 flex items-center justify-between px-6 backdrop-blur-md z-10" style={{ backgroundColor: currentBg.panelBg + 'cc' }}>
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="p-2 text-slate-400 hover:text-emerald-400 hover:bg-emerald-950/20 rounded-lg transition-all border border-transparent hover:border-emerald-500/10">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-white font-black tracking-tight text-sm sm:text-base">
            {t('graphTitle')} <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-amber-400">GRAPH-RAG</span>
          </h1>
        </div>
        
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-4 py-2 bg-[#08150f] text-slate-300 border border-emerald-500/15 rounded-xl text-xs font-bold hover:bg-emerald-950/40 hover:text-emerald-300 transition-all cursor-pointer">
             <Share2 size={14} /> {t('share')}
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-emerald-700 text-white rounded-xl text-xs font-bold hover:from-emerald-500 hover:to-emerald-600 shadow-lg shadow-emerald-950/50 border border-emerald-400/25 active:scale-98 transition-all cursor-pointer">
             <Download size={14} /> {t('exportData')}
          </button>
        </div>
      </header>

      {/* Đồ thị Full-screen */}
      <main className="flex-1 relative z-10">
        <ForceGraph 
          graphData={graphData}
          nodeLabel="name"
          nodeAutoColorBy="group"
          nodeRelSize={8}
          linkColor={() => 'rgba(27, 137, 97, 0.2)'}
          backgroundColor={currentBg.bodyBg}
          // Tăng các thông số cho không gian rộng
          d3Force={(force: any, name: string) => {
            if (name === 'charge') force.strength(-300);
            if (name === 'link') force.distance(100);
          }}
          nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const label = node.name;
            const fontSize = 14/globalScale;
            ctx.font = `${fontSize}px Inter, sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = node.color;
            ctx.fillText(label, node.x, node.y + 10);
            
            // Vẽ vòng tròn node
            ctx.beginPath();
            ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
            ctx.fill();
          }}
        />
        
        {/* Panel hướng dẫn nhỏ ở góc */}
        <div className="absolute bottom-6 left-6 p-4 border border-emerald-500/20 rounded-2xl text-[10px] text-emerald-400/70 font-mono space-y-1 backdrop-blur-sm shadow-lg shadow-black/20" style={{ backgroundColor: currentBg.panelBg + 'd9' }}>
           <p className="font-bold text-amber-400/80">{t('guidanceTitle')}</p>
           <p>{t('guidanceZoom')}</p>
           <p>{t('guidanceDrag')}</p>
           <p>{t('guidanceRealtime')}</p>
        </div>
      </main>
    </div>
  );
};

export default KnowledgeGraphView;