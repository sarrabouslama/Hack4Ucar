/**
 * Search Module
 * Handles hybrid document search across institutional data.
 */

window.SearchModule = {
    async loadAll() {
        const elResults = document.getElementById('search-results');
        if (!elResults) return;

        elResults.innerHTML = '<div style="text-align: center; padding: 40px;"><div class="loading-spinner"></div><p style="margin-top: 10px; font-size: 14px; color: var(--text-muted);">Loading institutional library...</p></div>';

        try {
            const res = await fetch('/api/v1/documents/documents');
            const data = await res.json();
            this.renderResults(data.items);
        } catch (err) {
            console.error('Failed to load documents:', err);
            elResults.innerHTML = '<div style="text-align: center; padding: 40px; color: #ef4444;"><p>Failed to load documents.</p></div>';
        }
    },

    async perform() {
        const input = document.getElementById('search-input');
        const query = input ? input.value.trim() : '';
        
        if (!query) {
            return this.loadAll();
        }
        
        const elResults = document.getElementById('search-results');
        if (!elResults) return;

        elResults.innerHTML = '<div style="text-align: center; padding: 40px;"><div class="loading-spinner"></div><p style="margin-top: 10px; font-size: 14px; color: var(--text-muted);">Searching across UCAR network...</p></div>';
        
        try {
            const res = await fetch(`/api/v1/documents/search?query=${encodeURIComponent(query)}`);
            const data = await res.json();
            this.renderResults(data.items, true);
        } catch (err) {
            console.error('Search failed:', err);
            elResults.innerHTML = '<div style="text-align: center; padding: 40px; color: #ef4444;"><p>Search failed. Please try again.</p></div>';
        }
    },

    renderResults(items, isSearch = false) {
        const elResults = document.getElementById('search-results');
        if (!elResults) return;

        if (!items.length) {
            elResults.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);"><p>${isSearch ? 'No documents found matching your query.' : 'The institutional library is empty.'}</p></div>`;
            return;
        }

        elResults.innerHTML = items.map(doc => `
            <div class="search-result-card" onclick="SearchModule.viewDetails('${doc.id}')">
                <div class="search-result-header">
                    <div>
                        <h3 class="search-result-title">${this.esc(doc.filename)}</h3>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="font-size: 11px; font-family: 'DM Mono', monospace; background: var(--cream); padding: 2px 8px; border-radius: 4px; color: var(--text-secondary);">${doc.content_type.split('/')[1].toUpperCase()}</span>
                            <span style="font-size: 11px; color: var(--text-muted);">${window.relTime ? window.relTime(doc.created_at) : ''}</span>
                        </div>
                    </div>
                    ${isSearch ? '<div style="font-size: 11px; font-weight: 500; color: var(--gold); border: 1px solid rgba(201,168,76,0.3); padding: 3px 10px; border-radius: 20px;">Ranked Result</div>' : ''}
                </div>
                <p class="search-result-excerpt">
                    ${doc.extracted_text ? `"...${this.esc(doc.extracted_text).substring(0, 200)}..."` : 'No text preview available.'}
                </p>
            </div>
        `).join('');
    },

    viewDetails(id) {
        if (window.toast) window.toast('Viewing document details...');
        // Modal logic could go here
    },

    esc(t) {
        return String(t)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }
};

// Setup global listener for enter key on search input
document.addEventListener('keydown', e => {
    if (e.target.id === 'search-input' && e.key === 'Enter') {
        SearchModule.perform();
    }
});
