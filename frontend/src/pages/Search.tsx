import React, { useEffect, useState } from 'react';
import { listDocuments, searchDocuments } from '../api/documentsApi';

interface SearchResult {
  id: string;
  filename: string;
  content_type: string;
  created_at: string;
  extracted_text?: string;
}

const Search: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const loadAll = async () => {
    setLoading(true);
    try {
      const res = await listDocuments();
      setResults(res.data.items || []);
    } catch (err) {
      console.error('Failed to load documents', err);
    } finally {
      setLoading(false);
    }
  };

  const performSearch = async () => {
    if (!query.trim()) {
      setHasSearched(false);
      await loadAll();
      return;
    }

    setLoading(true);
    setHasSearched(true);

    try {
      const res = await searchDocuments(query.trim());
      setResults(res.data.items || []);
    } catch (err) {
      console.error('Search failed', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  return (
    <div className="main module-panel">
      <div className="chat-header">
        <div className="header-left">
          <div className="header-title">Institutional Search</div>
          <div className="header-status">
            <span className="status-dot"></span>
            Online · Global index
          </div>
        </div>
      </div>

      <div className="view-content view-content--scroll">
        <div className="search-container" style={{ maxWidth: '800px', margin: '0 auto' }}>
          <h2 style={{ fontFamily: "'Fraunces', serif", fontWeight: 400, fontSize: '24px', marginBottom: '20px' }}>Knowledge Base Explorer</h2>

          <div
            className="input-box"
            style={{
              marginBottom: '30px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              background: 'var(--cream)',
              border: '1px solid var(--border-mid)',
              borderRadius: 'var(--radius-lg)',
              padding: '10px 12px',
            }}
          >
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && performSearch()}
              placeholder="Search across all institutional documents..."
              style={{ flex: 1, border: 'none', background: 'transparent', fontFamily: "'Syne', sans-serif", outline: 'none', padding: '5px' }}
            />
            <button
              onClick={performSearch}
              className="send-btn"
              style={{ width: '34px', height: '34px', background: 'var(--navy)', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              type="button"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div className="loading-spinner"></div>
                <p style={{ marginTop: '10px', fontSize: '14px', color: 'var(--text-muted)' }}>Searching across UCAR network...</p>
              </div>
            ) : results.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                <p>{hasSearched ? 'No documents found matching your query.' : 'The institutional library is empty.'}</p>
              </div>
            ) : (
              results.map((doc) => (
                <div key={doc.id} className="search-result-card" style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '18px', cursor: 'pointer', marginBottom: '16px' }}>
                  <div className="search-result-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                    <div>
                      <h3 className="search-result-title" style={{ fontSize: '15px', fontWeight: 600, color: 'var(--navy)', marginBottom: '2px' }}>
                        {doc.filename}
                      </h3>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <span style={{ fontSize: '11px', fontFamily: "'DM Mono', monospace", background: 'var(--cream)', padding: '2px 8px', borderRadius: '4px', color: 'var(--text-secondary)' }}>
                          {doc.content_type?.split('/')[1]?.toUpperCase() || 'DOC'}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    {hasSearched && (
                      <div style={{ fontSize: '11px', fontWeight: 500, color: 'var(--gold)', border: '1px solid rgba(201,168,76,0.3)', padding: '3px 10px', borderRadius: '20px' }}>
                        Ranked result
                      </div>
                    )}
                  </div>
                  <p className="search-result-excerpt" style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.6, fontStyle: 'italic' }}>
                    {doc.extracted_text ? `"${doc.extracted_text.substring(0, 200)}..."` : 'No text preview available.'}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Search;
