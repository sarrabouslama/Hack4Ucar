import { useState, useEffect } from 'react';
import UcarDashboard from './pages/UcarDashboard';
import InstitutionDashboard from './pages/InstitutionDashboard';
import './index.css';

export default function App() {
  const [view, setView] = useState<'ucar' | 'institution'>('ucar');
  const [ucarTab, setUcarTab] = useState<'overview' | 'ranking' | 'alerts' | 'predictions'>('overview');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Temps Réel (Polling) : On rafraîchit les compteurs d'alertes toutes les 5 secondes
  useEffect(() => {
    const interval = setInterval(() => {
      setRefreshTrigger(prev => prev + 1);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span>🎓</span> UniSmart AI
        </div>

        {/* Space switcher */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 10, color: 'var(--muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Espace
          </div>
          <button
            className={`nav-item ${view === 'ucar' ? 'active' : ''}`}
            onClick={() => setView('ucar')}
          >
            🔵 UCAR Central
          </button>
          <button
            className={`nav-item ${view === 'institution' ? 'active' : ''}`}
            onClick={() => setView('institution')}
          >
            🟠 Institution
          </button>
        </div>

        <div style={{ fontSize: 10, color: 'var(--muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Navigation
        </div>

        {view === 'ucar' ? (
          <>
            <button className={`nav-item ${ucarTab === 'overview' ? 'active' : ''}`} onClick={() => setUcarTab('overview')}>📊 Dashboard</button>
            <button className={`nav-item ${ucarTab === 'alerts' ? 'active' : ''}`} onClick={() => setUcarTab('alerts')}>🚨 Alertes</button>
            <button className={`nav-item ${ucarTab === 'predictions' ? 'active' : ''}`} onClick={() => setUcarTab('predictions')}>📈 Prédictions</button>
            <button className={`nav-item ${ucarTab === 'ranking' ? 'active' : ''}`} onClick={() => setUcarTab('ranking')}>🏆 Classement</button>
          </>
        ) : (
          <>
            <button className="nav-item active">📋 Mes KPIs</button>
            <button className="nav-item">➕ Saisir données</button>
            <button className="nav-item">🏅 Mon rang</button>
          </>
        )}

        <div style={{ marginTop: 'auto', padding: '12px', background: 'rgba(59,130,246,0.08)', borderRadius: 8, fontSize: 11, color: 'var(--muted)' }}>
          <div style={{ color: 'var(--primary)', fontWeight: 600, marginBottom: 4 }}>HACK4UCAR 2025</div>
          Track 4 · Member 1<br />Academic Intelligence
        </div>
      </aside>

      {/* Main */}
      <main className="main-content">
        {view === 'ucar'
          ? <UcarDashboard activeTab={ucarTab} setActiveTab={setUcarTab} refreshTrigger={refreshTrigger} />
          : <InstitutionDashboard />
        }
      </main>
    </div>
  );
}
