
        // ===== $PLUGIN_ID$ Gap Analysis =====

        const $PLUGIN_VAR$GapPrompts = $PROMPTS_JSON$;
        const $PLUGIN_VAR$GapDefaultPrompt = $DEFAULT_PROMPT_JSON$;

        function render$PLUGIN_ID$Gaps(data) {
            render$PLUGIN_ID$GapsSummary(data.summary || {});
            render$PLUGIN_ID$TopGaps(data.top_gaps || []);
            render$PLUGIN_ID$GapsCategories(data.categories || []);
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

        function render$PLUGIN_ID$GapsCategories(categories) {
            const container = document.getElementById('$CATEGORIES_EL$');
            if (!container) return;
            if (categories.length === 0) {
                container.innerHTML = '<p style="color: var(--text-dim);">No categories defined</p>';
                return;
            }
            container.innerHTML = categories.map(cat => `
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
                        ${cat.covered.map(t => `<span class="gap-topic covered clickable" tabindex="0" role="button" onclick="show$PLUGIN_ID$GapPrompt('${escapeHtml(t)}', '${escapeHtml(cat.name)}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();show$PLUGIN_ID$GapPrompt('${escapeHtml(t)}', '${escapeHtml(cat.name)}');}">${escapeHtml(t)}</span>`).join('')}
                        ${cat.gaps.map(t => `<span class="gap-topic missing clickable" tabindex="0" role="button" onclick="show$PLUGIN_ID$GapPrompt('${escapeHtml(t)}', '${escapeHtml(cat.name)}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();show$PLUGIN_ID$GapPrompt('${escapeHtml(t)}', '${escapeHtml(cat.name)}');}">${escapeHtml(t)}</span>`).join('')}
                    </div>
                </div>
            `).join('');
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
