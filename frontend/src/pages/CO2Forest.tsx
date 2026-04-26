import { useState, useEffect } from 'react';
import { getDashboard } from '../api/kpiApi';

// --- CONFIG & DATA ---
const ESG_LEVELS = [
  { label: '< 50 kg — Excellent', color: '#2ecc71', min: 0, max: 50 },
  { label: '50–100 kg — Good', color: '#7bc632', min: 50, max: 100 },
  { label: '100–200 kg — Warning', color: '#e8c020', min: 100, max: 200 },
  { label: '200–350 kg — Critical', color: '#e07010', min: 200, max: 350 },
  { label: '> 350 kg — Danger', color: '#c0392b', min: 350, max: 1000 },
];

const leafDark    = ['#1a8040','#4a8a10','#a08010','#a04808','#7a2010'];
const leafMid     = ['#2ecc71','#7bc632','#e8c020','#e07010','#c0392b'];
const leafLight   = ['#80f0a8','#b8e860','#f8e060','#f8a060','#f07060'];
const leafHi      = ['#c0ffdc','#dcf5a0','#fff0a0','#ffd0a0','#ffc0b0'];
const trunkLight  = ['#c8883a','#be7a2e','#b87828','#a06020','#705040'];
const trunkMid    = ['#9a6020','#8a5018','#886010','#784010','#503828'];
const trunkDark   = ['#6a3a10','#5a2e0a','#584008','#502808','#382418'];

// --- SVG HELPERS ---
const Leaf = ({ cx, cy, w, h, rot, fill, hiCol, op = 1 }: any) => {
  const r = rot * Math.PI / 180;
  const cos = Math.cos(r), sin = Math.sin(r);
  const pt = (lx: number, ly: number) => `${(cx + lx * cos - ly * sin).toFixed(2)},${(cy + lx * sin + ly * cos).toFixed(2)}`;
  const hw = w / 2, hh = h / 2;
  const path = `M ${pt(0, hh)} C ${pt(hw * 0.95, hh * 0.9)} ${pt(hw * 1.0, -hh * 0.2)} ${pt(0, -hh)} C ${pt(-hw * 1.0, -hh * 0.2)} ${pt(-hw * 0.95, hh * 0.9)} ${pt(0, hh)} Z`;
  const hlx = cx + (-hw * 0.22) * cos - (-hh * 0.25) * sin;
  const hly = cy + (-hw * 0.22) * sin + (-hh * 0.25) * cos;

  return (
    <g opacity={op}>
      <path d={path} fill={fill} filter="url(#leafShadow)" />
      <path d={path} fill={`url(#leafGrad_${fill.replace('#', '')})`} opacity={0.5} />
      <line x1={pt(0, hh * 0.7).split(',')[0]} y1={pt(0, hh * 0.7).split(',')[1]} x2={pt(0, -hh * 0.7).split(',')[0]} y2={pt(0, -hh * 0.7).split(',')[1]} stroke={trunkDark[0]} strokeWidth="0.5" opacity={0.3} />
      <ellipse cx={hlx.toFixed(2)} cy={hly.toFixed(2)} rx={(hw * 0.28).toFixed(2)} ry={(hh * 0.18).toFixed(2)} transform={`rotate(${rot}, ${hlx.toFixed(2)}, ${hly.toFixed(2)})`} fill={hiCol} opacity={0.55} />
    </g>
  );
};

