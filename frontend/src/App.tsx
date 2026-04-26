import { useState } from 'react';
import UcarDashboard from './pages/UcarDashboard';
import InstitutionDashboard from './pages/InstitutionDashboard';
import Chatbot from './pages/Chatbot';
import Automation from './pages/Automation';
import Search from './pages/Search';
import InstituteConsole from './pages/InstituteConsole';

type View = 'ucar' | 'institution' | 'chatbot' | 'automation' | 'search' | 'institute_console';
type DashboardTab = 'overview' | 'ranking' | 'alerts' | 'predictions';

function App() {
  const [view, setView] = useState<View>('ucar');
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [instituteListOpen, setInstituteListOpen] = useState(false);

  const embeddedViews: View[] = ['chatbot', 'automation', 'search', 'institute_console'];
  const isEmbeddedView = embeddedViews.includes(view);
  const isInstituteView = view === 'institute_console';

  const renderCurrentView = () => {
    if (view === 'ucar') {
      return (
        <UcarDashboard
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          refreshTrigger={refreshTrigger}
        />
      );
    }

    if (view === 'institution') {
      return <InstitutionDashboard />;
    }

    if (view === 'chatbot') {
      return <Chatbot />;
    }

    if (view === 'automation') {
      return <Automation />;
    }

    if (view === 'search') {
      return <Search />;
    }

    return <InstituteConsole />;
  };

  return (
    <div className="app-container">
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
          <div
            style={{
              fontSize: 10,
              color: 'rgba(255,255,255,0.3)',
              letterSpacing: '0.1em',
              marginTop: 4,
              textTransform: 'uppercase',
              paddingLeft: 45,
            }}
          >
            {isInstituteView ? 'Institute Workspace' : 'Intelligence · UCAR'}
          </div>
        </div>

        <div className="nav-links">
          <div
            style={{
              fontSize: 10,
              color: 'rgba(255,255,255,0.2)',
              padding: '0 16px',
              marginBottom: 12,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}
          >
            Espaces
          </div>

          <button className={`nav-item ${view === 'ucar' ? 'active' : ''}`} onClick={() => setView('ucar')}>
            Dashboard UCAR
          </button>
          <button className={`nav-item ${view === 'institution' ? 'active' : ''}`} onClick={() => setView('institution')}>
            Institution Scan
          </button>
          <div className="nav-group">
            <button
              className={`nav-item ${view === 'institute_console' ? 'active' : ''}`}
              onClick={() => {
                setView('institute_console');
                setInstituteListOpen(!instituteListOpen);
              }}
              style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                Institute Console
              </div>
              <svg 
                width="16" 
                height="16" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                style={{ 
                  transform: instituteListOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s'
                }}
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
            <div className={`nav-roll-list ${instituteListOpen ? 'open' : ''}`}>
              <a className="roll-item" href="#overview" onClick={() => setView('institute_console')}>Vue d'ensemble</a>
              <a className="roll-item" href="#energy" onClick={() => setView('institute_console')}>Consommation</a>
              <a className="roll-item" href="#rse" onClick={() => setView('institute_console')}>Actes RSE</a>
              <a className="roll-item" href="#ocr" onClick={() => setView('institute_console')}>OCR Documents</a>
              <a className="roll-item" href="#email" onClick={() => setView('institute_console')}>Empreinte email</a>
              <div className="roll-divider"></div>
              <a className="roll-item" href="#scorecard" onClick={() => setView('institute_console')}>CO2 optimise</a>
              <a className="roll-item" href="#email-results" onClick={() => setView('institute_console')}>Score numerique</a>
              <a className="roll-item" href="#documents" onClick={() => setView('institute_console')}>Justificatifs</a>
            </div>
          </div>
          <button className={`nav-item ${view === 'automation' ? 'active' : ''}`} onClick={() => setView('automation')}>
            Automation
          </button>
          <button className={`nav-item ${view === 'search' ? 'active' : ''}`} onClick={() => setView('search')}>
            Search
          </button>

          <div
            style={{
              fontSize: 10,
              color: 'rgba(255,255,255,0.2)',
              padding: '0 16px',
              margin: '24px 0 12px',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}
          >
            Actions
          </div>

          <button className="nav-item" onClick={() => setRefreshTrigger((prev) => prev + 1)}>
            Refresh data
          </button>
          <button className={`nav-item ${view === 'chatbot' ? 'active' : ''}`} onClick={() => setView('chatbot')}>
            Assistant UniBot
          </button>

          
        </div>

        <div style={{ padding: 20, borderTop: '1px solid rgba(255,255,255,0.05)', fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, background: '#10b981', borderRadius: '50%' }}></div>
            IA Prophet v2.5 Online
          </div>
        </div>
      </nav>

      <main className={`main-content ${isEmbeddedView ? 'main-content--flush' : ''}`}>{renderCurrentView()}</main>
    </div>
  );
}

export default App;
