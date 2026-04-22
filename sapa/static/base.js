
        // Theme management
        function initTheme() {
            const savedTheme = localStorage.getItem('health-bot-theme') || 'dark';
            document.documentElement.setAttribute('data-theme', savedTheme);
            updateThemeToggleText(savedTheme);
        }

        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('health-bot-theme', newTheme);
            updateThemeToggleText(newTheme);
        }

        function updateThemeToggleText(theme) {
            const el = document.getElementById('themeToggleText');
            if (el) el.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
        }

        initTheme();

        // Toast
        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.style.borderColor = type === 'error' ? '#ef4444' : type === 'success' ? 'var(--accent)' : 'var(--border)';
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        // Settings
        function toggleSettings() {
            const menu = document.getElementById('settingsMenu');
            const isOpen = menu.style.display === 'block';
            menu.style.display = isOpen ? 'none' : 'block';
            document.getElementById('settingsBtn').setAttribute('aria-expanded', !isOpen);
        }

        document.addEventListener('click', function(e) {
            const wrap = document.querySelector('.settings-wrapper');
            if (wrap && !wrap.contains(e.target)) {
                document.getElementById('settingsMenu').style.display = 'none';
            }
        });

        // Tab switching
        const PROFILE_TABS = $PROFILE_TABS_JSON$;

        function updateTabVisibility() {
            const pid = currentProfileId;
            const allowed = PROFILE_TABS[pid] || PROFILE_TABS['default'] || [];
            document.querySelectorAll('.tab, .nav-tab-direct').forEach(btn => {
                const panel = btn.getAttribute('data-panel');
                if (!panel || panel === 'dashboard' || panel === 'hermes') return;
                const show = allowed.length === 0 || allowed.includes(panel);
                btn.style.display = show ? '' : 'none';
            });
            // Hide nav groups that have no visible children (except category selector)
            document.querySelectorAll('.nav-item[data-category]').forEach(item => {
                const dropdown = item.querySelector('.nav-dropdown');
                if (!dropdown) return;
                const visibleTabs = dropdown.querySelectorAll('.tab:not([style*="display: none"])');
                item.style.display = visibleTabs.length > 0 ? '' : 'none';
            });
        }

        // Dashboard tab switching (Feed / Family / Gaps / Analytics)
        function switchDashTab(tab) {
            document.querySelectorAll('.dash-tab').forEach(t => t.classList.remove('active'));
            document.querySelector(`.dash-tab[onclick="switchDashTab('${tab}')"]`)?.classList.add('active');
            document.getElementById('dashTabFeed').style.display = tab === 'feed' ? 'block' : 'none';
            document.getElementById('dashTabFamily').style.display = tab === 'family' ? 'block' : 'none';
            document.getElementById('dashTabGaps').style.display = tab === 'gaps' ? 'block' : 'none';
            document.getElementById('dashTabAnalytics').style.display = tab === 'analytics' ? 'block' : 'none';
            if (tab === 'family' && typeof loadFamilyFeed === 'function') loadFamilyFeed();
        }

        // Gap tab switching (Health / Homestead within gaps)
        function switchGapTab(tab) {
            document.querySelectorAll('.gap-tab').forEach(t => t.classList.remove('active'));
            document.querySelector(`.gap-tab[onclick="switchGapTab('${tab}')"]`)?.classList.add('active');
            document.getElementById('gapTabHealth').style.display = tab === 'health' ? 'block' : 'none';
            document.getElementById('gapTabHomestead').style.display = tab === 'homestead' ? 'block' : 'none';
            if (tab === 'homestead' && typeof loadHomesteadGaps === 'function') loadHomesteadGaps();
        }

        // Unified sessions
        let _unifiedSessions = [];
        let _unifiedFilterTimer = null;

        function debouncedFilterUnifiedSessions() {
            clearTimeout(_unifiedFilterTimer);
            _unifiedFilterTimer = setTimeout(filterUnifiedSessions, 200);
        }

        async function loadUnifiedSessions() {
            try {
                const [healthRes, hsRes] = await Promise.all([
                    fetch('/api/history?limit=200'),
                    fetch('/api/homestead/history?limit=200')
                ]);
                const healthData = await healthRes.json();
                const hsData = await hsRes.json();

                // Tag each entry with category
                const healthEntries = (healthData || []).map(h => ({
                    ...h,
                    _category: 'health',
                    _sortDate: h.created_at || ''
                }));
                const hsEntries = (hsData || []).map(h => ({
                    ...h,
                    _category: 'homestead',
                    _sortDate: h.created_at || ''
                }));

                _unifiedSessions = [...healthEntries, ...hsEntries];
                // Populate filters from actual data
                populateUnifiedTypeFilter();
                // Populate topic list for combo filter
                const allTopics = new Set();
                _unifiedSessions.forEach(s => (s.topics || []).forEach(t => allTopics.add(t)));
                _sessionTopicsList = [...allTopics].sort((a, b) => a.localeCompare(b));
                filterUnifiedSessions();
            } catch (e) {
                console.error('Failed to load unified sessions:', e);
            }
        }

        function populateUnifiedTypeFilter() {
            const types = new Set();
            _unifiedSessions.forEach(s => {
                const t = s.session_type || s.type || 'session';
                types.add(t);
            });
            const select = document.getElementById('sessionTypeFilter');
            if (!select) return;
            const current = select.value;
            select.innerHTML = '<option value="">All Types</option>' +
                [...types].sort().map(t =>
                    `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`
                ).join('');
            select.value = current;
        }

        function filterUnifiedSessions() {
            const search = (document.getElementById('sessionSearch')?.value || '').toLowerCase();
            const catFilter = document.getElementById('sessionCategoryFilter')?.value || '';
            const typeFilter = document.getElementById('sessionTypeFilter')?.value || '';
            const topicFilter = (typeof _selectedTopic !== 'undefined') ? _selectedTopic : '';
            const sortVal = document.getElementById('sessionSortFilter')?.value || 'newest';

            let filtered = _unifiedSessions.slice();

            if (catFilter) {
                filtered = filtered.filter(s => s._category === catFilter);
            }
            if (search) {
                filtered = filtered.filter(s =>
                    (s.topic || '').toLowerCase().includes(search) ||
                    (s.response || '').toLowerCase().includes(search) ||
                    (s.session_type || '').toLowerCase().includes(search)
                );
            }
            if (typeFilter) {
                filtered = filtered.filter(s => (s.session_type || s.type || 'session') === typeFilter);
            }
            if (topicFilter) {
                filtered = filtered.filter(s => (s.topics || []).includes(topicFilter));
            }

            switch (sortVal) {
                case 'oldest':
                    filtered.sort((a, b) => (a._sortDate || '').localeCompare(b._sortDate || ''));
                    break;
                case 'az':
                    filtered.sort((a, b) => (a.topic || '').localeCompare(b.topic || ''));
                    break;
                case 'za':
                    filtered.sort((a, b) => (b.topic || '').localeCompare(a.topic || ''));
                    break;
                default:
                    filtered.sort((a, b) => (b._sortDate || '').localeCompare(a._sortDate || ''));
            }

            const countEl = document.getElementById('sessionResultCount');
            if (search || catFilter || typeFilter || topicFilter) {
                countEl.textContent = filtered.length + ' of ' + _unifiedSessions.length + ' sessions';
            } else {
                countEl.textContent = _unifiedSessions.length + ' sessions';
            }

            renderUnifiedSessions(filtered);
        }

        function renderUnifiedSessions(sessions) {
            const container = document.getElementById('allSessions');
            if (!container) return;

            if (sessions.length === 0) {
                container.innerHTML = '<div class="hs-empty"><div class="hs-empty-icon">📋</div><p>No sessions match your filters.</p></div>';
                return;
            }

            container.innerHTML = sessions.map(s => {
                const date = s.created_at ? new Date(s.created_at + 'Z').toLocaleDateString('en-US', {
                    month: 'short', day: 'numeric', year: 'numeric'
                }) : '';
                const preview = (s.response || s.prompt || '').replace(/^#\s+.+\n?/, '').substring(0, 200);
                const typeLabel = s.session_type || s.type || 'session';
                const catBadge = s._category === 'homestead'
                    ? '<span class="category-badge homestead">Homestead</span>'
                    : '<span class="category-badge health">Health</span>';
                const clickHandler = s._category === 'homestead'
                    ? `showHomesteadInModal(${s.id})`
                    : `showHistoryEntry(${s.id})`;
                return `<div class="hs-card" onclick="${clickHandler}">
                    <div class="hs-card-title">${escapeHtml(s.topic || 'Untitled')}</div>
                    <div class="hs-card-meta">
                        ${catBadge}
                        <span class="hs-card-type">${escapeHtml(typeLabel)}</span>
                        <span>${date}</span>
                    </div>
                    <div class="hs-card-preview">${escapeHtml(preview)}</div>
                </div>`;
            }).join('');
        }

        function switchPanel(panel) {
            if (!panel) return;
            // Update active states on nav buttons
            document.querySelectorAll('.tab, .nav-tab-direct').forEach(b => b.classList.remove('active'));
            const navBtn = document.querySelector(`[data-panel="${panel}"]`);
            if (navBtn) navBtn.classList.add('active');
            // Also highlight parent nav-btn if in dropdown
            document.querySelectorAll('.nav-item[data-category] .nav-btn').forEach(b => b.classList.remove('active'));
            if (navBtn) {
                const parentItem = navBtn.closest('.nav-item[data-category]');
                if (parentItem) {
                    const pb = parentItem.querySelector('.nav-btn');
                    if (pb) pb.classList.add('active');
                }
            }
            // Show panel
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            const target = document.getElementById(panel);
            if (target) target.classList.add('active');
            window.scrollTo(0, 0);
        }

        document.querySelectorAll('.tab, .nav-tab-direct').forEach(btn => {
            btn.addEventListener('click', () => {
                const panel = btn.getAttribute('data-panel');
                switchPanel(panel);
                // Plugin lazy-load hooks
                if (panel === 'recipes' && typeof loadRecipes === 'function' && typeof allRecipes !== 'undefined' && allRecipes.length === 0) loadRecipes();
                if (panel === 'mealplanner') { if (typeof loadMealPlanner === 'function') loadMealPlanner(); if (typeof loadGroceryList === 'function') loadGroceryList(); }
                if (panel === 'calendar' && typeof loadCalendar === 'function') loadCalendar();
            });
        });

        // Profile management
        let currentProfileId = parseInt(localStorage.getItem('health-bot-profile') || document.cookie.match(/profile_id=(\d+)/)?.[1] || '1');

        async function loadProfiles() {
            try {
                document.cookie = `profile_id=${currentProfileId}; path=/; max-age=31536000`;
                const res = await fetch('/api/profiles');
                const profiles = await res.json();
                const select = document.getElementById('profileSelect');
                if (!select) return;
                const esc = typeof escapeHtml === 'function' ? escapeHtml : (t => t);
                select.innerHTML = profiles.map(p =>
                    `<option value="${p.id}" ${p.id === currentProfileId ? 'selected' : ''}>${esc(p.display_name)}</option>`
                ).join('');
                document.documentElement.setAttribute('data-profile', currentProfileId);
                if (typeof applyProfileTheme === 'function') applyProfileTheme(currentProfileId);
                if (typeof updateBodyMapSelector === 'function') updateBodyMapSelector();
                const current = profiles.find(p => p.id === currentProfileId);
            } catch (e) {
                console.error('Failed to load profiles:', e);
            }
        }

        function switchProfile(profileId) {
            if (!profileId) return;
            profileId = parseInt(profileId);
            currentProfileId = profileId;
            document.cookie = `profile_id=${profileId}; path=/; max-age=31536000`;
            localStorage.setItem('health-bot-profile', profileId.toString());
            document.documentElement.setAttribute('data-profile', profileId);
            fetch(`/api/profiles/current/${profileId}`, { method: 'PUT' });
            if (typeof applyProfileTheme === 'function') applyProfileTheme(profileId);
            if (typeof updateBodyMapSelector === 'function') updateBodyMapSelector();
            updateTabVisibility();
            const select = document.getElementById('profileSelect');
            const profileName = select?.options[select.selectedIndex]?.text || 'profile';
            if (typeof showToast === 'function') showToast('Switched to ' + profileName, 'success');
            // Reload all data
            if (typeof loadDashboard === 'function') loadDashboard();
            if (typeof loadHulkData === 'function') loadHulkData();
            // Reload recipes (favorites/cook-log are profile-scoped)
            if (typeof loadRecipes === 'function') loadRecipes();
        }

        // Show homestead entries in the session modal
        async function showHomesteadInModal(entryId) {
            try {
                const res = await fetch('/api/homestead/history/' + entryId);
                const entry = await res.json();
                if (!entry || !entry.id) return;

                currentHistoryId = null;
                currentSession = { topic: entry.topic, name: null, historyId: null, _homesteadId: entry.id };

                document.getElementById('modalTitle').textContent = entry.topic || 'Homestead Session';
                const content = entry.response || entry.prompt || '';
                document.getElementById('modalContentMd').innerHTML = marked.parse(content);
                document.getElementById('modalContentMd').style.display = 'block';
                document.getElementById('modalTopics').innerHTML = '<span class="category-badge homestead" style="margin-right:0.5rem;">Homestead</span>' +
                    '<span class="session-type">' + escapeHtml(entry.session_type || 'session') + '</span>';
                lastFocusedElement = document.activeElement;
                const modal = document.getElementById('sessionModal');
                modal.classList.add('show');
                setTimeout(() => {
                    modal.scrollTo(0, 0);
                    const mc = modal.querySelector('.modal-content');
                    if (mc) mc.scrollTo(0, 0);
                }, 0);
                modal.querySelector('.close-btn')?.focus();
            } catch (e) {
                console.error('Failed to load homestead entry:', e);
            }
        }

        // WebSocket
        let ws = null;
        let wsReconnectTimer = null;
        let _wsRefreshTimer = null;
        let _wsWasConnected = false;

        function _debouncedRefresh() {
            if (_wsRefreshTimer) clearTimeout(_wsRefreshTimer);
            _wsRefreshTimer = setTimeout(() => {
                if (typeof loadDashboard === 'function') loadDashboard();
            }, 500);
        }

        function connectWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                if (wsReconnectTimer) {
                    clearTimeout(wsReconnectTimer);
                    wsReconnectTimer = null;
                }
                if (_wsWasConnected) {
                    console.log('WebSocket reconnected after disconnect — reloading page');
                    window.location.reload();
                    return;
                }
                _wsWasConnected = true;
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.event === 'file_created' || msg.event === 'file_processed' ||
                    msg.event === 'homestead_file_created' || msg.event === 'file_modified') {
                    _debouncedRefresh();
                } else if (msg.event === 'ping') {
                    // Keep-alive
                }
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                wsReconnectTimer = setTimeout(connectWebSocket, 5000);
            };

            ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                ws.close();
            };
        }

        // Rescan files
        async function rescanFiles() {
            try {
                const res = await fetch('/api/rescan', { method: 'POST' });
                const data = await res.json();
                showToast(`Rescanned ${data.files_scanned} files, ${data.topics_recorded} topics`, 'success');
                if (data.topics_recorded > 0 && typeof loadDashboard === 'function') loadDashboard();
            } catch (e) {
                showToast('Rescan failed', 'error');
            }
        }

        // Content search (server-side, Enter key)
        let _searchMode = false;

        async function serverSearch(query) {
            if (!query || query.length < 3) {
                if (_searchMode) exitSearchMode();
                return;
            }
            _searchMode = true;
            try {
                const res = await fetch('/api/search?q=' + encodeURIComponent(query) + '&limit=50');
                const results = await res.json();
                const container = document.getElementById('allSessions');
                const countEl = document.getElementById('sessionResultCount');
                if (countEl) countEl.textContent = results.length + ' search results for "' + query + '"';
                if (!container) return;
                if (results.length === 0) {
                    container.innerHTML = '<div class="hs-empty"><div class="hs-empty-icon">&#128269;</div><p>No results for "' + escapeHtml(query) + '"</p></div>';
                    return;
                }
                container.innerHTML = results.map(r => {
                    const date = r.created_at ? new Date(r.created_at + 'Z').toLocaleDateString('en-US', {month:'short',day:'numeric',year:'numeric'}) : '';
                    const catBadge = r.category === 'homestead'
                        ? '<span class="category-badge homestead">Homestead</span>'
                        : '<span class="category-badge health">Health</span>';
                    const snippet = highlightSnippet(escapeHtml(r.snippet || ''), query);
                    const clickHandler = r.category === 'homestead'
                        ? 'showHomesteadInModal(' + r.id + ')'
                        : 'showHistoryEntry(' + r.id + ')';
                    return '<div class="hs-card" onclick="' + clickHandler + '">' +
                        '<div class="hs-card-title">' + escapeHtml(r.topic || 'Untitled') + '</div>' +
                        '<div class="hs-card-meta">' + catBadge +
                        '<span class="hs-card-type">' + escapeHtml(r.session_type || 'session') + '</span>' +
                        (r.profile_name ? '<span>' + escapeHtml(r.profile_name) + '</span>' : '') +
                        '<span>' + date + '</span></div>' +
                        '<div class="hs-card-preview">' + snippet + '</div></div>';
                }).join('');
            } catch (e) {
                console.error('Search failed:', e);
                showToast('Search failed', 'error');
            }
        }

        function highlightSnippet(text, query) {
            if (!query) return text;
            const re = new RegExp('(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
            return text.replace(re, '<mark>$1</mark>');
        }

        function exitSearchMode() {
            _searchMode = false;
            filterUnifiedSessions();
        }

        // Attach Enter-key handler to session search
        document.addEventListener('DOMContentLoaded', function() {
            const searchInput = document.getElementById('sessionSearch');
            if (searchInput) {
                searchInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        const q = this.value.trim();
                        if (q.length >= 3) serverSearch(q);
                        else if (_searchMode) exitSearchMode();
                    }
                });
            }
        });

        // PWA: Register service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(err =>
                console.log('SW registration failed:', err)
            );
        }

        // Offline indicator
        function updateOnlineStatus() {
            const wrap = document.getElementById('liveIndicatorWrap');
            if (!wrap) return;
            const dot = wrap.querySelector('.live-dot');
            const label = wrap.querySelector('span');
            if (navigator.onLine) {
                if (dot) dot.style.background = '';
                if (label) label.textContent = 'Watching for new sessions';
            } else {
                if (dot) dot.style.background = '#f59e0b';
                if (label) label.textContent = 'Offline';
            }
        }
        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);