const Trunk = ({ x, y, w, h, lv }: any) => {
  const tl = trunkLight[lv], tm = trunkMid[lv], td = trunkDark[lv];
  const bx = x, by = y, tx = x, ty = y - h;
  const tw2 = w * 0.28, bw2 = w * 0.5;
  return (
    <g>
      <defs>
        <linearGradient id={`trunk${lv}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor={td} /><stop offset="20%" stopColor={tm} /><stop offset="50%" stopColor={tl} /><stop offset="80%" stopColor={tm} /><stop offset="100%" stopColor={td} />
        </linearGradient>
      </defs>
      <ellipse cx={bx} cy={by + 3} rx={bw2 * 1.1} ry={bw2 * 0.28} fill="rgba(0,0,0,0.28)" />
      <path d={`M${bx - bw2} ${by} C${bx - bw2 * 1.05} ${by - h * 0.35} ${bx - tw2 * 1.1} ${by - h * 0.7} ${tx - tw2} ${ty} L${tx + tw2} ${ty} C${bx + tw2 * 1.1} ${by - h * 0.7} ${bx + bw2 * 1.05} ${by - h * 0.35} ${bx + bw2} ${by} Z`} fill={`url(#trunk${lv})`} />
    </g>
  );
};

const LeafCloud = ({ cx, cy, rx, ry, count, lv, seedOffset = 0 }: any) => {
  const rng = (i: number, salt: number) => {
    const x = Math.sin(i * 127.1 + salt * 311.7 + seedOffset * 74.3) * 43758.5453;
    return x - Math.floor(x);
  };
  const leaves = [];
  for (let i = 0; i < count; i++) {
    const angle = rng(i, 1) * Math.PI * 2;
    const r = Math.sqrt(rng(i, 2));
    leaves.push({ lx: cx + Math.cos(angle) * rx * r, ly: cy + Math.sin(angle) * ry * r, i });
  }
  leaves.sort((a, b) => a.ly - b.ly);
  return (
    <g>
      {/* Background Blobs for Volume */}
      <ellipse cx={cx} cy={cy} rx={rx * 1.2} ry={ry * 1.2} fill={leafDark[lv]} opacity={0.4} filter="blur(8px)" />
      <ellipse cx={cx} cy={cy - 10} rx={rx * 0.8} ry={ry * 0.8} fill={leafMid[lv]} opacity={0.3} filter="blur(5px)" />
      
      {leaves.map(({ lx, ly, i }) => {
        const w = 12 + rng(i, 5) * 12;
        const shade = rng(i, 8);
        const fill = shade < 0.3 ? leafDark[lv] : shade < 0.7 ? leafMid[lv] : leafLight[lv];
        return <Leaf key={i} cx={lx} cy={ly} w={w} h={w * 0.8} rot={rng(i, 7) * 360} fill={fill} hiCol={leafHi[lv]} op={0.9} />;
      })}
    </g>
  );
};

// --- MAIN COMPONENT ---
export default function CO2Forest() {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    getDashboard().then(r => {
      const rankings = r.data.rankings || [];
      const enriched = rankings.map((inst: any) => ({
        ...inst,
        co2: Math.floor(400 - (inst.overall_score * 3.5)),
        energy: Math.floor(Math.random() * 40 + 50),
        recycle: Math.floor(Math.random() * 50 + 40)
      })).sort((a: any, b: any) => a.co2 - b.co2);
      setData(enriched);
    });
  }, []);

  const getLevel = (co2: number) => {
    if (co2 < 50) return 0;
    if (co2 < 100) return 1;
    if (co2 < 200) return 2;
    if (co2 < 350) return 3;
    return 4;
  };

  return (
    <div className="scene animate-fade-in" style={{ background: '#0c1a10', minHeight: '100vh', padding: '24px 16px', borderRadius: '24px' }}>
      <style>{`
        .scene { font-family: 'DM Mono', monospace; color: rgba(255,255,255,0.92); }
        .header h1 { font-family: 'Fraunces', serif; font-size: 28px; margin: 0; }
        .legend { display: flex; gap: 16px; flex-wrap: wrap; margin: 24px 0; padding: 12px; background: rgba(255,255,255,0.04); border-radius: 8px; }
        .leg-item { display: flex; align-items: center; gap: 8px; font-size: 11px; color: rgba(255,255,255,0.4); }
        .forest { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 50px 30px; padding: 60px 20px; background: #14301a; border-radius: 12px; border: 1px solid rgba(255,255,255,0.06); }
        .tree-card { display: flex; flex-direction: column; align-items: center; cursor: pointer; transition: transform 0.2s; position: relative; }
        .tree-card:hover { transform: translateY(-8px); }
        .tree-wrap { width: 140px; height: 160px; position: relative; }
        .inst-name { font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 15px; text-align: center; font-weight: 600; font-family: 'Fraunces', serif; }
        .co2-badge { margin-top: 8px; font-size: 10px; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-family: 'DM Mono', monospace; }
        @keyframes sway { from { transform: rotate(-1.5deg); } to { transform: rotate(1.5deg); } }
        .sway { transform-origin: bottom center; animation: sway 4s ease-in-out infinite alternate; }
      `}</style>

      <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h1 style={{ color: 'green' }}>CO₂ Forest</h1>
        <p style={{ fontSize: 10, opacity: 0.4, textTransform: 'uppercase' }}>University of Carthage · ESG Overview 2024–25</p>
      </div>

      <div className="legend">
        {ESG_LEVELS.map(l => (
          <div key={l.label} className="leg-item">
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: l.color, boxShadow: `0 0 8px ${l.color}` }} />
            {l.label}
          </div>
        ))}
      </div>

      <div className="forest">
        {data.map((inst, idx) => {
          const lv = getLevel(inst.co2);
          const col = ESG_LEVELS[lv].color;
          return (
            <div key={inst.institution_id} className="tree-card">
              <div className="tree-wrap sway" style={{ animationDelay: `${idx * 0.3}s` }}>
                <svg viewBox="0 0 110 150" xmlns="http://www.w3.org/2000/svg" style={{ overflow: 'visible' }}>
                  <defs>
                    <filter id="leafShadow"><feDropShadow dx="1" dy="2" stdDeviation="1" floodOpacity="0.3"/></filter>
                    {[leafDark[lv], leafMid[lv], leafLight[lv]].map(f => (
                      <radialGradient key={f} id={`leafGrad_${f.replace('#','')}`} cx="35%" cy="35%" r="65%">
                        <stop offset="0%" stopColor={leafHi[lv]} stopOpacity="0.7"/><stop offset="100%" stopColor={f} stopOpacity="0"/>
                      </radialGradient>
                    ))}
                  </defs>
                  <LeafCloud cx={55} cy={lv < 3 ? 55 : 80} rx={lv < 2 ? 45 : 25} ry={lv < 2 ? 35 : 20} count={lv === 0 ? 120 : lv === 1 ? 80 : lv === 2 ? 40 : 15} lv={lv} seedOffset={idx} />
                  <Trunk x={55} y={145} w={18} h={lv < 2 ? 45 : 35} lv={lv} />
                </svg>
              </div>
              <div className="inst-name">{inst.institution_name}</div>
              <div className="co2-badge" style={{ background: `${col}22`, color: col, border: `1px solid ${col}44`, boxShadow: `0 0 10px ${col}11` }}>
                {inst.co2} kg CO₂
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}