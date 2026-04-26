/**
 * Automation Module
 * Handles institutional anomaly detection and mailing workflow.
 */

window.AutomationModule = {
    async loadLogs() {
        const elTable = document.getElementById('mail-logs-table');
        if (!elTable) return;
        
        elTable.innerHTML = '<tr><td colspan="4" style="padding: 20px; text-align: center;">Loading anomalies...</td></tr>';
        
        try {
            const res = await fetch('/api/v1/chatbot/mail-logs');
            const logs = await res.json();
            
            if (!logs.length) {
                elTable.innerHTML = '<tr><td colspan="4" style="padding: 30px; text-align: center; color: var(--text-muted);">No anomalies detected yet. Click "Run detection" to start.</td></tr>';
                return;
            }
            
            elTable.innerHTML = logs.map(log => {
                const statusClass = log.status === 'sent' ? 'status-sent' : 
                                  log.status === 'proposed' ? 'status-proposed' : 'status-pending';
                
                return `
                    <tr class="automation-row">
                        <td><code style="background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px;">${log.anomaly_type}</code></td>
                        <td style="font-weight: 500;">${log.anomaly_details.institution || 'Unknown'}</td>
                        <td>
                            <span class="status-badge ${statusClass}">
                                ${log.status.toUpperCase()}
                            </span>
                        </td>
                        <td>
                            ${log.status === 'proposed' ? `
                                <div style="display: flex; gap: 8px;">
                                    <button onclick="AutomationModule.proposeDraft('${log.id}')" style="padding: 6px 12px; background: var(--navy); color: var(--gold-light); border: none; border-radius: 6px; font-size: 12px; cursor: pointer;">Draft AI</button>
                                </div>
                            ` : log.status === 'confirmed' ? `
                                <span style="font-size: 12px; color: var(--text-muted);">Processing...</span>
                            ` : log.status === 'sent' ? `
                                <span style="font-size: 12px; color: #166534;">✓ Sent</span>
                            ` : `
                                <span style="font-size: 12px; color: var(--text-muted);">No action</span>
                            `}
                        </td>
                    </tr>
                    ${log.body_plan ? `
                        <tr style="background: var(--cream); border-bottom: 1px solid var(--border-mid);">
                            <td colspan="4" style="padding: 18px;">
                                <div class="draft-container">
                                    <div style="font-weight: 600; margin-bottom: 8px; color: var(--navy);">Draft for Review:</div>
                                    <div style="line-height: 1.6; color: var(--text-secondary); margin-bottom: 12px;">${window.renderMd ? window.renderMd(log.body_plan) : log.body_plan}</div>
                                    <button onclick="AutomationModule.confirmAndSend('${log.id}')" style="background: #166534; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                                        Confirm & Send
                                    </button>
                                </div>
                            </td>
                        </tr>
                    ` : ''}
                `;
            }).join('');
        } catch (err) {
            console.error('Failed to load mail logs:', err);
            elTable.innerHTML = '<tr><td colspan="4" style="padding: 20px; text-align: center; color: #ef4444;">Failed to load logs</td></tr>';
        }
    },

    async triggerDetection() {
        if (window.toast) window.toast('Running institutional anomaly detection...');
        try {
            await fetch('/api/v1/chatbot/detect-anomalies', { method: 'POST' });
            setTimeout(() => this.loadLogs(), 1500);
        } catch (err) {
            if (window.toast) window.toast('❌ Detection failed');
        }
    },

    async proposeDraft(id) {
        if (window.toast) window.toast('UniBot is drafting the email...');
        try {
            await fetch(`/api/v1/chatbot/propose-draft/${id}`, { method: 'POST' });
            this.loadLogs();
        } catch (err) {
            if (window.toast) window.toast('❌ Drafting failed');
        }
    },

    async confirmAndSend(id) {
        if (window.toast) window.toast('Queueing email for delivery...');
        try {
            await fetch(`/api/v1/chatbot/confirm-send/${id}`, { method: 'POST' });
            if (window.toast) window.toast('✓ Email scheduled');
            setTimeout(() => this.loadLogs(), 1500);
        } catch (err) {
            if (window.toast) window.toast('❌ Sending failed');
        }
    }
};
