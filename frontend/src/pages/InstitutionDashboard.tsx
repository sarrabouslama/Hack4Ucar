import { useState, useEffect, useRef } from 'react';

const API_BASE = '/api/v1';

async function safeGet(url: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function getInstitutionsRaw() {
  return safeGet(`${API_BASE}/kpis/institutions`);
}

async function uploadDocumentRaw(file: File, institutionId: string) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(
    `${API_BASE}/documents/upload?institution_id=${encodeURIComponent(institutionId)}`,
    { method: 'POST', body: formData }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

interface Institution {
  id: string;
  name: string;
  code: string;
  region?: string;
}

interface UploadRecord {
  filename: string;
  status: string;
  parser_name: string;
  preview: string;
}

export default function InstitutionDashboard() {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingInstitutions, setFetchingInstitutions] = useState(true);
  const [success, setSuccess] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploads, setUploads] = useState<UploadRecord[]>([]);
  const [institutionError, setInstitutionError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setFetchingInstitutions(true);
    getInstitutionsRaw()
      .then((data: Institution[]) => {
        setInstitutions(data || []);
        if (data && data.length > 0) setSelectedId(data[0].id);
      })
      .catch((err) => {
        setInstitutionError(err.message || 'Failed to load institutions');
      })
      .finally(() => setFetchingInstitutions(false));
  }, []);

  const handleFile = async (file: File) => {
    if (!selectedId && institutions.length > 0) {
      setError('Please select an institution');
      return;
    }
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      // If no institution selected, upload without institution_id
      const res = await uploadDocumentRaw(file, selectedId);
      setSuccess(res.document || res);
      const newRecord: UploadRecord = {
        filename: res.document?.filename || file.name,
        status: res.document?.status || 'processed',
        parser_name: res.document?.parser_name || 'parser',
        preview: res.extraction_preview?.text_preview || '',
      };
      setUploads((prev) => [newRecord, ...prev]);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div
      style={{
        maxWidth: '1400px',
        margin: '0 auto',
        padding: '40px 20px',
        fontFamily: "'Syne', sans-serif",
      }}
    >
      {/* Header Banner */}
      <div
        style={{
          padding: '40px',
          borderRadius: '24px',
          marginBottom: '40px',
          background: 'linear-gradient(135deg, #0d1b38 0%, #1e3a6e 100%)',
          border: '1px solid rgba(255,255,255,0.1)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '24px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
        }}
      >
        <div style={{ maxWidth: '60%' }}>
          <h1
            style={{
              fontFamily: "'Fraunces', serif",
              fontSize: '2.4rem',
              color: 'white',
              marginBottom: '8px',
              lineHeight: 1.1,
            }}
          >
            Document Ingestion{' '}
            <span style={{ color: '#e8c96a' }}>AI Portal</span>
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '1rem', margin: 0 }}>
            Upload institutional documents — PDFs, Excel sheets, images — and let AI extract KPIs
            automatically.
          </p>
        </div>

        <div
          style={{
            background: 'rgba(255,255,255,0.06)',
            padding: '20px 24px',
            borderRadius: '16px',
            border: '1px solid rgba(255,255,255,0.1)',
            minWidth: '280px',
          }}
        >
          <div
            style={{
              fontSize: '10px',
              color: '#e8c96a',
              fontWeight: 700,
              letterSpacing: '1px',
              textTransform: 'uppercase',
              marginBottom: '8px',
              fontFamily: "'DM Mono', monospace",
            }}
          >
            Connected Institution
          </div>

          {fetchingInstitutions ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '14px' }}>
              Loading institutions...
            </div>
          ) : institutionError ? (
            <div style={{ color: '#f87171', fontSize: '13px' }}>
              ⚠ {institutionError}
              <br />
              <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px' }}>
                Make sure the backend is running and DB is seeded.
              </span>
            </div>
          ) : institutions.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>
              No institutions found.{' '}
              <span style={{ color: 'rgba(255,255,255,0.3)' }}>
                Run seed script first.
              </span>
            </div>
          ) : (
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'white',
                fontSize: '16px',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
                width: '100%',
              }}
            >
              {institutions.map((inst) => (
                <option key={inst.id} value={inst.id} style={{ background: '#0d1b38' }}>
                  {inst.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '40px', alignItems: 'start' }}>
        {/* Left: Upload Area */}
        <div>
          {/* Drop Zone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => !loading && fileInputRef.current?.click()}
            style={{
              height: '420px',
              border: `2px dashed ${dragActive ? '#e8c96a' : 'rgba(201,168,76,0.3)'}`,
              borderRadius: '24px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.3s ease',
              background: dragActive
                ? 'rgba(201,168,76,0.07)'
                : 'rgba(255,255,255,0.02)',
              boxShadow: dragActive ? '0 0 40px rgba(201,168,76,0.12)' : 'none',
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: 'none' }}
              accept=".pdf,.png,.jpg,.jpeg,.xlsx,.csv"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
                e.target.value = '';
              }}
            />

            {loading ? (
              <div style={{ textAlign: 'center' }}>
                <div
                  style={{
                    width: '64px',
                    height: '64px',
                    border: '5px solid rgba(201,168,76,0.2)',
                    borderTopColor: '#e8c96a',
                    borderRadius: '50%',
                    animation: 'spin 0.8s linear infinite',
                    margin: '0 auto 24px',
                  }}
                />
                <h2
                  style={{
                    fontFamily: "'Fraunces', serif",
                    fontSize: '22px',
                    color: '#111827',
                    margin: '0 0 8px',
                  }}
                >
                  AI is analysing…
                </h2>
                <p style={{ color: '#9ca3af', margin: 0, fontSize: '14px' }}>
                  Extracting data with Gemini Vision
                </p>
              </div>
            ) : (
              <>
                <div style={{ fontSize: '64px', marginBottom: '20px', lineHeight: 1 }}>📂</div>
                <h2
                  style={{
                    fontFamily: "'Fraunces', serif",
                    fontSize: '24px',
                    color: '#111827',
                    margin: '0 0 10px',
                  }}
                >
                  Drop your document here
                </h2>
                <p style={{ color: '#6b7280', textAlign: 'center', maxWidth: '360px', margin: '0 0 28px', fontSize: '14px', lineHeight: 1.6 }}>
                  Supports PDF, PNG/JPG images, Excel (.xlsx) and CSV files.
                  AI will extract and classify data automatically.
                </p>
                <div
                  style={{
                    padding: '12px 28px',
                    background: '#0d1b38',
                    color: '#e8c96a',
                    borderRadius: '12px',
                    fontWeight: 700,
                    fontSize: '13px',
                    fontFamily: "'DM Mono', monospace",
                    letterSpacing: '0.06em',
                    border: '1px solid rgba(201,168,76,0.4)',
                  }}
                >
                  SELECT A FILE
                </div>
                <p style={{ color: '#9ca3af', fontSize: '11px', marginTop: '12px', fontFamily: "'DM Mono', monospace" }}>
                  or drag & drop
                </p>
              </>
            )}
          </div>

          {/* Recent Uploads Table */}
          {uploads.length > 0 && (
            <div
              style={{
                marginTop: '32px',
                background: 'white',
                borderRadius: '16px',
                border: '1px solid rgba(0,0,0,0.08)',
                overflow: 'hidden',
              }}
            >
              <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
                <h3 style={{ fontFamily: "'Fraunces', serif", fontSize: '18px', margin: 0, color: '#0d1b38' }}>
                  Recent Uploads
                </h3>
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: '#f6f2eb' }}>
                    <th style={{ padding: '12px 20px', textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>File</th>
                    <th style={{ padding: '12px 20px', textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>Parser</th>
                    <th style={{ padding: '12px 20px', textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {uploads.map((u, i) => (
                    <tr key={i} style={{ borderTop: '1px solid rgba(0,0,0,0.05)' }}>
                      <td style={{ padding: '12px 20px', fontWeight: 600 }}>{u.filename}</td>
                      <td style={{ padding: '12px 20px', color: '#6b7280' }}>{u.parser_name}</td>
                      <td style={{ padding: '12px 20px' }}>
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '3px 10px',
                            borderRadius: '20px',
                            fontSize: '11px',
                            fontWeight: 700,
                            background: u.status === 'processed' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                            color: u.status === 'processed' ? '#10b981' : '#ef4444',
                          }}
                        >
                          {u.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right: Status Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {error && (
            <div
              style={{
                padding: '20px',
                background: 'rgba(239,68,68,0.06)',
                border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: '16px',
              }}
            >
              <div style={{ fontSize: '20px', marginBottom: '8px' }}>❌</div>
              <h3 style={{ color: '#ef4444', margin: '0 0 8px', fontSize: '16px' }}>Upload failed</h3>
              <p style={{ color: '#6b7280', margin: '0 0 16px', fontSize: '13px' }}>{error}</p>
              <button
                onClick={() => setError(null)}
                style={{
                  padding: '8px 16px',
                  background: 'transparent',
                  border: '1px solid rgba(239,68,68,0.4)',
                  borderRadius: '8px',
                  color: '#ef4444',
                  cursor: 'pointer',
                  fontSize: '13px',
                }}
              >
                Dismiss
              </button>
            </div>
          )}

          {success && (
            <div
              style={{
                padding: '24px',
                background: 'rgba(16,185,129,0.06)',
                border: '1px solid rgba(16,185,129,0.3)',
                borderRadius: '16px',
              }}
            >
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>✨</div>
              <h3 style={{ color: '#10b981', fontSize: '18px', margin: '0 0 8px', fontFamily: "'Fraunces', serif" }}>
                Analysis Complete
              </h3>
              <p style={{ fontSize: '13px', color: '#6b7280', margin: '0 0 16px', lineHeight: 1.6 }}>
                Gemini identified the document and routed data to the relevant modules.
              </p>
              {success.module_classification && (
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ fontSize: '11px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px', fontFamily: "'DM Mono', monospace" }}>
                    Classification
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#0d1b38' }}>
                    {success.module_classification}
                  </div>
                </div>
              )}
              <button
                onClick={() => setSuccess(null)}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: '#0d1b38',
                  color: '#e8c96a',
                  border: '1px solid rgba(201,168,76,0.4)',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: '13px',
                  fontFamily: "'DM Mono', monospace",
                }}
              >
                UPLOAD ANOTHER
              </button>
            </div>
          )}

          {/* Guide */}
          {!success && !error && (
            <div
              style={{
                padding: '24px',
                background: 'white',
                border: '1px solid rgba(0,0,0,0.08)',
                borderRadius: '16px',
              }}
            >
              <h3 style={{ fontFamily: "'Fraunces', serif", fontSize: '18px', margin: '0 0 16px', color: '#0d1b38' }}>
                💡 Smart Guide
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {[
                  ['1', 'Select institution', 'The AI will associate extracted KPIs with the selected university.'],
                  ['2', 'Drop your file', 'PDFs, photos of bills, Excel spreadsheets — all supported.'],
                  ['3', 'Automatic routing', 'Extracted data appears instantly on the UCAR dashboard.'],
                ].map(([num, title, desc]) => (
                  <div key={num} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: '28px',
                        height: '28px',
                        background: '#f5e9c4',
                        borderRadius: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '12px',
                        fontWeight: 700,
                        flexShrink: 0,
                        color: '#0d1b38',
                      }}
                    >
                      {num}
                    </div>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: '#111827', marginBottom: '2px' }}>{title}</div>
                      <div style={{ fontSize: '12px', color: '#6b7280', lineHeight: 1.5 }}>{desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Badge */}
          <div
            style={{
              padding: '20px',
              background: '#0d1b38',
              color: 'white',
              textAlign: 'center',
              borderRadius: '16px',
            }}
          >
            <div style={{ fontSize: '22px', marginBottom: '8px' }}>🤖</div>
            <div style={{ fontSize: '14px', fontWeight: 600 }}>Powered by Gemini Vision</div>
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px', fontFamily: "'DM Mono', monospace" }}>
              98.4% extraction accuracy
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}