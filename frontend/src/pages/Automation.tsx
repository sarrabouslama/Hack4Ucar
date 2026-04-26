import React, { useEffect, useState } from 'react';
import { confirmMailSend, getMailLogs, requestDraft, triggerAnomalyDetection } from '../api/chatbotApi';

interface MailLog {
  id: string;
  anomaly_type: string;
  anomaly_details: Record<string, unknown>;
  status: string;
  body_plan?: string;
}

const Automation: React.FC = () => {
  const [logs, setLogs] = useState<MailLog[]>([]);
  const [loading, setLoading] = useState(false);

  const loadLogs = async () => {
    try {
      const res = await getMailLogs();
      setLogs(res.data);
    } catch (err) {
      console.error('Failed to load logs', err);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const triggerDetection = async () => {
    setLoading(true);
    try {
      await triggerAnomalyDetection();
      setTimeout(loadLogs, 1500);
    } catch (err) {
      console.error('Detection failed', err);
    } finally {
      setLoading(false);
    }
  };

  const proposeDraft = async (id: string) => {
    try {
      await requestDraft(id);
      await loadLogs();
    } catch (err) {
      console.error('Drafting failed', err);
    }
  };

  const confirmAndSend = async (id: string) => {
    try {
      await confirmMailSend(id);
      setTimeout(loadLogs, 1500);
    } catch (err) {
      console.error('Sending failed', err);
    }
  };

  return (
    <div className="main module-panel">
      <div className="chat-header">
        <div className="header-left">
          <div className="header-title">Mailing Automation</div>
          <div className="header-status">
            <span className="status-dot"></span>
            Online · Monitoring
          </div>
        </div>
      </div>

      <div className="view-content view-content--scroll">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ fontFamily: "'Fraunces', serif", fontWeight: 400, fontSize: '24px' }}>Institutional Workflow</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
              Monitor anomalies and manage automated institutional communication.
            </p>
          </div>
          <button onClick={triggerDetection} disabled={loading} className="new-btn new-btn--inline" type="button">
            {loading ? 'Running...' : 'Run detection'}
          </button>
        </div>

        <div style={{ background: 'var(--white)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
          <table className="automation-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13.5px' }}>
            <thead style={{ background: 'var(--cream)', borderBottom: '1px solid var(--border)' }}>
              <tr>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-secondary)' }}>Anomaly Type</th>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-secondary)' }}>Target Institution</th>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-secondary)' }}>Status</th>
                <th style={{ padding: '14px 18px', fontWeight: 600, color: 'var(--text-secondary)' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No anomalies detected yet
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const hasDraft = Boolean(log.body_plan);

                  return (
                    <React.Fragment key={log.id}>
                      <tr className="automation-row" style={{ borderBottom: '1px solid var(--border-mid)' }}>
                        <td style={{ padding: '14px 18px' }}>
                          <code style={{ background: 'rgba(0,0,0,0.05)', padding: '2px 6px', borderRadius: '4px' }}>{log.anomaly_type}</code>
                        </td>
                        <td style={{ padding: '14px 18px', fontWeight: 500 }}>{String(log.anomaly_details?.institution || 'Unknown')}</td>
                        <td style={{ padding: '14px 18px' }}>
                          <span
                            className={`status-badge ${log.status === 'sent' ? 'status-sent' : log.status === 'proposed' ? 'status-proposed' : 'status-pending'}`}
                            style={{
                              fontSize: '11px',
                              fontWeight: 600,
                              padding: '4px 8px',
                              borderRadius: '20px',
                              background: log.status === 'sent' ? '#dcfce7' : log.status === 'proposed' ? '#fef08a' : '#e5e7eb',
                              color: log.status === 'sent' ? '#166534' : log.status === 'proposed' ? '#854d0e' : '#374151',
                            }}
                          >
                            {log.status.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '14px 18px' }}>
                          {!hasDraft && log.status === 'proposed' ? (
                            <button
                              onClick={() => proposeDraft(log.id)}
                              style={{ padding: '6px 12px', background: 'var(--navy)', color: 'var(--gold-light)', border: 'none', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}
                              type="button"
                            >
                              Draft AI
                            </button>
                          ) : hasDraft && log.status === 'proposed' ? (
                            <button
                              onClick={() => confirmAndSend(log.id)}
                              style={{ background: '#166534', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}
                              type="button"
                            >
                              Confirm & Send
                            </button>
                          ) : log.status === 'confirmed' ? (
                            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Processing...</span>
                          ) : log.status === 'sent' ? (
                            <span style={{ fontSize: '12px', color: '#166534' }}>Sent</span>
                          ) : (
                            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No action</span>
                          )}
                        </td>
                      </tr>

                      {hasDraft && (
                        <tr style={{ background: 'var(--cream)', borderBottom: '1px solid var(--border-mid)' }}>
                          <td colSpan={4} style={{ padding: '18px' }}>
                            <div className="draft-container">
                              <div style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--navy)' }}>Draft for Review</div>
                              <div style={{ lineHeight: 1.6, color: 'var(--text-secondary)', marginBottom: '12px', whiteSpace: 'pre-wrap' }}>{log.body_plan}</div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Automation;
