import { useState, useEffect } from 'react';
import axios from 'axios';
import { getInstitutions, submitKpis } from '../api/kpiApi';

export default function InstitutionDashboard() {
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [scanJson, setScanJson] = useState('');
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const demoJson = {
    total_effectif: 120,
    sessions_planned: 24,
    total_recorded_presence: 2160,
    students: [
      { id: "S1", final_grade: 14, presence_count: 22, is_repeating: false },
      { id: "S2", final_grade: 9, presence_count: 20, is_repeating: true },
      { id: "S3", final_grade: null, presence_count: 0, is_repeating: true },
      { id: "S4", final_grade: 11, presence_count: 24, is_repeating: false }
    ]
  };

  useEffect(() => {
    getInstitutions().then(r => {
      setInstitutions(r.data);
      if (r.data.length > 0) setSelectedId(r.data[0].id);
    });
  }, []);

  const handleProcessScan = async () => {
    if (!scanJson || !selectedId) return;
    setLoading(true);
    try {
      const parsed = JSON.parse(scanJson);
      // 1. Calculer les taux via l'IA
      const res = await axios.post('http://localhost:8000/api/v1/academic/process-scan', parsed);
      const analysisData = res.data;
      setAnalysis(analysisData);

      // 2. Filtrer les indicateurs qui sont 'null' pour éviter les erreurs DB
      const cleanIndicators = Object.fromEntries(
        Object.entries(analysisData.indicators).filter(([_, v]) => v !== null)
      );

      // 3. Transmettre AUTOMATIQUEMENT à l'UCAR
      await submitKpis(selectedId, {
        reporting_date: new Date().toISOString(),
        ...cleanIndicators
      });
      
      setSuccess(true);
      setTimeout(() => setSuccess(false), 4000);
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      const errorMsg = typeof errorDetail === 'object' 
        ? JSON.stringify(errorDetail) 
        : (errorDetail || err.message);
        
      alert("Erreur lors de la transmission : " + errorMsg);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="header-flex" style={{ marginBottom: 30 }}>
        <div>
          <h1 className="title">🏢 Espace Institution (Mode Scan)</h1>
          <p className="subtitle">Importez les données brutes des documents scannés</p>
        </div>
        
        <select 
          className="form-select" 
          value={selectedId} 
          onChange={(e) => setSelectedId(e.target.value)}
          style={{ maxWidth: '300px' }}
        >
          <option value="">Sélectionner votre institution...</option>
          {institutions.map(inst => (
            <option key={inst.id} value={inst.id}>{inst.name} ({inst.code})</option>
          ))}
        </select>
      </div>

      {selectedId ? (
        <div className="grid-2" style={{ alignItems: 'start' }}>
          
          {/* Input Area */}
          <div className="card">
            <div className="section-title">📄 Simulation de Scan Documentaire</div>
            <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 15 }}>
              Collez ici le JSON extrait du module de reconnaissance de caractères (OCR).
            </p>
            <textarea 
              className="form-input" 
              style={{ minHeight: 250, fontFamily: 'monospace', fontSize: 12, background: 'rgba(0,0,0,0.2)' }}
              value={scanJson}
              onChange={(e) => setScanJson(e.target.value)}
              placeholder='{ "total_effectif": 100, ... }'
            />
            <div style={{ display: 'flex', gap: 10, marginTop: 15 }}>
              <button className="btn btn-ghost" onClick={() => setScanJson(JSON.stringify(demoJson, null, 2))}>
                📝 Charger exemple
              </button>
              <button className="btn btn-primary" onClick={handleProcessScan} disabled={loading || !scanJson}>
                {loading ? 'Analyse...' : '🔍 Lancer le calcul IA'}
              </button>
            </div>
          </div>

          {/* Result Area */}
          {analysis && (
            <div className="card animate-fade-in" style={{ borderColor: 'var(--primary)' }}>
              <div className="section-title">📊 Résultats du Calcul</div>
              
              <div className="stats-grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 15, marginBottom: 20 }}>
                {Object.entries(analysis.indicators).map(([key, value]: [string, any]) => (
                  <div key={key} style={{ padding: 15, background: 'rgba(255,255,255,0.03)', borderRadius: 8, border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 10, textTransform: 'uppercase', color: 'var(--muted)' }}>{key.replace('_', ' ')}</div>
                    <div style={{ fontSize: 24, fontWeight: 'bold', color: value === null ? 'var(--danger)' : 'var(--text)' }}>
                      {value !== null ? `${value}%` : 'N/A'}
                    </div>
                  </div>
                ))}
              </div>

              {analysis.warnings.length > 0 && (
                <div style={{ padding: 12, background: 'rgba(255,165,0,0.1)', color: '#ffa500', borderRadius: 8, marginBottom: 20, fontSize: 12 }}>
                  <strong>⚠️ Warnings :</strong>
                  <ul style={{ margin: '5px 0 0 15px' }}>
                    {analysis.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}

          {success && (
            <div className="card" style={{ gridColumn: '1 / -1', background: 'rgba(0,255,100,0.1)', color: '#00ff66', textAlign: 'center' }}>
              ✅ Données certifiées et enregistrées avec succès !
            </div>
          )}

        </div>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: '60px', border: '2px dashed var(--border)' }}>
          <div style={{ fontSize: '40px', marginBottom: '20px' }}>🏫</div>
          <h2>Identifiez-vous</h2>
          <p style={{ color: 'var(--muted)' }}>Sélectionnez votre institution pour simuler un scan.</p>
        </div>
      )}
    </div>
  );
}

