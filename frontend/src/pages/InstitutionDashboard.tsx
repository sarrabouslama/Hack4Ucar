import { useState, useEffect, useRef } from 'react';
import { getInstitutions, uploadDocument } from '../api/kpiApi';

export default function InstitutionDashboard() {
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getInstitutions().then(r => {
      setInstitutions(r.data);
      if (r.data.length > 0) setSelectedId(r.data[0].id);
    });
  }, []);

  const handleFile = async (file: File) => {
    if (!selectedId) {
      alert("Veuillez sélectionner une institution");
      return;
    }
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await uploadDocument(file, selectedId);
      setSuccess(res.data.document);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="container animate-fade-in" style={{ maxWidth: '1400px', margin: '0 auto', padding: '40px 20px' }}>
      
      {/* Top Banner / Header */}
      <div className="glass-panel" style={{ 
        padding: '40px', 
        borderRadius: '30px', 
        marginBottom: '40px', 
        background: 'linear-gradient(135deg, rgba(13, 27, 56, 0.95) 0%, rgba(30, 58, 110, 0.9) 100%)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 20px 40px rgba(0,0,0,0.3)'
      }}>
        <div style={{ maxWidth: '60%' }}>
          <h1 className="title" style={{ fontSize: '3.2rem', color: 'white', marginBottom: '10px', lineHeight: '1.1' }}>
            Portail <span style={{ color: '#4facfe' }}>D'Ingestion</span> AI
          </h1>
          <p className="subtitle" style={{ color: 'rgba(255,255,255,0.6)', fontSize: '1.1rem' }}>
            Centralisez et automatisez l'extraction de vos KPIs académiques, financiers et environnementaux.
          </p>
        </div>

        <div style={{ background: 'rgba(255,255,255,0.05)', padding: '20px', borderRadius: '20px', border: '1px solid rgba(255,255,255,0.1)', minWidth: '300px' }}>
          <label style={{ fontSize: '10px', color: '#4facfe', fontWeight: '800', letterSpacing: '1px', display: 'block', marginBottom: '8px', textTransform: 'uppercase' }}>INSTITUTION CONNECTÉE</label>
          <select 
            className="form-select" 
            value={selectedId} 
            onChange={(e) => setSelectedId(e.target.value)}
            style={{ 
                background: 'transparent', 
                border: 'none', 
                color: 'white', 
                fontSize: '18px', 
                fontWeight: '600',
                outline: 'none',
                cursor: 'pointer',
                width: '100%'
            }}
          >
            <option value="" style={{background: '#111'}}>Sélectionner institution...</option>
            {institutions.map(inst => (
              <option key={inst.id} value={inst.id} style={{background: '#111'}}>{inst.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 400px', gap: '40px', alignItems: 'start' }}>
        
        {/* Left Column: Main Action Area */}
        <div className="stack">
          
          {/* Main Upload Card */}
          <div 
            className={`upload-zone ${dragActive ? 'active' : ''} ${loading ? 'loading' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              height: '450px',
              border: '2px dashed rgba(201, 168, 76, 0.3)',
              borderRadius: '32px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
              background: dragActive ? 'rgba(201, 168, 76, 0.05)' : 'rgba(255,255,255,0.03)',
              position: 'relative',
              overflow: 'hidden',
              boxShadow: dragActive ? '0 0 40px rgba(201, 168, 76, 0.1)' : 'none'
            }}
          >
            <input 
              ref={fileInputRef}
              type="file" 
              style={{ display: 'none' }} 
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />

            {loading ? (
              <div style={{ textAlign: 'center' }}>
                <div className="spinner-glow" style={{ position: 'relative', width: '80px', height: '80px', margin: '0 auto 30px' }}>
                    <div style={{ position: 'absolute', inset: 0, border: '6px solid rgba(79, 172, 254, 0.1)', borderRadius: '50%' }} />
                    <div style={{ position: 'absolute', inset: 0, border: '6px solid transparent', borderTopColor: '#4facfe', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                </div>
                <h2 style={{ margin: 0, fontSize: '24px' }}>IA en cours d'analyse...</h2>
                <p style={{ color: 'var(--text-muted)', marginTop: '10px' }}>Extraction Gemini Vision & Classification</p>
              </div>
            ) : (
              <>
                <div className="icon-box" style={{ fontSize: '80px', marginBottom: '25px', filter: 'drop-shadow(0 10px 20px rgba(0,0,0,0.2))' }}>📂</div>
                <h2 style={{ fontSize: '28px', marginBottom: '12px' }}>Glissez votre document</h2>
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', maxWidth: '400px', fontSize: '1.1rem' }}>
                  Déposez un scan de facture, un relevé académique ou un certificat RSE.
                </p>
                <div style={{ marginTop: '40px', padding: '12px 30px', background: 'var(--navy)', color: 'var(--gold-light)', borderRadius: '14px', fontWeight: '700', fontSize: '15px', border: '1px solid var(--gold)' }}>
                  SÉLECTIONNER UN FICHIER
                </div>
              </>
            )}
          </div>

          {/* Recent Activity Mock (to fill desktop space) */}
          <div className="card" style={{ marginTop: '40px', borderRadius: '24px', border: '1px solid rgba(0,0,0,0.05)' }}>
             <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                 🕒 Historique Récent d'Ingestion
             </h3>
             <table className="data-table" style={{ width: '100%' }}>
                 <thead>
                     <tr>
                         <th>Fichier</th>
                         <th>Module</th>
                         <th>Date</th>
                         <th>Statut</th>
                     </tr>
                 </thead>
                 <tbody>
                     <tr>
                         <td style={{ fontWeight: '600' }}>Facture_STEG_S1.pdf</td>
                         <td><span className="badge badge-warning">Environment</span></td>
                         <td>Aujourd'hui, 10:24</td>
                         <td style={{ color: 'var(--success)' }}>● Terminé</td>
                     </tr>
                     <tr>
                         <td style={{ fontWeight: '600' }}>Transcript_L3_Informatique.png</td>
                         <td><span className="badge badge-good">Academic</span></td>
                         <td>Hier, 16:45</td>
                         <td style={{ color: 'var(--success)' }}>● Terminé</td>
                     </tr>
                 </tbody>
             </table>
          </div>
        </div>

        {/* Right Column: Status & Insights */}
        <div className="stack">
            
            {success ? (
                <div className="card animate-slide-up" style={{ 
                    borderRadius: '24px', 
                    background: 'linear-gradient(180deg, rgba(16, 185, 129, 0.05) 0%, rgba(16, 185, 129, 0.1) 100%)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    padding: '30px'
                }}>
                    <div style={{ fontSize: '40px', marginBottom: '15px' }}>✨</div>
                    <h3 style={{ color: '#10b981', fontSize: '22px', marginBottom: '10px' }}>Analyse Terminée</h3>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '25px' }}>
                        Gemini a identifié le document et routé les données vers les modules correspondants.
                    </p>

                    <div className="result-metric" style={{ marginBottom: '20px' }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Classification</div>
                        <div style={{ fontSize: '20px', fontWeight: '800' }}>{success.module_classification}</div>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '30px' }}>
                        {success.module_classification.split(', ').map((mod: string) => (
                            <div key={mod} style={{ background: 'white', padding: '5px 15px', borderRadius: '10px', fontSize: '12px', fontWeight: '700', border: '1px solid rgba(0,0,0,0.1)' }}>
                                #{mod.toUpperCase()}
                            </div>
                        ))}
                    </div>

                    <button className="btn btn-primary" style={{ width: '100%', padding: '15px', borderRadius: '15px' }} onClick={() => setSuccess(null)}>
                        UPLOADER UN AUTRE
                    </button>
                </div>
            ) : error ? (
                <div className="card" style={{ borderRadius: '24px', border: '1px solid #ef4444', background: 'rgba(239, 68, 68, 0.05)' }}>
                    <h3 style={{ color: '#ef4444', marginBottom: '15px' }}>Oups ! Échec de l'analyse</h3>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>{error}</p>
                    <button className="btn btn-ghost" onClick={() => setError(null)}>Réessayer</button>
                </div>
            ) : (
                <div className="card glass-panel" style={{ 
                    borderRadius: '24px', 
                    padding: '30px', 
                    background: 'white', 
                    border: '1px solid rgba(0,0,0,0.05)' 
                }}>
                    <h3 style={{ marginBottom: '20px' }}>💡 Guide Intelligent</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <div style={{ display: 'flex', gap: '15px' }}>
                            <div style={{ width: '30px', height: '30px', background: '#f5e9c4', borderRadius: '8px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>1</div>
                            <p style={{ fontSize: '13px', lineHeight: '1.5' }}><strong>Vérifiez l'institution :</strong> L'IA associera les KPIs à l'université sélectionnée en haut de page.</p>
                        </div>
                        <div style={{ display: 'flex', gap: '15px' }}>
                            <div style={{ width: '30px', height: '30px', background: '#f5e9c4', borderRadius: '8px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>2</div>
                            <p style={{ fontSize: '13px', lineHeight: '1.5' }}><strong>Documents multiples :</strong> Vous pouvez uploader des PDF multi-pages ou des photos de factures.</p>
                        </div>
                        <div style={{ display: 'flex', gap: '15px' }}>
                            <div style={{ width: '30px', height: '30px', background: '#f5e9c4', borderRadius: '8px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>3</div>
                            <p style={{ fontSize: '13px', lineHeight: '1.5' }}><strong>Validation :</strong> Les données extraites apparaissent instantanément sur le dashboard UCAR après l'upload.</p>
                        </div>
                    </div>
                </div>
            )}

            <div className="card" style={{ marginTop: '20px', borderRadius: '24px', background: '#0d1b38', color: 'white', textAlign: 'center' }}>
                <div style={{ fontSize: '24px', marginBottom: '10px' }}>🤖</div>
                <div style={{ fontSize: '14px', fontWeight: '600' }}>Propulsé par Gemini 1.5 Pro</div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '5px' }}>Précision d'extraction de 98.4%</div>
            </div>
        </div>
      </div>

      <style>{`
        .upload-zone:hover {
          border-color: var(--gold) !important;
          background: rgba(201, 168, 76, 0.05) !important;
          transform: translateY(-8px);
          box-shadow: 0 20px 50px rgba(13, 27, 56, 0.1) !important;
        }
        .upload-zone.active {
          border-color: #4facfe !important;
          background: rgba(79, 172, 254, 0.08) !important;
        }
        .icon-box {
            animation: float 3s ease-in-out infinite;
        }
        @keyframes float {
            0% { transform: translateY(0); }
            50% { transform: translateY(-15px); }
            100% { transform: translateY(0); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .animate-fade-in {
            animation: fadeIn 0.6s ease-out forwards;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .data-table th {
            font-size: 10px;
            color: var(--text-muted);
            text-transform: uppercase;
            padding: 10px;
        }
        .data-table td {
            padding: 15px 10px;
            font-size: 13px;
        }
      `}</style>
    </div>
  );
}
