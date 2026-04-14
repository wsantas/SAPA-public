        // ============== Recipes ==============
        let allRecipes = [];
        let recipeFavorites = new Set();
        let recipeCookLog = [];
        let recipeQuickFilter = 'all';
        let recipeAutoFilter = null;

        async function loadRecipes() {
            try {
                const [recipesRes, favsRes, cookRes] = await Promise.all([
                    fetch('/api/recipes'),
                    fetch('/api/recipes/favorites'),
                    fetch('/api/recipes/cook-log')
                ]);
                allRecipes = await recipesRes.json();
                const favs = await favsRes.json();
                recipeFavorites = new Set(Array.isArray(favs) ? favs : []);
                const cookData = await cookRes.json();
                recipeCookLog = Array.isArray(cookData) ? cookData : [];

                recipeAutoFilter = null;
                updateAutoFilterBadge();
                filterRecipes();
            } catch (e) {
                console.error('Error loading recipes:', e);
            }
        }

        function updateAutoFilterBadge() {
            const badge = document.getElementById('recipeAutoFilterBadge');
            const label = document.getElementById('recipeAutoFilterLabel');
            if (recipeAutoFilter && recipeAutoFilter.length) {
                label.textContent = recipeAutoFilter.map(f => f.charAt(0).toUpperCase() + f.slice(1)).join(' + ');
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        }

        function clearAutoFilter() {
            recipeAutoFilter = [];
            updateAutoFilterBadge();
            filterRecipes();
        }

        // --- Autocomplete filter ---
        const _rfOptions = [
            { group: 'category', value: 'breakfast', label: 'Breakfast' },
            { group: 'category', value: 'lunch', label: 'Lunch' },
            { group: 'category', value: 'dinner', label: 'Dinner' },
            { group: 'category', value: 'snack', label: 'Snack' },
            { group: 'category', value: 'side', label: 'Side' },
            { group: 'category', value: 'soup', label: 'Soup' },
            { group: 'category', value: 'salad', label: 'Salad' },
            { group: 'category', value: 'hulk', label: 'HULK' },
            { group: 'diet', value: 'paleo', label: 'Paleo' },
            { group: 'diet', value: 'keto', label: 'Keto' },
            { group: 'diet', value: 'whole30', label: 'Whole30' },
            { group: 'diet', value: 'dairy-free', label: 'Dairy-Free' },
            { group: 'diet', value: 'gluten-free', label: 'Gluten-Free' },
            { group: 'chef', value: 'Alain Passard', label: 'Passard' },
            { group: 'chef', value: 'Dan Barber', label: 'Barber' },
            { group: 'chef', value: 'Heinz Reitbauer', label: 'Reitbauer' },
            { group: 'chef', value: 'Yoshihiro Narisawa', label: 'Narisawa' },
            { group: 'chef', value: 'Mauro Colagreco', label: 'Colagreco' },
        ];
        let _rfSelected = []; // [{group, value, label}]
        let _rfHighlight = -1;

        function _rfIsSelected(group, value) {
            return _rfSelected.some(s => s.group === group && s.value === value);
        }

        function _rfToggle(group, value, label) {
            const idx = _rfSelected.findIndex(s => s.group === group && s.value === value);
            if (idx >= 0) _rfSelected.splice(idx, 1);
            else _rfSelected.push({ group, value, label });
            _rfRenderTags();
            _rfRenderDropdown();
            filterRecipes();
        }

        function _rfRemove(group, value) {
            _rfSelected = _rfSelected.filter(s => !(s.group === group && s.value === value));
            _rfRenderTags();
            filterRecipes();
        }

        function _rfRenderTags() {
            const container = document.getElementById('recipeFilterTags');
            container.innerHTML = _rfSelected.map(s =>
                `<span class="rf-tag" data-group="${s.group}">` +
                `${escapeHtml(s.label)}<span class="rf-x" onclick="event.stopPropagation(); _rfRemove('${s.group}','${s.value.replace(/'/g, "\\'")}')">×</span>` +
                `</span>`
            ).join('');
            const input = document.getElementById('recipeSearch');
            input.placeholder = _rfSelected.length ? '' : 'Search or filter...';
        }

        function _rfGetFiltered() {
            const q = (document.getElementById('recipeSearch').value || '').toLowerCase();
            return _rfOptions.filter(o => {
                if (!q) return true;
                return o.label.toLowerCase().includes(q) || o.value.toLowerCase().includes(q) || o.group.toLowerCase().includes(q);
            });
        }

        function _rfRenderDropdown() {
            const dd = document.getElementById('recipeFilterDropdown');
            const filtered = _rfGetFiltered();
            if (!filtered.length) { dd.innerHTML = '<div style="padding:0.75rem;color:var(--text-dim);font-size:0.82rem;">No matches</div>'; return; }
            const groups = ['category', 'diet', 'chef'];
            const groupLabels = { category: 'Category', diet: 'Diet', chef: 'Chef' };
            let html = '';
            let optIdx = 0;
            for (const g of groups) {
                const items = filtered.filter(o => o.group === g);
                if (!items.length) continue;
                html += `<div class="rf-group-label">${groupLabels[g]}</div>`;
                for (const o of items) {
                    const sel = _rfIsSelected(o.group, o.value);
                    html += `<div class="rf-option${sel ? ' rf-selected' : ''}${optIdx === _rfHighlight ? ' rf-highlighted' : ''}" data-idx="${optIdx}" onmousedown="_rfToggle('${o.group}','${o.value.replace(/'/g, "\\'")}','${o.label.replace(/'/g, "\\'")}')" onmouseenter="_rfHighlight=${optIdx};_rfRenderDropdown()"><span class="rf-check">✓</span>${escapeHtml(o.label)}</div>`;
                    optIdx++;
                }
            }
            dd.innerHTML = html;
        }

        function _rfInit() {
            const input = document.getElementById('recipeSearch');
            const dd = document.getElementById('recipeFilterDropdown');

            input.addEventListener('focus', () => {
                _rfHighlight = -1;
                _rfRenderDropdown();
                dd.classList.add('open');
            });

            input.addEventListener('input', () => {
                _rfHighlight = -1;
                _rfRenderDropdown();
                dd.classList.add('open');
                filterRecipes();
            });

            input.addEventListener('keydown', (e) => {
                const filtered = _rfGetFiltered();
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    _rfHighlight = Math.min(_rfHighlight + 1, filtered.length - 1);
                    _rfRenderDropdown();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    _rfHighlight = Math.max(_rfHighlight - 1, -1);
                    _rfRenderDropdown();
                } else if (e.key === 'Enter' && _rfHighlight >= 0) {
                    e.preventDefault();
                    const o = filtered[_rfHighlight];
                    if (o) { _rfToggle(o.group, o.value, o.label); input.value = ''; }
                } else if (e.key === 'Backspace' && !input.value && _rfSelected.length) {
                    const last = _rfSelected[_rfSelected.length - 1];
                    _rfRemove(last.group, last.value);
                    _rfRenderDropdown();
                } else if (e.key === 'Escape') {
                    dd.classList.remove('open');
                    input.blur();
                }
            });

            document.addEventListener('click', (e) => {
                if (!e.target.closest('#recipeFilterBox')) dd.classList.remove('open');
            });
        }

        // Init autocomplete after DOM ready
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', _rfInit);
        else setTimeout(_rfInit, 0);

        function setRecipeQuickFilter(filter) {
            recipeQuickFilter = filter;
            document.querySelectorAll('.recipe-quick-filters button').forEach(b => b.classList.remove('active'));
            const btn = document.getElementById('recipeFilter' + filter.charAt(0).toUpperCase() + filter.slice(1));
            if (btn) btn.classList.add('active');
            filterRecipes();
        }

        function getRecipeCookCount(recipeId) {
            return recipeCookLog.filter(c => c.recipe_id === recipeId).length;
        }

        function getRecipeLastCooked(recipeId) {
            const entry = recipeCookLog.find(c => c.recipe_id === recipeId);
            return entry ? entry.cooked_at : null;
        }

        function filterRecipes() {
            const search = document.getElementById('recipeSearch').value.toLowerCase();
            const activeCategories = _rfSelected.filter(s => s.group === 'category').map(s => s.value);
            const activeFrameworks = _rfSelected.filter(s => s.group === 'diet').map(s => s.value);
            const activeChefs = _rfSelected.filter(s => s.group === 'chef').map(s => s.value);
            const sortVal = document.getElementById('recipeSort')?.value || 'az';

            let filtered = allRecipes;

            // Auto-filter (e.g. dairy-free + gluten-free)
            if (recipeAutoFilter && recipeAutoFilter.length) {
                filtered = filtered.filter(r => {
                    const fw = r.frameworks || [];
                    return recipeAutoFilter.every(f => fw.includes(f));
                });
            }

            if (search) {
                filtered = filtered.filter(r =>
                    r.title.toLowerCase().includes(search) ||
                    r.description.toLowerCase().includes(search) ||
                    (r.tags || []).some(t => t.toLowerCase().includes(search)) ||
                    (r.ingredients || []).some(i => i.name.toLowerCase().includes(search))
                );
            }

            if (activeCategories.length) {
                filtered = filtered.filter(r => activeCategories.includes(r.category));
            }

            if (activeFrameworks.length) {
                filtered = filtered.filter(r => {
                    const fw = r.frameworks || [];
                    return activeFrameworks.every(f => fw.includes(f));
                });
            }

            if (activeChefs.length) {
                filtered = filtered.filter(r => activeChefs.includes(r.chef));
            }

            // Quick filters
            if (recipeQuickFilter === 'favorites') {
                filtered = filtered.filter(r => recipeFavorites.has(r.id));
            } else if (recipeQuickFilter === 'recent') {
                const cookedIds = new Set(recipeCookLog.map(c => c.recipe_id));
                filtered = filtered.filter(r => cookedIds.has(r.id));
            } else if (recipeQuickFilter === 'never') {
                const cookedIds = new Set(recipeCookLog.map(c => c.recipe_id));
                filtered = filtered.filter(r => !cookedIds.has(r.id));
            }

            // Sort
            switch (sortVal) {
                case 'az':
                    filtered.sort((a, b) => a.title.localeCompare(b.title));
                    break;
                case 'za':
                    filtered.sort((a, b) => b.title.localeCompare(a.title));
                    break;
                case 'time':
                    filtered.sort((a, b) => (a.prepTime + a.cookTime) - (b.prepTime + b.cookTime));
                    break;
                case 'calories':
                    filtered.sort((a, b) => (a.nutrition?.calories || 0) - (b.nutrition?.calories || 0));
                    break;
                case 'protein':
                    filtered.sort((a, b) => (b.nutrition?.protein || 0) - (a.nutrition?.protein || 0));
                    break;
                case 'recent':
                    filtered.sort((a, b) => {
                        const aLast = getRecipeLastCooked(a.id) || '';
                        const bLast = getRecipeLastCooked(b.id) || '';
                        return bLast.localeCompare(aLast);
                    });
                    break;
                case 'most':
                    filtered.sort((a, b) => getRecipeCookCount(b.id) - getRecipeCookCount(a.id));
                    break;
            }

            renderRecipes(filtered);
        }

        function renderRecipes(recipes) {
            const grid = document.getElementById('recipeGrid');
            document.getElementById('recipeCount').textContent = recipes.length + ' recipes';

            if (recipes.length === 0) {
                grid.innerHTML = '<div class="card" style="grid-column: 1/-1; text-align: center; padding: 2rem;"><p style="color: var(--text-dim);">No recipes found</p></div>';
                return;
            }

            grid.innerHTML = recipes.map(r => {
                const categoryColors = {
                    breakfast: '#f59e0b',
                    lunch: '#22c55e',
                    dinner: '#ef4444',
                    snack: '#8b5cf6',
                    side: '#06b6d4',
                    soup: '#f97316',
                    salad: '#10b981',
                    hulk: '#dc2626'
                };
                const color = categoryColors[r.category] || 'var(--accent)';
                const isFav = recipeFavorites.has(r.id);
                const cookCount = getRecipeCookCount(r.id);
                return `
                <div class="card" style="cursor: pointer; transition: transform 0.15s;" onclick="showRecipe('${r.id}')" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='none'">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                        <span style="font-size: 0.7rem; padding: 0.2rem 0.5rem; background: ${color}20; color: ${color}; border-radius: 4px; text-transform: uppercase; font-weight: 600;">${r.category}</span>
                        ${r.chef ? '<span style="font-size: 0.65rem; color: var(--text-dim); font-style: italic;">' + escapeHtml(r.chef) + '</span>' : ''}
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            ${isFav ? '<span style="color: #ef4444; font-size: 0.85rem;">&#9829;</span>' : ''}
                            ${cookCount > 0 ? '<span class="recipe-cook-badge">&#127859; ' + cookCount + 'x</span>' : ''}
                            <span style="font-size: 0.75rem; color: var(--text-dim);">${r.prepTime + r.cookTime} min</span>
                        </div>
                    </div>
                    <h3 style="font-size: 1rem; margin: 0 0 0.5rem 0; color: var(--text);">${escapeHtml(r.title)}</h3>
                    <p style="font-size: 0.8rem; color: var(--text-dim); margin: 0 0 0.75rem 0; line-height: 1.4;">${escapeHtml(r.description.substring(0, 100))}${r.description.length > 100 ? '...' : ''}</p>
                    <div style="display: flex; gap: 0.75rem; font-size: 0.75rem; color: var(--text-dim);">
                        <span>🔥 ${r.nutrition?.calories || 0} cal</span>
                        <span>💪 ${r.nutrition?.protein || 0}g protein</span>
                    </div>
                </div>
                `;
            }).join('');
        }

        function showRecipe(id) {
            const recipe = allRecipes.find(r => r.id === id);
            if (!recipe) return;

            document.getElementById('recipeModalTitle').textContent = recipe.title;

            // Update favorite heart
            const heart = document.getElementById('recipeModalFavHeart');
            if (recipeFavorites.has(recipe.id)) {
                heart.innerHTML = '&#9829;';
                heart.classList.add('favorited');
            } else {
                heart.innerHTML = '&#9825;';
                heart.classList.remove('favorited');
            }

            const content = `
                <div style="margin-bottom: 1rem;">
                    <p style="color: var(--text-dim); margin-bottom: 0.75rem;">${escapeHtml(recipe.description)}</p>
                    <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem;">
                        ${(recipe.frameworks || []).map(f => `<span style="font-size: 0.7rem; padding: 0.2rem 0.5rem; background: var(--accent)20; color: var(--accent); border-radius: 4px;">${f}</span>`).join('')}
                    </div>
                    <div style="display: flex; gap: 1.5rem; font-size: 0.85rem; color: var(--text-dim); padding: 0.75rem; background: var(--bg); border-radius: 8px;">
                        <span>⏱️ Prep: ${recipe.prepTime}min</span>
                        <span>🍳 Cook: ${recipe.cookTime}min</span>
                        <span>👥 Serves: ${recipe.servings}</span>
                        <span>📊 ${recipe.difficulty}</span>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                    <div style="padding: 0.75rem; background: var(--bg); border-radius: 8px;">
                        <div style="font-weight: 600; margin-bottom: 0.5rem; color: var(--text);">Nutrition (per serving)</div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.25rem; font-size: 0.85rem; color: var(--text-dim);">
                            <span>Calories: ${recipe.nutrition?.calories || 0}</span>
                            <span>Protein: ${recipe.nutrition?.protein || 0}g</span>
                            <span>Carbs: ${recipe.nutrition?.carbs || 0}g</span>
                            <span>Fat: ${recipe.nutrition?.fat || 0}g</span>
                            <span>Fiber: ${recipe.nutrition?.fiber || 0}g</span>
                            <span>Sugar: ${recipe.nutrition?.sugar || 0}g</span>
                        </div>
                    </div>
                    <div style="padding: 0.75rem; background: var(--bg); border-radius: 8px;">
                        <div style="font-weight: 600; margin-bottom: 0.5rem; color: var(--text);">Tags</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 0.25rem;">
                            ${(recipe.tags || []).map(t => `<span style="font-size: 0.7rem; padding: 0.15rem 0.4rem; background: var(--border); border-radius: 3px; color: var(--text-dim);">${t}</span>`).join('')}
                        </div>
                    </div>
                </div>

                <div style="margin-bottom: 1rem;">
                    <div style="font-weight: 600; margin-bottom: 0.5rem; color: var(--text);">Ingredients</div>
                    <ul style="margin: 0; padding-left: 1.25rem; color: var(--text-dim); font-size: 0.9rem; line-height: 1.6;">
                        ${(recipe.ingredients || []).map(i => `<li>${i.amount} ${i.unit} ${escapeHtml(i.name)}${i.notes ? ` (${escapeHtml(i.notes)})` : ''}</li>`).join('')}
                    </ul>
                </div>

                <div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem; color: var(--text);">Instructions</div>
                    <ol style="margin: 0; padding-left: 1.25rem; color: var(--text-dim); font-size: 0.9rem; line-height: 1.8;">
                        ${(recipe.instructions || []).map(i => `<li style="margin-bottom: 0.5rem;">${escapeHtml(i)}</li>`).join('')}
                    </ol>
                </div>
            `;

            document.getElementById('recipeModalContent').innerHTML = content;
            document.getElementById('recipeModal').classList.add('show');

            // Set up recipe request
            currentRecipeForRequest = recipe;
            updateRecipeRequestSection();
        }

        function closeRecipeModal() {
            document.getElementById('recipeModal').classList.remove('show');
            currentRecipeForRequest = null;
        }

        async function logRecipeAsMeal() {
            if (!currentRecipeForRequest) return;

            const servings = parseFloat(document.getElementById('logServings').value) || 1;
            const recipe = currentRecipeForRequest;
            const nutrition = recipe.nutrition || {};

            try {
                const res = await fetch('/api/meals', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        meal_name: recipe.title + (servings !== 1 ? ` (${servings} servings)` : ''),
                        category: recipe.category || 'meal',
                        calories: Math.round((nutrition.calories || 0) * servings),
                        protein: Math.round((nutrition.protein || 0) * servings),
                        carbs: Math.round((nutrition.carbs || 0) * servings),
                        fat: Math.round((nutrition.fat || 0) * servings),
                        notes: `Recipe: ${recipe.id}`
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Logged ${recipe.title} - ${Math.round((nutrition.protein || 0) * servings)}g protein`, 'success');
                    // Also log to cook log
                    fetch('/api/recipes/cook-log', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ recipe_id: recipe.id, servings: servings })
                    }).then(() => {
                        // Refresh cook log data
                        fetch('/api/recipes/cook-log').then(r => r.json()).then(d => {
                            recipeCookLog = Array.isArray(d) ? d : [];
                        });
                    });
                    closeRecipeModal();
                    // Refresh nutrition panel if visible
                    if (document.getElementById('nutrition').classList.contains('active')) {
                        loadTodayMeals();
                    }
                    // Refresh dashboard protein tracker
                    loadProteinTracker();
                } else {
                    showToast('Error logging meal: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                showToast('Error logging meal', 'error');
            }
        }

        // ============== Recipe Actions ==============

        async function toggleRecipeFavorite() {
            if (!currentRecipeForRequest) return;
            try {
                const res = await fetch('/api/recipes/favorites', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ recipe_id: currentRecipeForRequest.id })
                });
                const data = await res.json();
                if (data.success) {
                    const heart = document.getElementById('recipeModalFavHeart');
                    if (data.favorited) {
                        recipeFavorites.add(currentRecipeForRequest.id);
                        heart.innerHTML = '&#9829;';
                        heart.classList.add('favorited');
                        showToast('Added to favorites', 'success');
                    } else {
                        recipeFavorites.delete(currentRecipeForRequest.id);
                        heart.innerHTML = '&#9825;';
                        heart.classList.remove('favorited');
                        showToast('Removed from favorites', 'success');
                    }
                }
            } catch (e) {
                showToast('Error toggling favorite', 'error');
            }
        }

        async function addRecipeToGrocery() {
            if (!currentRecipeForRequest) return;
            const servings = parseFloat(document.getElementById('logServings').value) || 1;
            try {
                const res = await fetch('/api/grocery/from-recipe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ recipe_id: currentRecipeForRequest.id, servings: servings })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Added ${data.added} items to grocery list`, 'success');
                } else {
                    showToast(data.error || 'Error adding to grocery', 'error');
                }
            } catch (e) {
                showToast('Error adding to grocery', 'error');
            }
        }

        // ============== Cooking Mode ==============
        let cookingRecipe = null;
        let cookingStep = 0;
        let cookingBaseServings = 1;
        let cookingTimers = [];
        let cookingWakeLock = null;

        function startCookingMode() {
            if (!currentRecipeForRequest) return;
            cookingRecipe = currentRecipeForRequest;
            cookingStep = 0;
            cookingBaseServings = cookingRecipe.servings || 1;
            const servingsInput = document.getElementById('cookingServings');
            servingsInput.value = cookingBaseServings;

            closeRecipeModal();

            document.getElementById('cookingTitle').textContent = cookingRecipe.title;
            renderCookingIngredients(1);
            renderCookingSteps();
            updateCookingNav();

            document.getElementById('cookingMode').style.display = 'flex';
            document.body.style.overflow = 'hidden';

            // Request wake lock
            requestWakeLock();
        }

        function exitCookingMode() {
            document.getElementById('cookingMode').style.display = 'none';
            document.body.style.overflow = '';

            // Clear timers
            cookingTimers.forEach(t => clearInterval(t.interval));
            cookingTimers = [];
            document.getElementById('cookingTimers').innerHTML = '';

            // Release wake lock
            releaseWakeLock();
            cookingRecipe = null;
        }

        function renderCookingIngredients(multiplier) {
            if (!cookingRecipe) return;
            const ings = cookingRecipe.ingredients || [];

            // Group by category
            const grouped = {};
            ings.forEach(ing => {
                const cat = ing.category || 'other';
                if (!grouped[cat]) grouped[cat] = [];
                grouped[cat].push(ing);
            });

            let html = '';
            for (const [cat, items] of Object.entries(grouped)) {
                html += '<div class="cooking-ing-category">';
                html += '<div class="cooking-ing-category-label">' + escapeHtml(cat) + '</div>';
                items.forEach((ing, i) => {
                    let amt = ing.amount || '';
                    if (amt && multiplier !== 1) {
                        try {
                            const scaled = parseFloat(amt) * multiplier;
                            amt = scaled === Math.floor(scaled) ? scaled.toString() : scaled.toFixed(1);
                        } catch (e) {}
                    }
                    const key = cat + '-' + i;
                    html += '<div class="cooking-ing-item" id="cing-' + key + '" onclick="toggleCookingIng(this)">';
                    html += '<input type="checkbox" tabindex="-1">';
                    html += '<span>' + (amt ? amt + ' ' : '') + (ing.unit || '') + ' ' + escapeHtml(ing.name) + (ing.notes ? ' (' + escapeHtml(ing.notes) + ')' : '') + '</span>';
                    html += '</div>';
                });
                html += '</div>';
            }

            document.getElementById('cookingIngredients').innerHTML = html;
        }

        function toggleCookingIng(el) {
            el.classList.toggle('checked');
            const cb = el.querySelector('input[type="checkbox"]');
            if (cb) cb.checked = el.classList.contains('checked');
        }

        function scaleCookingIngredients() {
            if (!cookingRecipe) return;
            const servings = parseFloat(document.getElementById('cookingServings').value) || 1;
            const multiplier = servings / cookingBaseServings;
            renderCookingIngredients(multiplier);
        }

        function renderCookingSteps() {
            if (!cookingRecipe) return;
            const steps = cookingRecipe.instructions || [];
            const container = document.getElementById('cookingSteps');

            container.innerHTML = steps.map((step, i) => {
                const cls = i === cookingStep ? 'active' : (i < cookingStep ? 'completed' : '');
                let timerHtml = '';
                const timerMatch = step.match(/(\d+)[\s-]*(?:to[\s-]*(\d+))?\s*(minutes?|mins?|hours?|hrs?)/i);
                if (timerMatch) {
                    const mins = timerMatch[3].toLowerCase().startsWith('h')
                        ? parseInt(timerMatch[1]) * 60
                        : (timerMatch[2] ? Math.round((parseInt(timerMatch[1]) + parseInt(timerMatch[2])) / 2) : parseInt(timerMatch[1]));
                    timerHtml = '<div><button class="cooking-step-timer-btn" onclick="event.stopPropagation(); startCookingTimer(' + (mins * 60) + ', ' + i + ')">&#9202; Start ' + mins + ' min timer</button></div>';
                }
                return '<div class="cooking-step ' + cls + '" id="cstep-' + i + '" onclick="goToCookingStep(' + i + ')">' +
                    '<span class="cooking-step-number">' + (i + 1) + '</span>' +
                    escapeHtml(step) +
                    timerHtml +
                    '</div>';
            }).join('');

            // Scroll active step into view
            const activeEl = document.getElementById('cstep-' + cookingStep);
            if (activeEl) activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        function goToCookingStep(idx) {
            cookingStep = idx;
            renderCookingSteps();
            updateCookingNav();
        }

        function cookingNextStep() {
            if (!cookingRecipe) return;
            const total = (cookingRecipe.instructions || []).length;
            if (cookingStep < total - 1) {
                cookingStep++;
                renderCookingSteps();
                updateCookingNav();
            }
        }

        function cookingPrevStep() {
            if (cookingStep > 0) {
                cookingStep--;
                renderCookingSteps();
                updateCookingNav();
            }
        }

        function updateCookingNav() {
            if (!cookingRecipe) return;
            const total = (cookingRecipe.instructions || []).length;
            const counter = document.getElementById('cookingStepCounter');
            counter.textContent = 'Step ' + (cookingStep + 1) + ' of ' + total;

            const prevBtn = document.getElementById('cookingPrevBtn');
            prevBtn.disabled = cookingStep === 0;
            prevBtn.style.opacity = cookingStep === 0 ? '0.4' : '1';

            const nextBtn = document.getElementById('cookingNextBtn');
            if (cookingStep === total - 1) {
                nextBtn.className = 'cooking-nav-finish';
                nextBtn.textContent = 'I Made This!';
                nextBtn.onclick = finishCooking;
            } else {
                nextBtn.className = 'cooking-nav-next';
                nextBtn.textContent = 'Next';
                nextBtn.onclick = cookingNextStep;
            }
        }

        async function finishCooking() {
            if (!cookingRecipe) return;
            const servings = parseFloat(document.getElementById('cookingServings').value) || 1;

            // Log to cook log
            try {
                await fetch('/api/recipes/cook-log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ recipe_id: cookingRecipe.id, servings: servings })
                });
                // Refresh cook log
                const res = await fetch('/api/recipes/cook-log');
                const data = await res.json();
                recipeCookLog = Array.isArray(data) ? data : [];
            } catch (e) {}

            // Also log as meal
            const nutrition = cookingRecipe.nutrition || {};
            try {
                await fetch('/api/meals', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        meal_name: cookingRecipe.title + (servings !== 1 ? ' (' + servings + ' servings)' : ''),
                        category: cookingRecipe.category || 'meal',
                        calories: Math.round((nutrition.calories || 0) * (servings / cookingBaseServings)),
                        protein: Math.round((nutrition.protein || 0) * (servings / cookingBaseServings)),
                        carbs: Math.round((nutrition.carbs || 0) * (servings / cookingBaseServings)),
                        fat: Math.round((nutrition.fat || 0) * (servings / cookingBaseServings)),
                        notes: 'Recipe: ' + cookingRecipe.id
                    })
                });
            } catch (e) {}

            showToast('Nice! Logged ' + cookingRecipe.title, 'success');
            exitCookingMode();
            loadProteinTracker();
        }

        // Cooking Timers
        function startCookingTimer(seconds, stepIdx) {
            const id = Date.now();
            const timer = {
                id: id,
                seconds: seconds,
                remaining: seconds,
                stepIdx: stepIdx,
                interval: null
            };

            timer.interval = setInterval(() => {
                timer.remaining--;
                renderCookingTimerDisplays();
                if (timer.remaining <= 0) {
                    clearInterval(timer.interval);
                    // Browser notification
                    if ('Notification' in window && Notification.permission === 'granted') {
                        new Notification('Timer Done!', { body: 'Step ' + (stepIdx + 1) + ' timer is up!' });
                    } else if ('Notification' in window && Notification.permission !== 'denied') {
                        Notification.requestPermission();
                    }
                    showToast('Timer done! (Step ' + (stepIdx + 1) + ')', 'success');
                    // Remove from timers
                    cookingTimers = cookingTimers.filter(t => t.id !== id);
                    renderCookingTimerDisplays();
                }
            }, 1000);

            cookingTimers.push(timer);
            renderCookingTimerDisplays();
            showToast('Timer started: ' + Math.floor(seconds / 60) + ' min', 'success');
        }

        function renderCookingTimerDisplays() {
            const container = document.getElementById('cookingTimers');
            if (cookingTimers.length === 0) {
                container.innerHTML = '';
                return;
            }
            container.innerHTML = cookingTimers.map(t => {
                const mins = Math.floor(t.remaining / 60);
                const secs = t.remaining % 60;
                const urgent = t.remaining <= 30;
                return '<span class="cooking-timer-display' + (urgent ? ' urgent' : '') + '" onclick="cancelCookingTimer(' + t.id + ')" title="Click to cancel">' +
                    '&#9202; S' + (t.stepIdx + 1) + ': ' + mins + ':' + String(secs).padStart(2, '0') +
                    '</span>';
            }).join(' ');
        }

        function cancelCookingTimer(id) {
            const timer = cookingTimers.find(t => t.id === id);
            if (timer) {
                clearInterval(timer.interval);
                cookingTimers = cookingTimers.filter(t => t.id !== id);
                renderCookingTimerDisplays();
                showToast('Timer cancelled', 'info');
            }
        }

        // Wake Lock
        async function requestWakeLock() {
            try {
                if ('wakeLock' in navigator) {
                    cookingWakeLock = await navigator.wakeLock.request('screen');
                }
            } catch (e) {
                // Wake lock not supported or denied
            }
        }

        function releaseWakeLock() {
            if (cookingWakeLock) {
                cookingWakeLock.release().catch(() => {});
                cookingWakeLock = null;
            }
        }

        function printRecipe() {
            window.print();
        }

        // Keyboard handler for cooking mode
        document.addEventListener('keydown', (e) => {
            if (!cookingRecipe || document.getElementById('cookingMode').style.display === 'none') return;
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                e.preventDefault();
                cookingNextStep();
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                e.preventDefault();
                cookingPrevStep();
            } else if (e.key === 'Escape') {
                exitCookingMode();
            }
        });

        // ============== Meal Planner Functions ==============
        let currentRecipeForRequest = null;

        function updateRecipeRequestSection() {
            const requestSection = document.getElementById('recipeRequestSection');
            const planSection = document.getElementById('recipePlanSection');

            if (currentRecipeForRequest) {
                requestSection.style.display = 'none';
                planSection.style.display = 'block';
                document.getElementById('recipePlanDate').valueAsDate = new Date();
            } else {
                requestSection.style.display = 'none';
                planSection.style.display = 'none';
            }
        }

        async function addRecipeToPlan() {
            if (!currentRecipeForRequest) return;

            const planDate = document.getElementById('recipePlanDate').value;
            const mealType = document.getElementById('recipePlanMealType').value;

            if (!planDate) {
                showToast('Please select a date', 'error');
                return;
            }

            try {
                const res = await fetch('/api/meal-plans', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        plan_date: planDate,
                        meal_type: mealType,
                        recipe_id: currentRecipeForRequest.id,
                        recipe_name: currentRecipeForRequest.title
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Added ${currentRecipeForRequest.title} to ${mealType} on ${planDate}`);
                    closeRecipeModal();
                } else {
                    showToast('Error: ' + (data.error || 'Failed to add to plan'), 'error');
                }
            } catch (e) {
                showToast('Error adding to plan', 'error');
            }
        }

        async function requestRecipe() {
            if (!currentRecipeForRequest) return;
            const notes = document.getElementById('requestNotes').value;
            const requestDate = document.getElementById('requestDate').value;

            try {
                const res = await fetch('/api/meal-requests', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        recipe_id: currentRecipeForRequest.id,
                        recipe_name: currentRecipeForRequest.title,
                        notes: notes,
                        requested_date: requestDate
                    })
                });
                const data = await res.json();
                if (data.success) {
                    alert('Recipe requested successfully!');
                    document.getElementById('requestNotes').value = '';
                    closeRecipeModal();
                } else {
                    alert('Error: ' + (data.error || 'Failed to submit request'));
                }
            } catch (e) {
                alert('Error submitting request');
            }
        }
