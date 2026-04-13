
        // ============== Homestead Tab Switching ==============

        let hsActiveTab = 'feed';

        function switchHsTab(tab) {
            hsActiveTab = tab;
            document.querySelectorAll('.hs-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.hs-tab-content').forEach(c => c.classList.remove('active'));
            document.querySelector(`.hs-tab[onclick="switchHsTab('${tab}')"]`)?.classList.add('active');
            const content = document.getElementById(tab === 'feed' ? 'hsTabFeed' : 'hsTabGaps');
            if (content) content.classList.add('active');

            if (tab === 'gaps') loadHomesteadGaps();
        }

        // ============== Homestead Feed ==============

        let hsAllSessions = [];
        let hsCurrentSearch = '';

        // escapeHtml is provided by BASE_JS (sapa/gaps.py)

        async function loadHomesteadFeed() {
            try {
                const res = await fetch('/api/homestead/history?limit=100');
                hsAllSessions = await res.json();
                renderHomesteadFeed(hsAllSessions);

                const statsRes = await fetch('/api/homestead/stats');
                const stats = await statsRes.json();
                const countEl = document.getElementById('hsSessionCount');
                if (countEl) countEl.textContent = stats.session_count || 0;
            } catch (e) {
                console.error('Failed to load homestead feed:', e);
            }
        }

        function renderHomesteadFeed(sessions) {
            const container = document.getElementById('hsFeedList');
            if (!container) return;

            if (!sessions || sessions.length === 0) {
                container.innerHTML = `
                    <div class="hs-empty">
                        <div class="hs-empty-icon">&#127793;</div>
                        <p>No homestead sessions yet</p>
                        <p style="font-size: 0.8rem; margin-top: 0.5rem;">Drop .md or .txt files into the homestead inbox to get started</p>
                    </div>`;
                return;
            }

            container.innerHTML = sessions.map(s => {
                const date = s.created_at ? new Date(s.created_at).toLocaleDateString('en-US', {
                    month: 'short', day: 'numeric', year: 'numeric'
                }) : '';
                const preview = (s.response || s.prompt || '').replace(/^#\s+.+\n?/, '').substring(0, 200);
                const typeLabel = s.session_type || 'session';
                return `<div class="hs-card" onclick="showHomesteadDetail(${s.id})">
                    <div class="hs-card-title">${escapeHtml(s.topic || 'Untitled')}</div>
                    <div class="hs-card-meta">
                        <span class="hs-card-type">${escapeHtml(typeLabel)}</span>
                        <span>${date}</span>
                    </div>
                    <div class="hs-card-preview">${escapeHtml(preview)}</div>
                </div>`;
            }).join('');
        }

        function searchHomesteadFeed(query) {
            hsCurrentSearch = query.trim().toLowerCase();
            if (!hsCurrentSearch) {
                renderHomesteadFeed(hsAllSessions);
                return;
            }
            const filtered = hsAllSessions.filter(s => {
                const text = ((s.topic || '') + ' ' + (s.response || '') + ' ' + (s.notes || '')).toLowerCase();
                return text.includes(hsCurrentSearch);
            });
            renderHomesteadFeed(filtered);
        }

        async function showHomesteadDetail(entryId) {
            try {
                const res = await fetch(`/api/homestead/history/${entryId}`);
                const entry = await res.json();
                if (!entry || !entry.id) return;

                const listView = document.getElementById('hsListView');
                const detailView = document.getElementById('hsDetailView');
                const searchBar = document.querySelector('#hsTabFeed .hs-search-bar');
                if (listView) listView.style.display = 'none';
                if (searchBar) searchBar.style.display = 'none';
                if (detailView) {
                    detailView.classList.add('active');

                    const date = entry.created_at ? new Date(entry.created_at).toLocaleDateString('en-US', {
                        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
                    }) : '';

                    const typeLabel = entry.session_type || 'session';
                    const content = entry.response || entry.prompt || '';
                    const rendered = typeof marked !== 'undefined' ? marked.parse(content) : content.replace(/\n/g, '<br>');

                    detailView.innerHTML = `
                        <button class="hs-detail-back" onclick="closeHomesteadDetail()">&#8592; Back to feed</button>
                        <div class="hs-detail-header">
                            <h3>${escapeHtml(entry.topic || 'Untitled')}</h3>
                            <div class="hs-card-meta">
                                <span class="hs-card-type">${escapeHtml(typeLabel)}</span>
                                <span>${date}</span>
                            </div>
                        </div>
                        <div class="hs-detail-content">${rendered}</div>
                        <div class="hs-detail-actions">
                            <button class="hs-btn-delete" onclick="deleteHomesteadEntry(${entry.id})">Delete</button>
                        </div>`;
                }
            } catch (e) {
                console.error('Failed to load homestead detail:', e);
            }
        }

        function closeHomesteadDetail() {
            const listView = document.getElementById('hsListView');
            const detailView = document.getElementById('hsDetailView');
            const searchBar = document.querySelector('#hsTabFeed .hs-search-bar');
            if (listView) listView.style.display = '';
            if (searchBar) searchBar.style.display = '';
            if (detailView) {
                detailView.classList.remove('active');
                detailView.innerHTML = '';
            }
        }

        async function deleteHomesteadEntry(entryId) {
            if (!confirm('Delete this homestead session?')) return;
            try {
                await fetch(`/api/homestead/history/${entryId}`, { method: 'DELETE' });
                closeHomesteadDetail();
                loadHomesteadFeed();
                if (typeof showToast === 'function') showToast('Session deleted', 'success');
            } catch (e) {
                if (typeof showToast === 'function') showToast('Delete failed', 'error');
            }
        }

        // ============== Homestead Gap Analysis ==============

        async function loadHomesteadGaps() {
            try {
                const res = await fetch('/api/homestead/gap-analysis');
                const data = await res.json();
                renderHomesteadGaps(data);
                // Mirror to standalone homestead panel elements
                [['hsGapsSummary','hsGapsSummaryStandalone'],['hsTopGaps','hsTopGapsStandalone'],['hsGapsCategories','hsGapsCategoriesStandalone']].forEach(([s,d]) => {
                    const src = document.getElementById(s), dst = document.getElementById(d);
                    if (src && dst) dst.innerHTML = src.innerHTML;
                });
            } catch (e) {
                console.error('Failed to load homestead gaps:', e);
            }
        }

        // Gap rendering functions (renderHomesteadGaps, etc.) provided by generate_gap_js in plugin.py
