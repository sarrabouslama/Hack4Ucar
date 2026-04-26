import { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';
import { getDashboard, getAlerts, getAtRisk, explainWhy, getHistory } from '../api/kpiApi';

// ─── Types ────────────────────────────────────────────────────────────────────
interface RankRow { rank: number; institution_name: string; institution_code: string; institution_id: string; success_rate: number; dropout_rate: number; attendance_rate: number; overall_score: number; badges: string[]; }
interface ConsolidatedKPI { indicator: string; avg_value: number; min_value: number; max_value: number; total_institutions: number; }
interface AlertItem { id: string; institution_id: string; institution_name: string; severity: string; indicator: string; actual_value: number; threshold_value: number; message: string; xai_explanation: string; xai_factors: Record<string, number>; }

// ─── KPI Card ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, unit, color, icon, sub }: { label: string; value: number; unit?: string; color: string; icon: string; sub?: string }) {
  return (
    <div className="card kpi-card">
      <div className="glow" style={{ background: color }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: 22 }}>{icon}</span>
        <span className="kpi-label" style={{ textAlign: 'right' }}>{label}</span>
      </div>
      <div className="kpi-value" style={{ color }}>{value?.toFixed(1)}<span style={{ fontSize: 16, marginLeft: 2 }}>{unit}</span></div>
      {sub && <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

// ─── Why Modal ────────────────────────────────────────────────────────────────
function WhyModal({ institutionId, indicator, alertMsg, onClose }: { institutionId: string; indicator: string; alertMsg?: string; onClose: () => void }) {
  const [xaiContent, setXaiContent] = useState<{ title: string; body: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const handleWhy = (id: string, indicator: string) => {
    explainWhy(id, indicator)
      .then(res => {
        const data = res.data;
        const factorsHtml = Object.entries(data.factors || {}).map(([f, v]: [string, any]) => `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; background:rgba(255,255,255,0.03); padding:8px; border-radius:6px;">
            <span style="font-size:12px; color:var(--muted)">${f.replace('_', ' ')}</span>
            <div style="flex:1; height:4px; background:var(--border); margin:0 15px; border-radius:2px; overflow:hidden;">
              <div style="width:${(v * 100)}%; height:100%; background:var(--primary);"></div>
            </div>
            <span style="font-weight:bold; font-size:12px;">${(v * 100).toFixed(0)}%</span>
          </div>
        `).join('');

        const content = `
          <div style="color:var(--text); line-height:1.6;">
            ${alertMsg ? `
            <div style="margin-bottom:15px; padding:12px; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:8px; color:#ef4444; font-size:14px; display:flex; align-items:center; gap:10px;">
              <span>🚨</span> <strong>Diagnostic :</strong> ${alertMsg}
            </div>` : ''}

            <div style="margin-bottom:20px; padding:15px; background:rgba(59,130,246,0.1); border-left:4px solid var(--primary); border-radius:4px;">
              ${data.explanation.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}
            </div>
            
            <div style="margin-bottom:20px;">
              <h4 style="margin-bottom:12px; font-size:14px; color:var(--primary); display:flex; align-items:center; gap:8px;">
                🔗 Facteurs Contributifs (XAI)
              </h4>
              ${factorsHtml || '<p style="color:var(--muted); font-size:12px;">Analyse des corrélations en cours...</p>'}
            </div>

            <div style="padding:15px; background:rgba(16,185,129,0.1); border-radius:8px; border:1px dashed #10b981;">
              <h4 style="margin:0 0 8px 0; font-size:13px; color:#10b981;">💡 Recommandation Stratégique</h4>
              <p style="margin:0; font-size:13px;">${data.recommendation}</p>
            </div>
          </div>
        `;

        setXaiContent({
          title: `Analyse IA — ${data.institution_name}`,
          body: content
        });
      })
      .catch((err) => {
        console.error("XAI Error:", err);
        setXaiContent({
          title: "Analyse IA",
          body: `
            <div style="margin-bottom:15px; padding:12px; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:8px; color:#ef4444; font-size:14px; display:flex; align-items:center; gap:10px;">
              <span>🚨</span> <strong>Diagnostic :</strong> ${alertMsg || 'Donnée hors seuil détectée'}
            </div>
          `
        });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    handleWhy(institutionId, indicator);
  }, [institutionId, indicator]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3>🔍 Pourquoi ? — {indicator}</h3>
          <button className="btn btn-ghost" style={{ padding: '4px 10px' }} onClick={onClose}>✕</button>
        </div>
        {loading ? (
          <div className="loading-center" style={{ padding: '60px 0' }}><div className="spinner" /></div>
        ) : (
          <div dangerouslySetInnerHTML={{ __html: xaiContent?.body || '' }} />
        )}
      </div>
    </div>
  );
}

// ─── History Chart Modal ──────────────────────────────────────────────────────
function HistoryModal({ institutionId, institutionName, indicator, onClose }: { institutionId: string; institutionName: string; indicator: string; onClose: () => void }) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getHistory(institutionId, indicator)
      .then(r => setData(r.data.history || []))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 640 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3>📈 {institutionName} — {indicator}</h3>
          <button className="btn btn-ghost" style={{ padding: '4px 10px' }} onClick={onClose}>✕</button>
        </div>
        {loading ? <div className="loading-center"><div className="spinner" /></div> : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fill: 'var(--muted)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--muted)', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }} />
              <Line type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={2} dot={{ r: 3, fill: 'var(--primary)' }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function UcarDashboard({ activeTab, setActiveTab, refreshTrigger }: {
  activeTab: 'overview' | 'ranking' | 'alerts' | 'predictions',
  setActiveTab: (t: 'overview' | 'ranking' | 'alerts' | 'predictions') => void,
  refreshTrigger: number
}) {
  const [dashboard, setDashboard] = useState<any>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [atRisk, setAtRisk] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [whyModal, setWhyModal] = useState<{ id: string; indicator: string; alertMsg?: string } | null>(null);
  const [historyModal, setHistoryModal] = useState<{ id: string; name: string; indicator: string } | null>(null);
  const [drillDown, setDrillDown] = useState<any>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([getDashboard(), getAlerts(), getAtRisk()])
      .then(([d, a, r]) => {
        setDashboard(d.data || {});
        const alertsData = a.data?.alerts || (Array.isArray(a.data) ? a.data : []);
        setAlerts(alertsData);
        setAtRisk(r.data?.institutions || []);
      })
      .catch(err => console.error("Erreur API:", err))
      .finally(() => setLoading(false));
  }, [refreshTrigger]);

  if (loading) return (
    <div>
      <div className="header"><div><h1>Dashboard UCAR</h1><p>Chargement des données...</p></div></div>
      <div className="loading-center"><div className="spinner" /></div>
    </div>
  );

  const kpis: ConsolidatedKPI[] = dashboard?.consolidated_kpis || [];
  const rankings: RankRow[] = dashboard?.rankings || [];
  const getKpi = (name: string) => kpis.find(k => k.indicator === name);

  const KPI_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    success_rate: { icon: '🎓', color: '#10b981', label: 'Taux de Réussite Moy.' },
    dropout_rate: { icon: '⚠️', color: '#ef4444', label: 'Taux d\'Abandon Moy.' },
    attendance_rate: { icon: '📅', color: '#3b82f6', label: 'Taux de Présence Moy.' },
    exam_pass_rate: { icon: '📝', color: '#8b5cf6', label: 'Taux Passage Examens' },
    grade_repetition_rate: { icon: '🔄', color: '#f97316', label: 'Redoublement Moy.' },
  };

  return (
    <div>
      <div className="animate-fade-in">
        {/* Header */}
        <div className="card" style={{ marginBottom: 32, border: 'none', background: 'var(--navy)', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ color: 'var(--gold-light)', fontSize: 28, marginBottom: 4 }}>🔵 Dashboard UCAR Central</h1>
            <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: 14 }}>
              {dashboard?.total_institutions || 0} établissements · {dashboard?.active_alerts_count || 0} alertes actives · Top : <strong>{dashboard?.top_performer || 'N/A'}</strong>
            </p>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {(dashboard?.critical_alerts_count || 0) > 0 && (
              <div className="badge badge-critical" style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444' }}>
                🚨 {dashboard.critical_alerts_count} critique(s)
              </div>
            )}
            <div style={{ fontStyle: 'italic', fontSize: 12, opacity: 0.7 }}>
              {new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
            </div>
          </div>
        </div>

        <div className="page">
          {/* Tabs */}
          <div className="tabs" style={{ position: 'relative', zIndex: 10 }}>
            {([['overview', '📊 Vue d\'ensemble'], ['ranking', '🏆 Classement'], ['alerts', '🚨 Alertes']] as const).map(([k, l]) => (
              <button
                key={k}
                className={`tab-btn ${activeTab === k ? 'active' : ''}`}
                onClick={() => {
                  console.log("Changement d'onglet vers:", k);
                  setActiveTab(k);
                }}
              >
                {l}
              </button>
            ))}
          </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <>
              {/* KPI Summary Cards */}
              <div className="section-title">Indicateurs académiques consolidés</div>
              <div className="grid-5" style={{ marginBottom: 28, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '15px' }}>
                {['success_rate', 'dropout_rate', 'attendance_rate', 'exam_pass_rate', 'grade_repetition_rate'].map(ind => {
                  const kpi = getKpi(ind);
                  const cfg = KPI_CONFIG[ind];
                  return kpi ? (
                    <KpiCard key={ind}
                      label={cfg.label} value={kpi.avg_value} unit="%" color={cfg.color} icon={cfg.icon}
                      sub={`Min: ${kpi.min_value}% · Max: ${kpi.max_value}%`}
                    />
                  ) : null;
                })}
              </div>

              <div className="grid-2">
                {/* Bar chart comparison */}
                <div className="card">
                  <div className="section-title">Taux de réussite par institution</div>
                  <div style={{ width: '100%', height: 250 }}>
                    <BarChart width={450} height={200} data={rankings} layout="vertical" margin={{ left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 11 }} />
                      <YAxis type="category" dataKey="institution_name" width={100} tick={{ fill: 'var(--muted)', fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }} />
                      <Bar dataKey="success_rate" radius={[0, 4, 4, 0]}>
                        {rankings.map(r => (
                          <Cell key={r.institution_code} fill={r.success_rate >= 75 ? '#10b981' : r.success_rate >= 60 ? '#3b82f6' : '#ef4444'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </div>
                </div>

                {/* Dropout bar chart */}
                <div className="card">
                  <div className="section-title">Taux d'abandon par institution</div>
                  <div style={{ width: '100%', height: 250 }}>
                    <BarChart width={450} height={200} data={rankings} layout="vertical" margin={{ left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis type="number" domain={[0, 35]} tick={{ fill: 'var(--muted)', fontSize: 11 }} />
                      <YAxis type="category" dataKey="institution_name" width={100} tick={{ fill: 'var(--muted)', fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }} />
                      <Bar dataKey="dropout_rate" radius={[0, 4, 4, 0]}>
                        {rankings.map(r => (
                          <Cell key={r.institution_code} fill={r.dropout_rate <= 15 ? '#10b981' : '#ef4444'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </div>
                </div>

                {/* At Risk */}
                {atRisk.length > 0 && (
                  <div className="card" style={{ gridColumn: '1/-1' }}>
                    <div className="section-title">⚠️ Institutions à risque (abandon {'>'} seuil)</div>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Institution</th><th>Taux d'abandon</th><th>Excès</th><th>Sévérité</th><th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {atRisk.map(r => (
                          <tr key={r.institution_code}>
                            <td style={{ fontWeight: 600 }}>{r.institution_name}</td>
                            <td style={{ color: '#ef4444', fontWeight: 700 }}>{r.dropout_rate}%</td>
                            <td style={{ color: '#f59e0b' }}>+{r.excess}%</td>
                            <td><span className={`badge badge-${r.severity}`}>{r.severity}</span></td>
                            <td>
                              <button className="btn-why" onClick={() => setWhyModal({ id: r.institution_id, indicator: 'dropout_rate' })}>
                                🔍 Pourquoi ?
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Ranking Tab */}
          {activeTab === 'ranking' && (
            <div className="card">
              <div className="section-title">Classement complet — Vue UCAR</div>
              <table className="data-table">
                <thead>
                  <tr><th>#</th><th>Institution</th><th>Réussite</th><th>Abandon</th><th>Présence</th><th>Score</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {rankings.map(r => (
                    <tr key={r.institution_code}>
                      <td><div className={`rank-badge rank-${r.rank <= 3 ? r.rank : 'n'}`}>{r.rank}</div></td>
                      <td>
                        <button
                          className="btn-link"
                          style={{ background: 'none', border: 'none', padding: 0, color: 'var(--primary)', fontWeight: 600, cursor: 'pointer', fontSize: 14, textDecoration: 'underline' }}
                          onClick={() => setDrillDown(r)}
                        >
                          {r.institution_name}
                        </button>
                      </td>
                      <td style={{ color: r.success_rate >= 75 ? '#10b981' : '#ef4444', fontWeight: 600 }}>{r.success_rate}%</td>
                      <td style={{ color: r.dropout_rate <= 15 ? '#10b981' : '#ef4444', fontWeight: 600 }}>{r.dropout_rate}%</td>
                      <td>{r.attendance_rate}%</td>
                      <td>{r.overall_score}</td>
                      <td style={{ display: 'flex', gap: 8 }}>
                        <button className="btn-why" style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--primary)', padding: '4px 8px', borderRadius: 4, border: 'none', cursor: 'pointer', fontSize: 12 }}
                          onClick={() => setWhyModal({ id: r.institution_id, indicator: 'success_rate', alertMsg: `Analyse de performance pour ${r.institution_name}` })}>
                          🔍 Pourquoi ?
                        </button>
                        <button className="btn-why" onClick={() => setHistoryModal({ id: r.institution_id, name: r.institution_name, indicator: 'success_rate' })}>
                          📈
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Predictions Tab */}
          {activeTab === 'predictions' && (
            <div className="card">
              <div className="section-title">🔮 Prévisions IA — Horizon 6 mois</div>
              <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 20 }}>
                Analyse prédictive basée sur le modèle Facebook Prophet. Les pointillés représentent les tendances projetées.
              </p>
              <div style={{ display: 'flex', gap: 20, marginBottom: 20 }}>
                <select
                  className="form-select"
                  style={{ maxWidth: 300 }}
                  onChange={(e) => {
                    const inst = rankings.find(r => r.institution_id === e.target.value);
                    if (inst) setHistoryModal({ id: inst.institution_id, name: inst.institution_name, indicator: 'success_rate' });
                  }}
                >
                  <option value="">Sélectionner une institution pour analyse complète...</option>
                  {rankings.map(r => <option key={r.institution_id} value={r.institution_id}>{r.institution_name}</option>)}
                </select>
              </div>

              <div style={{ textAlign: 'center', padding: 60, background: 'rgba(255,255,255,0.02)', borderRadius: 12, border: '1px dashed var(--border)' }}>
                <div style={{ fontSize: 40, marginBottom: 16 }}>📈</div>
                <h3>Analyse de séries temporelles</h3>
                <p style={{ maxWidth: 500, margin: '0 auto', color: 'var(--muted)' }}>
                  Pour visualiser les prédictions détaillées, cliquez sur l'icône graphique 📈 dans le tableau de classement ou choisissez une institution ci-dessus.
                </p>
              </div>
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="animate-fade-in">
              <div className="section-title">Alertes de Performance en temps réel</div>
              {alerts.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
                  ✅ Aucune alerte active pour le moment
                </div>
              ) : (
                alerts.map((a: any) => (
                  <div key={a.id} className={`card alert-item alert-${a.severity}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, padding: '15px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
                      <div style={{ fontSize: 24 }}>{a.severity === 'critical' ? '🚨' : '⚠️'}</div>
                      <div>
                        <h4 style={{ margin: 0, fontSize: 16 }}>{a.institution_name} — <span style={{ color: 'var(--muted)', fontWeight: 'normal' }}>{a.indicator.replace(/_/g, ' ')}</span></h4>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
                      <span className={`badge badge-${a.severity}`} style={{ fontSize: 10 }}>{a.severity}</span>
                      <button
                        className="btn btn-ghost"
                        style={{ fontSize: 13, color: 'var(--primary)', fontWeight: 'bold' }}
                        onClick={() => setWhyModal({ id: a.institution_id, indicator: a.indicator, alertMsg: a.message })}
                      >
                        🔍 Pourquoi ?
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Modals */}
        {drillDown && (
          <div className="modal-overlay" onClick={() => setDrillDown(null)}>
            <div className="modal" style={{ maxWidth: 900, width: '90%' }} onClick={e => e.stopPropagation()}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div>
                  <h2 style={{ margin: 0 }}>📊 Détails : {drillDown.institution_name}</h2>
                  <p style={{ color: 'var(--muted)', margin: '4px 0 0 0' }}>Analyse complète des 5 indicateurs clés de performance</p>
                </div>
                <button className="btn btn-ghost" onClick={() => setDrillDown(null)}>✕</button>
              </div>

              <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 15, marginBottom: 20 }}>
                {[
                  { label: 'Réussite', val: drillDown.success_rate, key: 'success_rate', target: 75, inv: false },
                  { label: 'Abandon', val: drillDown.dropout_rate, key: 'dropout_rate', target: 15, inv: true },
                  { label: 'Présence', val: drillDown.attendance_rate, key: 'attendance_rate', target: 80, inv: false },
                  { label: 'Passage', val: drillDown.exam_pass_rate || 0, key: 'exam_pass_rate', target: 50, inv: false },
                  { label: 'Redoublement', val: drillDown.grade_repetition_rate || 0, key: 'grade_repetition_rate', target: 10, inv: true }
                ].map(kpi => {
                  const isBad = kpi.inv ? kpi.val > kpi.target : kpi.val < kpi.target;
                  return (
                    <div key={kpi.key} className="card" style={{ borderLeft: `4px solid ${isBad ? '#ef4444' : '#10b981'}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                        <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>{kpi.label.toUpperCase()}</span>
                        <span style={{ fontSize: 18 }}>{isBad ? '⚠️' : '✅'}</span>
                      </div>
                      <div style={{ fontSize: 24, fontWeight: 'bold', marginBottom: 10 }}>{kpi.val}%</div>
                      <div style={{ display: 'flex', gap: 10 }}>
                        <button
                          className="btn btn-ghost"
                          style={{ fontSize: 10, padding: '4px 8px', color: 'var(--primary)' }}
                          onClick={() => setWhyModal({ id: drillDown.institution_id, indicator: kpi.key, alertMsg: `Analyse détaillée de ${kpi.label} pour ${drillDown.institution_name}` })}
                        >
                          🔍 Pourquoi ?
                        </button>
                        <button
                          className="btn btn-ghost"
                          style={{ fontSize: 10, padding: '4px 8px' }}
                          onClick={() => setHistoryModal({ id: drillDown.institution_id, name: drillDown.institution_name, indicator: kpi.key })}
                        >
                          📈 Tendance
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="card" style={{ background: 'var(--surface2)', textAlign: 'center', padding: 20 }}>
                <div style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 5 }}>SCORE GLOBAL</div>
                <div style={{ fontSize: 32, fontWeight: 'bold', color: 'var(--primary)' }}>{drillDown.overall_score} / 100</div>
              </div>
            </div>
          </div>
        )}

        {whyModal && (
          <WhyModal
            institutionId={whyModal.id}
            indicator={whyModal.indicator}
            alertMsg={whyModal.alertMsg}
            onClose={() => setWhyModal(null)}
          />
        )}
        {historyModal && (
          <HistoryModal
            institutionId={historyModal.id}
            institutionName={historyModal.name}
            indicator={historyModal.indicator}
            onClose={() => setHistoryModal(null)}
          />
        )}
      </div>
    </div>
  );
}
