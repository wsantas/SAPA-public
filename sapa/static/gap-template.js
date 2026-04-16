
        // ===== $PLUGIN_ID$ Gap Analysis =====

        const $PLUGIN_VAR$GapPrompts = $PROMPTS_JSON$;
        const $PLUGIN_VAR$GapDefaultPrompt = $DEFAULT_PROMPT_JSON$;

        let _$PLUGIN_VAR$Categories = [];
        let _$PLUGIN_VAR$CatSort = 'default';

        function render$PLUGIN_ID$Gaps(data) {
            render$PLUGIN_ID$GapsSummary(data.summary || {});
            render$PLUGIN_ID$TopGaps(data.top_gaps || []);
            _$PLUGIN_VAR$Categories = data.categories || [];
            render$PLUGIN_ID$GapsCategories();
        }

        function render$PLUGIN_ID$GapsSummary(summary) {
            const container = document.getElementById('$SUMMARY_EL$');
            if (!container) return;
            container.innerHTML = `
                <div class="gap-stat">
                    <div class="gap-stat-number">${summary.overall_coverage || 0}%</div>
                    <div class="gap-stat-label">Overall Coverage</div>
                </div>
                <div class="gap-stat">
                    <div class="gap-stat-number">${summary.topics_covered || 0}</div>
                    <div class="gap-stat-label">Topics Covered</div>
                </div>
                <div class="gap-stat">
                    <div class="gap-stat-number">${summary.topics_remaining || 0}</div>
                    <div class="gap-stat-label">Gaps Remaining</div>
                </div>
            `;
        }

        function render$PLUGIN_ID$TopGaps(gaps) {
            const container = document.getElementById('$TOP_GAPS_EL$');
            if (!container) return;
            if (gaps.length === 0) {
                container.innerHTML = '<p style="color: var(--green);">No critical gaps - you are covering the essentials.</p>';
                return;
            }
            container.innerHTML = gaps.map(g => `
                <div class="gap-top-item clickable" tabindex="0" role="button" onclick="show$PLUGIN_ID$GapPrompt('${escapeHtml(g.topic)}', '${escapeHtml(g.category)}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();show$PLUGIN_ID$GapPrompt('${escapeHtml(g.topic)}', '${escapeHtml(g.category)}');}">
                    <div>
                        <div class="gap-top-name">${escapeHtml(g.topic)}</div>
                        <div class="gap-top-cat">${escapeHtml(g.category)}</div>
                    </div>
                    <span class="gap-priority-badge ${g.priority}">${g.priority}</span>
                </div>
            `).join('');
        }

        function set$PLUGIN_ID$CategorySort(mode) {
            _$PLUGIN_VAR$CatSort = mode;
            render$PLUGIN_ID$GapsCategories();
        }

        function render$PLUGIN_ID$GapsCategories() {
            const container = document.getElementById('$CATEGORIES_EL$');
            if (!container) return;
            if (_$PLUGIN_VAR$Categories.length === 0) {
                container.innerHTML = '<p style="color: var(--text-dim);">No categories defined</p>';
                return;
            }

            const categories = [..._$PLUGIN_VAR$Categories];
            const sortMode = _$PLUGIN_VAR$CatSort;

            if (sortMode === 'coverage-asc') {
                categories.sort((a, b) => a.coverage - b.coverage);
            } else if (sortMode === 'coverage-desc') {
                categories.sort((a, b) => b.coverage - a.coverage);
            } else if (sortMode === 'name') {
                categories.sort((a, b) => a.name.localeCompare(b.name));
            }
            // 'default' leaves the server-provided order (priority then coverage)

            const sortOptions = [
                ['default', 'Priority (default)'],
                ['coverage-asc', 'Coverage: lowest first'],
                ['coverage-desc', 'Coverage: highest first'],
                ['name', 'Name (A–Z)'],
            ];
            const sortControl = `
                <div class="gap-sort-control" style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem; font-size:0.85rem; color:var(--text-dim);">
                    <label for="$CATEGORIES_EL$-sort">Sort by:</label>
                    <select id="$CATEGORIES_EL$-sort" onchange="set$PLUGIN_ID$CategorySort(this.value)" style="background:var(--card); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:0.3rem 0.5rem; font-size:0.85rem;">
                        ${sortOptions.map(([v, l]) => `<option value="${v}"${sortMode === v ? ' selected' : ''}>${l}</option>`).join('')}
                    </select>
                </div>
            `;

            const catsHtml = categories.map(cat => `
                <div class="gap-category">
                    <div class="gap-category-header">
                        <div class="gap-category-name">
                            ${escapeHtml(cat.name)}
                            <span class="gap-priority-badge ${cat.priority}">${cat.priority}</span>
                        </div>
                        <div class="gap-coverage">${cat.coverage}%</div>
                    </div>
                    <div class="gap-progress">
                        <div class="gap-progress-fill ${cat.priority}" style="width: ${cat.coverage}%;"></div>
                    </div>
                    <div class="gap-topics">
                        ${cat.covered.map(t => { const n = typeof t === 'object' ? t.name : t; const m = typeof t === 'object' ? t.mastery : 100; const cls = m >= 70 ? 'covered' : 'partial'; return `<span class="gap-topic ${cls} clickable" tabindex="0" role="button" title="Mastery: ${m}%" onclick="show$PLUGIN_ID$GapPrompt('${escapeHtml(n)}', '${escapeHtml(cat.name)}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();show$PLUGIN_ID$GapPrompt('${escapeHtml(n)}', '${escapeHtml(cat.name)}');}">${escapeHtml(n)} <small style="opacity:0.6">${m}%</small></span>`; }).join('')}
                        ${cat.gaps.map(t => { const n = typeof t === 'object' ? t.name : t; const m = typeof t === 'object' ? (t.mastery || 0) : 0; return `<span class="gap-topic missing clickable" tabindex="0" role="button" title="Mastery: ${m}%" onclick="show$PLUGIN_ID$GapPrompt('${escapeHtml(n)}', '${escapeHtml(cat.name)}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();show$PLUGIN_ID$GapPrompt('${escapeHtml(n)}', '${escapeHtml(cat.name)}');}">${escapeHtml(n)}${m > 0 ? ` <small style="opacity:0.6">${m}%</small>` : ''}</span>`; }).join('')}
                    </div>
                </div>
            `).join('');

            container.innerHTML = sortControl + catsHtml;
        }

        function show$PLUGIN_ID$GapPrompt(topic, category) {
            const key = topic.toLowerCase();
            const prompt = $PLUGIN_VAR$GapPrompts[key] || $PLUGIN_VAR$GapDefaultPrompt.replace('$TOPIC$', topic).replace('$CATEGORY$', category);
            document.getElementById('gapModalTitle').textContent = 'Fill Gap: ' + topic;
            document.getElementById('gapModalCategory').innerHTML = '<span class="gap-topic missing" style="cursor:default;">' + escapeHtml(category) + '</span>';
            document.getElementById('gapModalPrompt').textContent = prompt;
            document.getElementById('gapModalHint').textContent = 'Click to copy prompt';
            document.getElementById('gapModalHint').style.color = 'var(--text-dim)';
            document.getElementById('gapPromptModal').classList.add('show');
        }
