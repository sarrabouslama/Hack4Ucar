import { useState } from 'react';
import UcarDashboard from './pages/UcarDashboard';
import InstitutionDashboard from './pages/InstitutionDashboard';

function App() {
  const [view, setView] = useState<'ucar' | 'institution'>('ucar');
  const [activeTab, setActiveTab] = useState<'overview' | 'ranking' | 'alerts' | 'predictions'>('overview');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  return (
    <div className="app-container">
      {/* Sidebar UniBot Style */}
      <nav className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-gem">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0d1b38" strokeWidth="2.5">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <span>UniSmart</span>
          </div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em', marginTop: 4, textTransform: 'uppercase', paddingLeft: 45 }}>
            Intelligence · UCAR
          </div>
        </div>

        <div className="nav-links">
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', padding: '0 16px', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Espaces</div>
          <button className={`nav-item ${view === 'ucar' ? 'active' : ''}`} onClick={() => setView('ucar')}>
            🏢 Dashboard UCAR
          </button>
          <button className={`nav-item ${view === 'institution' ? 'active' : ''}`} onClick={() => setView('institution')}>
            🏫 Institution
          </button>

          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', padding: '0 16px', margin: '24px 0 12px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Actions</div>
          <button className="nav-item" onClick={() => setRefreshTrigger(prev => prev + 1)}>🔄 Actualiser les données</button>
          <button className="nav-item">💬 Assistant UniBot</button>
        </div>

        <div style={{ padding: 20, borderTop: '1px solid rgba(255,255,255,0.05)', fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, background: '#10b981', borderRadius: '50%' }}></div>
            IA Prophet v2.5 Online
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        {view === 'ucar' ? (
          <UcarDashboard 
            activeTab={activeTab} 
            setActiveTab={setActiveTab} 
            refreshTrigger={refreshTrigger} 
          />
        ) : (
          <InstitutionDashboard />
        )}
      </main>
    </div>
  );
}

export default App;
