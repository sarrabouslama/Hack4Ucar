import React, { useState } from 'react';
import './InstituteConsole.css';

const API = '/api/v1';

interface Initiative {
  title: string;
  category: string;
  description: string;
  estimated: number;
  proof: boolean;
  confidence: number;
}

const InstituteConsole: React.FC = () => {
  const [initiatives, setInitiatives] = useState<Initiative[]>([
    { title: 'Solar rooftop tranche A', category: 'solar', description: 'Installation de panneaux photovoltaiques sur le bloc administratif.', estimated: 22000, proof: true, confidence: 0.91 },
    { title: 'LED retrofit amphitheatres', category: 'lighting', description: 'Remplacement progressif de l eclairage traditionnel par LED.', estimated: 8600, proof: true, confidence: 0.74 }
  ]);
  const [profile, setProfile] = useState({
    institutionId: 'ucar-ensi-green',
    institutionName: 'ENSI Green Campus',
    surface: 9600,
    students: 1630,
    employees: 210,
    period: '2026-S1',
  });

  const [utilities, setUtilities] = useState({
    electricity: { consumption: 515000, cost: 112000, note: 'Campus principal' },
    gas: { consumption: 19000, cost: 23600, note: 'Laboratoires' },
    water: { consumption: 7600, cost: 9900, note: 'Bloc pedagogique' },
  });

  const [emailMetrics, setEmailMetrics] = useState({
    sent: 84000,
    avgSize: 172,
    attachments: 18000,
    avgAttachSize: 840,
    recipients: 2.4,
    storedDays: 180,
    period: '2026-S1',
  });

  const [results, setResults] = useState<Record<string, Record<string, unknown> | null>>({
    scorecard: null,
    emailFootprint: null,
    ocrExtraction: null,
    uploads: null,
  });

  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const fillSampleData = () => {
    setProfile({
      institutionId: 'ucar-ensi-green',
      institutionName: 'ENSI Green Campus',
      surface: 9600,
      students: 1630,
      employees: 210,
      period: '2026-S1',
    });
    setUtilities({
      electricity: { consumption: 515000, cost: 112000, note: 'Campus principal' },
      gas: { consumption: 19000, cost: 23600, note: 'Laboratoires' },
      water: { consumption: 7600, cost: 9900, note: 'Bloc pedagogique' },
    });
    setEmailMetrics({
      sent: 84000,
      avgSize: 172,
      attachments: 18000,
      avgAttachSize: 840,
      recipients: 2.4,
      storedDays: 180,
      period: '2026-S1',
    });
    setInitiatives([
      { title: 'Solar rooftop tranche A', category: 'solar', description: 'Installation de panneaux photovoltaiques sur le bloc administratif.', estimated: 22000, proof: true, confidence: 0.91 },
      { title: 'LED retrofit amphitheatres', category: 'lighting', description: 'Remplacement progressif de l eclairage traditionnel par LED.', estimated: 8600, proof: true, confidence: 0.74 }
    ]);
    showToast('Jeu de donnees institut charge.');
  };

  const runScorecard = async () => {
    try {
      const payload = {
        institution_id: profile.institutionId,
        institution_name: profile.institutionName,
        surface_m2: profile.surface,
        students_count: profile.students,
        employees_count: profile.employees,
        utility_bills: [
          { utility_type: 'electricity', period_label: profile.period, consumption_value: utilities.electricity.consumption, consumption_unit: 'kwh', invoice_amount: utilities.electricity.cost },
          { utility_type: 'gas', period_label: profile.period, consumption_value: utilities.gas.consumption, consumption_unit: 'm3', invoice_amount: utilities.gas.cost },
          { utility_type: 'water', period_label: profile.period, consumption_value: utilities.water.consumption, consumption_unit: 'm3', invoice_amount: utilities.water.cost },
        ],
        rse_initiatives: initiatives.map(i => ({
          title: i.title,
          category: i.category,
          description: i.description,
          estimated_co2_reduction_kg: i.estimated,
          proof_document_present: i.proof,
          proof_confidence: i.confidence
        }))
      };
      const res = await fetch(`${API}/environment/scorecard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setResults((prev) => ({ ...prev, scorecard: data }));
      showToast('Score environnemental mis a jour.');
    } catch {
      showToast('Erreur scorecard');
    }
  };

  const runEmailFootprint = async () => {
    try {
      const payload = {
        institution_id: profile.institutionId,
        institution_name: profile.institutionName,
        students_count: profile.students,
        employees_count: profile.employees,
        email_metrics: [{
          period_label: emailMetrics.period,
          emails_sent: emailMetrics.sent,
          average_email_size_kb: emailMetrics.avgSize,
          attachments_count: emailMetrics.attachments,
          average_attachment_size_kb: emailMetrics.avgAttachSize,
          average_recipients: emailMetrics.recipients,
          stored_days: emailMetrics.storedDays
        }]
      };
      const res = await fetch(`${API}/environment/email-footprint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setResults((prev) => ({ ...prev, emailFootprint: data }));
      showToast('Empreinte email calculee.');
    } catch {
      showToast('Erreur email footprint');
    }
  };

  return (
    <div className="institute-console-wrapper">
       

        <main className="main">
          <header className="header">
            <div>
              <div className="header-title">Institute Sustainability Console</div>
              <div className="header-sub">Factures, OCR, RSE, empreinte email et score environnemental consolide</div>
            </div>
            <div className="header-actions">
              <button className="soft-btn" onClick={fillSampleData}>Sample Data</button>
              <button className="primary-btn" onClick={async () => { await runScorecard(); await runEmailFootprint(); }}>Run Full Analysis</button>
            </div>
          </header>

          <div className="content">
            <section className="top-grid" id="overview">
              <article className="stat-card">
                <div className="stat-label">Score Environnemental</div>
                <div className="stat-value">{results.scorecard?.environmental_score ?? '--'}</div>
                <div className="stat-sub">{results.scorecard ? `${results.scorecard.annualized_co2_per_person_kg.toFixed(1)} kg/pers/an` : 'Calcul en attente...'}</div>
                <div className={`status-pill ${results.scorecard?.verdict?.toLowerCase().includes('alarme') ? 'danger' : ''}`}>
                  {results.scorecard?.verdict ?? 'Awaiting data'}
                </div>
              </article>
              <article className="stat-card">
                <div className="stat-label">CO2 Optimise</div>
                <div className="stat-value">{results.scorecard?.optimized_co2_kg.toLocaleString() ?? '--'} <span style={{fontSize:'14px'}}>kg</span></div>
                <div className="stat-sub">Reductions RSE: {results.scorecard?.total_rse_reduction_kg.toLocaleString() ?? '0'} kg</div>
              </article>
              <article className="stat-card">
                <div className="stat-label">Email Footprint</div>
                <div className="stat-value">{results.emailFootprint?.digital_responsibility_score ?? '--'}</div>
                <div className="stat-sub">Score de sobriete numerique</div>
              </article>
              <article className="stat-card">
                <div className="stat-label">Documents Analyses</div>
                <div className="stat-value">{Array.isArray(results.uploads) ? results.uploads.length : 0}</div>
                <div className="stat-sub">Justificatifs relies a la periode</div>
              </article>
            </section>

            <section className="main-grid">
              <div className="stack">
                <section className="panel" id="energy">
                  <div className="panel-head">
                    <div>
                      <div className="panel-title">Profil Institut & Consommation</div>
                      <div className="panel-copy">Donnees de surface, effectifs et factures energetiques.</div>
                    </div>
                  </div>
                  <div className="panel-body">
                    <div className="form-grid">
                      <div className="field">
                        <label>Institution Name</label>
                        <input value={profile.institutionName} onChange={e => setProfile({...profile, institutionName: e.target.value})} />
                      </div>
                      <div className="field">
                        <label>Surface m2</label>
                        <input type="number" value={profile.surface} onChange={e => setProfile({...profile, surface: parseInt(e.target.value) || 0})} />
                      </div>
                      <div className="field">
                        <label>Etudiants</label>
                        <input type="number" value={profile.students} onChange={e => setProfile({...profile, students: parseInt(e.target.value) || 0})} />
                      </div>
                      <div className="field">
                        <label>Employes</label>
                        <input type="number" value={profile.employees} onChange={e => setProfile({...profile, employees: parseInt(e.target.value) || 0})} />
                      </div>
                    </div>

                    <div className="utility-grid">
                      {(['electricity', 'gas', 'water'] as const).map(u => (
                        <div key={u} className="utility-row">
                          <div className="utility-type">{u}</div>
                          <div className="field">
                            <label>Conso</label>
                            <input type="number" value={utilities[u].consumption} onChange={e => setUtilities({...utilities, [u]: {...utilities[u], consumption: parseInt(e.target.value) || 0}})} />
                          </div>
                          <div className="field">
                            <label>Cout</label>
                            <input type="number" value={utilities[u].cost} onChange={e => setUtilities({...utilities, [u]: {...utilities[u], cost: parseInt(e.target.value) || 0}})} />
                          </div>
                          <div className="field">
                            <label>Note</label>
                            <input value={utilities[u].note} onChange={e => setUtilities({...utilities, [u]: {...utilities[u], note: e.target.value}})} />
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="toolbar">
                      <button className="primary-btn" onClick={runScorecard}>Compute CO2 Scorecard</button>
                    </div>
                  </div>
                </section>

                <section className="panel" id="rse">
                  <div className="panel-head">
                     <div>
                        <div className="panel-title">Actes RSE & Initiatives</div>
                     </div>
                  </div>
                  <div className="panel-body">
                    <div className="initiative-list">
                      {initiatives.map((init, idx) => (
                        <div key={idx} className="initiative-row">
                          <div className="field"><label>Titre</label><input value={init.title} onChange={e => {
                            const next = [...initiatives];
                            next[idx].title = e.target.value;
                            setInitiatives(next);
                          }} /></div>
                          <div className="field"><label>Reduction kg</label><input type="number" value={init.estimated} onChange={e => {
                            const next = [...initiatives];
                            next[idx].estimated = parseInt(e.target.value) || 0;
                            setInitiatives(next);
                          }} /></div>
                          <div className="field"><label>Confiance</label><input type="number" step="0.1" value={init.confidence} onChange={e => {
                            const next = [...initiatives];
                            next[idx].confidence = parseFloat(e.target.value) || 0;
                            setInitiatives(next);
                          }} /></div>
                        </div>
                      ))}
                    </div>
                    <div className="toolbar" style={{marginTop: '15px'}}>
                      <button className="soft-btn" onClick={() => setInitiatives([...initiatives, {title: 'New', category: 'other', description: '', estimated: 0, proof: true, confidence: 0.5}])}>Add RSE Action</button>
                    </div>
                  </div>
                </section>
              </div>

              <div className="stack">
                <section className="panel" id="scorecard">
                   <div className="panel-head"><div className="panel-title">Environmental Gauge</div></div>
                   <div className="panel-body">
                      <div className="gauge">
                        <div className="gauge-ring" style={{
                          background: `conic-gradient(var(--gold) ${(results.scorecard?.environmental_score || 0) * 3.6}deg, var(--cream-deep) 0deg)`,
                        }}>
                          <div className="gauge-copy">
                            <div className="gauge-score">{results.scorecard?.environmental_score ?? '--'}</div>
                            <div className="gauge-label">score /100</div>
                          </div>
                        </div>
                      </div>
                      <div style={{marginTop:20}}>
                        {results.scorecard?.insights?.map((insight: string, i: number) => (
                          <div key={i} className="insight-item" style={{marginBottom:8, fontSize:'13px'}}>{insight}</div>
                        ))}
                      </div>
                   </div>
                </section>
                
                <section className="panel">
                    <div className="panel-head"><div className="panel-title">Email Footprint Result</div></div>
                    <div className="panel-body">
                       <div className="stat-value">{results.emailFootprint?.digital_responsibility_score ?? '--'} <span style={{fontSize:'12px', color:'#999'}}>/ 100</span></div>
                       <div className="stat-sub">{results.emailFootprint?.verdict}</div>
                    </div>
                </section>
              </div>
            </section>
          </div>
        </main>

      {toastMessage && (
        <div className="toast show">{toastMessage}</div>
      )}
    </div>
  );
};

export default InstituteConsole;
