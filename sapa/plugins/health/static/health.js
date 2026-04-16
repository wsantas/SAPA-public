
        let sessionsData = [];
        let analyticsData = {};
        let allTopicsData = [];
        let allHistoryData = [];
        let historyDisplayCount = 5;
        let calendarMonth = new Date().getMonth();
        let calendarYear = new Date().getFullYear();

        // Body map configurations per profile
        const DEMO_BODY_MAP = { value: 'demo', label: 'General Anatomy (Demo)' };
        const PROFILE_BODY_MAPS = {
            1: [DEMO_BODY_MAP],
            2: [DEMO_BODY_MAP],
        };

        function updateBodyMapSelector() {
            const select = document.getElementById('bodyMapIssue');
            const maps = PROFILE_BODY_MAPS[currentProfileId] || [DEMO_BODY_MAP];

            select.disabled = false;
            select.innerHTML = maps.map(m =>
                `<option value="${m.value}">${escapeHtml(m.label)}</option>`
            ).join('');
            // Show the first available body map
            switchBodyMapIssue(maps[0].value);
        }

        function applyProfileTheme(profileId) {
            document.documentElement.setAttribute('data-profile', profileId.toString());
        }


        function toggleCareerCTO(show) {
            const main = document.getElementById('career-main');
            const cto = document.getElementById('career-cto');
            if (!main || !cto) return;
            main.style.display = show ? 'none' : 'block';
            cto.style.display = show ? 'block' : 'none';
            document.getElementById('career').scrollTop = 0;
            window.scrollTo(0, 0);
        }

        function toggleComebackDay(id) {
            const el = document.getElementById(id);
            if (!el) return;
            const allDays = ['cb-mon','cb-tue','cb-wed','cb-thu','cb-fri','cb-sun'];
            allDays.forEach(d => {
                const other = document.getElementById(d);
                if (other && d !== id) other.style.display = 'none';
            });
            el.style.display = el.style.display === 'none' ? 'block' : 'none';
        }

        // escapeHtml is provided by BASE_JS (sapa/gaps.py)

        // ============== Protein Dashboard Widget ==============
        let _proteinData = null;

        async function loadProteinTracker() {
            try {
                const [proteinRes, streakRes] = await Promise.all([
                    fetch('/api/protein/today'),
                    fetch('/api/protein/streak')
                ]);
                const data = await proteinRes.json();
                const streakData = await streakRes.json();
                _proteinData = data;

                const consumed = data.consumed || 0;
                const goal = data.goal || 100;
                const remaining = data.remaining || Math.max(0, goal - consumed);
                const pct = Math.min(100, Math.round((consumed / goal) * 100));
                const streak = streakData.streak || 0;

                const widget = document.getElementById('proteinWidget');
                if (!widget) return;

                // Hide widget if profile has no protein goal set (goal defaults to 100)
                if (goal <= 0) {
                    widget.style.display = 'none';
                    return;
                }
                widget.style.display = '';

                // Update ring
                const ring = document.getElementById('dashProteinRing');
                if (ring) ring.style.strokeDashoffset = (100 - pct);
                const pctLabel = document.getElementById('dashProteinPct');
                if (pctLabel) pctLabel.textContent = pct + '%';

                // Update numbers
                const nums = document.getElementById('dashProteinNums');
                if (nums) nums.textContent = consumed + ' / ' + goal + 'g';
                const rem = document.getElementById('dashProteinRemaining');
                if (rem) rem.textContent = remaining > 0 ? remaining + 'g remaining' : 'Goal reached!';

                // Update streak
                const streakEl = document.getElementById('dashProteinStreak');
                const streakNum = document.getElementById('dashProteinStreakNum');
                if (streakEl && streakNum) {
                    if (streak > 0) {
                        streakEl.style.display = '';
                        streakNum.textContent = streak;
                    } else {
                        streakEl.style.display = 'none';
                    }
                }

                // Ring color
                if (ring) {
                    if (pct >= 100) ring.style.stroke = '#22c55e';
                    else if (pct >= 70) ring.style.stroke = 'var(--accent)';
                    else if (pct >= 40) ring.style.stroke = '#f59e0b';
                    else ring.style.stroke = '#ef4444';
                }

                // Update expandable meal list
                const mealsList = document.getElementById('dashProteinMeals');
                if (mealsList && data.meals) {
                    const proteinMeals = data.meals.filter(m => m.protein > 0);
                    if (proteinMeals.length > 0) {
                        mealsList.innerHTML = proteinMeals.map(m =>
                            '<div class="protein-meal-item">' +
                            '<span class="name">' + escapeHtml(m.meal_name) + '</span>' +
                            '<span>' + (m.protein || 0) + 'g</span>' +
                            '</div>'
                        ).join('');
                    } else {
                        mealsList.innerHTML = '<div style="color: var(--text-dim); font-size: 0.8rem; padding: 0.3rem 0;">No protein logged yet today</div>';
                    }
                }
            } catch (e) {
                console.error('Error loading protein:', e);
            }
        }

        function toggleProteinMeals() {
            const el = document.getElementById('dashProteinMeals');
            if (el) el.classList.toggle('open');
        }

        function showCustomProteinInput() {
            const el = document.getElementById('proteinCustomInput');
            if (el) el.style.display = el.style.display === 'none' ? 'flex' : 'none';
        }

        function dashAddCustomProtein() {
            const name = document.getElementById('dashCustomProteinName').value.trim() || 'Custom';
            const amount = parseInt(document.getElementById('dashCustomProteinAmt').value) || 0;
            if (amount <= 0) {
                showToast('Enter protein amount', 'error');
                return;
            }
            quickAddProtein(name, amount);
            document.getElementById('dashCustomProteinName').value = '';
            document.getElementById('dashCustomProteinAmt').value = '';
            document.getElementById('proteinCustomInput').style.display = 'none';
        }

        async function quickAddProtein(name, amount) {
            try {
                await fetch('/api/protein/quick', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, protein: amount})
                });
                loadProteinTracker();
                // Also refresh nutrition tab if it's loaded
                if (document.getElementById('nutrition') && document.getElementById('nutrition').classList.contains('active')) {
                    loadTodayMeals();
                }
                showToast(`Added ${amount}g protein`, 'success');
            } catch (e) {
                showToast('Error adding protein', 'error');
            }
        }

        async function addCustomProtein() {
            const name = document.getElementById('customProteinName').value.trim() || 'Custom';
            const amount = parseInt(document.getElementById('customProteinAmount').value) || 0;
            if (amount <= 0) {
                showToast('Enter protein amount', 'error');
                return;
            }
            await quickAddProtein(name, amount);
            document.getElementById('customProteinName').value = '';
            document.getElementById('customProteinAmount').value = '';
        }


        // ============== Meal Planner View State ==============
        let _mpView = 'week';
        let _mpMonth = new Date().getMonth();
        let _mpYear = new Date().getFullYear();

        function switchMealPlanView(view) {
            _mpView = view;
            document.querySelectorAll('.mp-view-btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`.mp-view-btn[onclick="switchMealPlanView('${view}')"]`)?.classList.add('active');
            document.getElementById('weekPlanView').style.display = view === 'week' ? 'block' : 'none';
            document.getElementById('monthPlanView').style.display = view === 'month' ? 'block' : 'none';
            if (view === 'month') loadMealPlanMonth();
        }

        function navMealPlanMonth(delta) {
            _mpMonth += delta;
            if (_mpMonth > 11) { _mpMonth = 0; _mpYear++; }
            if (_mpMonth < 0) { _mpMonth = 11; _mpYear--; }
            loadMealPlanMonth();
        }

        function jumpToWeek(dateStr) {
            // Switch to week view, setting the week start to the Monday of the clicked date's week
            const clicked = new Date(dateStr + 'T12:00:00');
            const day = clicked.getDay();
            const diff = day === 0 ? -6 : 1 - day;
            const monday = new Date(clicked);
            monday.setDate(clicked.getDate() + diff);
            // Store the week start for loadMealPlanner to use
            window._mpWeekOverride = monday;
            switchMealPlanView('week');
            loadMealPlanner();
        }

        async function loadMealPlanMonth() {
            const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
            document.getElementById('mpMonthLabel').textContent = `${monthNames[_mpMonth]} ${_mpYear}`;

            // Render day headers
            const headerGrid = document.getElementById('mpDayHeaders');
            headerGrid.innerHTML = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
                .map(d => `<div class="mp-cal-day-header">${d}</div>`).join('');

            // Calculate grid range: first day of month padded to Sunday
            const firstOfMonth = new Date(_mpYear, _mpMonth, 1);
            const lastOfMonth = new Date(_mpYear, _mpMonth + 1, 0);
            const startPad = firstOfMonth.getDay();
            const gridStart = new Date(firstOfMonth);
            gridStart.setDate(1 - startPad);
            const totalCells = Math.ceil((startPad + lastOfMonth.getDate()) / 7) * 7;

            // Fetch plans for the visible range
            const fmtDate = d => d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
            const gridEnd = new Date(gridStart);
            gridEnd.setDate(gridStart.getDate() + totalCells - 1);

            let plansByDate = {};
            try {
                const res = await fetch(`/api/meal-plans?start_date=${fmtDate(gridStart)}&end_date=${fmtDate(gridEnd)}`);
                const plans = await res.json();
                plans.forEach(p => {
                    if (!plansByDate[p.plan_date]) plansByDate[p.plan_date] = [];
                    plansByDate[p.plan_date].push(p);
                });
            } catch (e) {
                console.error('Error loading month plans:', e);
            }

            const today = new Date();
            const todayStr = fmtDate(today);
            let html = '';
            for (let i = 0; i < totalCells; i++) {
                const cellDate = new Date(gridStart);
                cellDate.setDate(gridStart.getDate() + i);
                const dateStr = fmtDate(cellDate);
                const isOther = cellDate.getMonth() !== _mpMonth;
                const isToday = dateStr === todayStr;
                const dayPlans = plansByDate[dateStr] || [];
                const hasMeals = dayPlans.length > 0;

                const classes = ['mp-cal-cell'];
                if (isToday) classes.push('today');
                if (isOther) classes.push('other-month');
                if (hasMeals) classes.push('has-meals');

                const mealTypes = new Set(dayPlans.map(p => p.meal_type));
                const dots = ['breakfast','lunch','dinner','snack']
                    .filter(t => mealTypes.has(t))
                    .map(t => `<span class="mp-dot ${t}"></span>`)
                    .join('');

                html += `<div class="${classes.join(' ')}" onclick="openMealSidebar('${dateStr}')" title="${dateStr}${hasMeals ? '\\n' + dayPlans.map(p => p.meal_type + ': ' + p.recipe_name).join('\\n') : ''}">
                    <span>${cellDate.getDate()}</span>
                    <div class="mp-cal-dots">${dots}</div>
                </div>`;
            }
            document.getElementById('monthPlanGrid').innerHTML = html;
        }

        async function loadMealPlanner() {
            // Show management sections for all profiles
            document.getElementById('pendingRequestsSection').style.display = 'block';
            document.getElementById('addMealPlanSection').style.display = 'block';
            document.getElementById('premadePlansSection').style.display = 'block';

            try {
                // Load pending requests
                {
                    const requestsRes = await fetch('/api/meal-requests?status=pending');
                    const requests = await requestsRes.json();

                    document.getElementById('pendingCount').textContent = requests.length;

                    const pendingDiv = document.getElementById('pendingRequests');
                    if (requests.length === 0) {
                        pendingDiv.innerHTML = '<div style="color: var(--text-dim); font-size: 0.85rem;">No pending requests</div>';
                    } else {
                        pendingDiv.innerHTML = requests.map(r => `
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--bg); border-radius: 8px;">
                                <div>
                                    <div style="font-weight: 500;">${r.recipe_name}</div>
                                    <div style="font-size: 0.8rem; color: var(--text-dim);">
                                        From ${r.requester_name || 'Unknown'}
                                        ${r.requested_date ? ' for ' + r.requested_date : ''}
                                        ${r.notes ? ' - ' + r.notes : ''}
                                    </div>
                                </div>
                                <div style="display: flex; gap: 0.5rem;">
                                    <button onclick="planFromRequest(${r.id}, '${r.recipe_id || ''}', '${r.recipe_name.replace(/'/g, "\\'")}')" style="padding: 0.4rem 0.75rem; background: var(--accent); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem;">Plan</button>
                                    <button onclick="dismissRequest(${r.id})" style="padding: 0.4rem 0.75rem; background: var(--border); color: var(--text); border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem;">Dismiss</button>
                                </div>
                            </div>
                        `).join('');
                    }
                }

                // Load meal plans for this week (supports override from month view click)
                const today = window._mpWeekOverride || new Date();
                window._mpWeekOverride = null;
                const fmtD = d => d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
                const startDate = fmtD(today);
                const endDay = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
                const endDate = fmtD(endDay);

                const plansRes = await fetch(`/api/meal-plans?start_date=${startDate}&end_date=${endDate}`);
                const plans = await plansRes.json();

                const weekGrid = document.getElementById('weekPlanGrid');
                const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

                // Group plans by date
                const plansByDate = {};
                plans.forEach(p => {
                    if (!plansByDate[p.plan_date]) plansByDate[p.plan_date] = [];
                    plansByDate[p.plan_date].push(p);
                });

                // Generate week grid
                let gridHtml = '';
                for (let i = 0; i < 7; i++) {
                    const date = new Date(today.getTime() + i * 24 * 60 * 60 * 1000);
                    const dateStr = fmtD(date);
                    const dayPlans = plansByDate[dateStr] || [];
                    const isToday = dateStr === fmtD(new Date());

                    gridHtml += `
                        <div style="background: ${isToday ? 'rgba(16,185,129,0.1)' : 'var(--bg)'}; padding: 0.75rem; border-radius: 8px; border: 1px solid ${isToday ? 'var(--accent)' : 'var(--border)'}; cursor: pointer;" onclick="openMealSidebar('${dateStr}')">
                            <div style="font-weight: 600; font-size: 0.85rem; margin-bottom: 0.5rem;">${days[date.getDay()]} ${date.getDate()}</div>
                            ${dayPlans.length > 0 ? dayPlans.map(p => `
                                <div style="font-size: 0.8rem; color: var(--text-dim); margin-bottom: 0.25rem; display: flex; justify-content: space-between; align-items: center;">
                                    <span>${p.meal_type}: ${p.recipe_id ? `<a href="#" onclick="event.stopPropagation(); event.preventDefault(); if(allRecipes.length===0){loadRecipes().then(()=>showRecipe('${p.recipe_id}'))}else{showRecipe('${p.recipe_id}')}" style="color: var(--accent); text-decoration: none; cursor: pointer;">${p.recipe_name}</a>` : p.recipe_name}</span>
                                    <button onclick="event.stopPropagation(); deleteMealPlan(${p.id})" class="delete-btn" aria-label="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m2 0v14a2 2 0 01-2 2H8a2 2 0 01-2-2V6h12z"/></svg></button>
                                </div>
                            `).join('') : '<div style="font-size: 0.75rem; color: var(--text-dim);">No meals planned</div>'}
                        </div>
                    `;
                }
                weekGrid.innerHTML = gridHtml;

                // Load request history
                const historyRes = await fetch('/api/meal-requests');
                const history = await historyRes.json();

                const historyDiv = document.getElementById('requestHistory');
                const historyTitle = document.getElementById('requestHistoryTitle');

                historyTitle.textContent = 'Request History';
                const nonPending = history.filter(r => r.status !== 'pending').slice(0, 10);
                if (nonPending.length === 0) {
                    historyDiv.innerHTML = '<div style="color: var(--text-dim); font-size: 0.85rem;">No request history</div>';
                } else {
                    historyDiv.innerHTML = nonPending.map(r => `
                        <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: var(--bg); border-radius: 6px; font-size: 0.85rem;">
                            <span>${r.recipe_name} <span style="color: var(--text-dim);">- ${r.requester_name || 'Unknown'}</span></span>
                            <span style="color: ${r.status === 'planned' ? 'var(--accent)' : 'var(--text-dim)'};">${r.status}</span>
                        </div>
                    `).join('');
                }

                // Set default plan date
                document.getElementById('planDate').valueAsDate = new Date();

                // Also load month view if active
                if (_mpView === 'month') loadMealPlanMonth();

            } catch (e) {
                console.error('Error loading meal planner:', e);
            }
        }

        async function planFromRequest(requestId, recipeId, recipeName) {
            document.getElementById('planRecipeName').value = recipeName;
            document.getElementById('planDate').valueAsDate = new Date();
            // Store request ID to link when planning
            document.getElementById('planRecipeName').dataset.requestId = requestId;
            document.getElementById('planRecipeName').dataset.recipeId = recipeId;
        }

        async function addMealPlan() {
            const planDate = document.getElementById('planDate').value;
            const mealType = document.getElementById('planMealType').value;
            const recipeName = document.getElementById('planRecipeName').value;
            const requestId = document.getElementById('planRecipeName').dataset.requestId;
            const recipeId = document.getElementById('planRecipeName').dataset.recipeId;

            if (!planDate || !recipeName) {
                alert('Please enter a date and recipe name');
                return;
            }

            try {
                const res = await fetch('/api/meal-plans', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        plan_date: planDate,
                        meal_type: mealType,
                        recipe_id: recipeId || null,
                        recipe_name: recipeName,
                        request_id: requestId ? parseInt(requestId) : null
                    })
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('planRecipeName').value = '';
                    document.getElementById('planRecipeName').dataset.requestId = '';
                    document.getElementById('planRecipeName').dataset.recipeId = '';
                    loadMealPlanner();
                } else {
                    alert('Error: ' + (data.error || 'Failed to add meal plan'));
                }
            } catch (e) {
                alert('Error adding meal plan');
            }
        }

        async function dismissRequest(requestId) {
            try {
                await fetch(`/api/meal-requests/${requestId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'dismissed' })
                });
                loadMealPlanner();
            } catch (e) {
                console.error('Error dismissing request:', e);
            }
        }

        async function deleteMealPlan(planId) {
            try {
                await fetch(`/api/meal-plans/${planId}`, { method: 'DELETE' });
                _sidebarDayPlans = _sidebarDayPlans.filter(p => p.id !== planId);
                if (_sidebarDayPlans.length === 0) _sidebarShowingAdd = true;
                document.getElementById('mealSidebarTitle').textContent = _sidebarShowingAdd ? 'Add Meal' : "Today's Menu";
                document.getElementById('mealSidebarFilters').style.display = _sidebarShowingAdd ? '' : 'none';
                renderMealSidebar();
                loadMealPlanner();
            } catch (e) {
                console.error('Error deleting meal plan:', e);
            }
        }

        const PREMADE_MEAL_PLANS = {
            'high-protein': [
                { day: 0, meal: 'dinner', id: 'hulk-chicken-thigh-feast', recipe: 'Juicy Chicken Thigh Feast' },
                { day: 1, meal: 'dinner', id: 'hulk-beef-stir-fry', recipe: 'Massive Beef Stir-Fry' },
                { day: 2, meal: 'dinner', id: 'garlic-butter-salmon', recipe: 'Garlic Butter Salmon' },
                { day: 3, meal: 'dinner', id: 'df-mediterranean-turkey-meatballs', recipe: 'Mediterranean Turkey Meatballs' },
                { day: 4, meal: 'dinner', id: 'grilled-steak-chimichurri', recipe: 'Grilled Steak with Chimichurri' },
                { day: 5, meal: 'dinner', id: 'df-chicken-shawarma-bowl', recipe: 'Chicken Shawarma Bowl' },
                { day: 6, meal: 'dinner', id: 'slow-cooker-beef-short-ribs', recipe: 'Slow Cooker Beef Short Ribs' }
            ],
            'easy-weeknight': [
                { day: 0, meal: 'dinner', id: 'lemon-herb-chicken-rice', recipe: 'One-Pot Lemon Herb Chicken and Rice' },
                { day: 1, meal: 'dinner', id: 'df-teriyaki-beef-bowls', recipe: 'Teriyaki Beef Bowls' },
                { day: 2, meal: 'dinner', id: 'zucchini-noodle-bolognese', recipe: 'Zucchini Noodle Bolognese' },
                { day: 3, meal: 'dinner', id: 'thai-basil-chicken', recipe: 'Thai Basil Chicken Stir-Fry' },
                { day: 4, meal: 'dinner', id: 'cajun-chicken-rice', recipe: 'Cajun Chicken and Rice Skillet' },
                { day: 5, meal: 'dinner', id: 'hulk-bison-burger-stack', recipe: 'Triple Bison Burger Stack' },
                { day: 6, meal: 'dinner', id: 'bone-broth-chicken-soup', recipe: 'Bone Broth Chicken Soup' }
            ],
            'homestead': [
                { day: 0, meal: 'dinner', id: 'lemon-herb-roasted-chicken', recipe: 'Lemon Herb Roasted Chicken' },
                { day: 1, meal: 'dinner', id: 'df-sweet-potato-turkey-chili', recipe: 'Sweet Potato Turkey Chili' },
                { day: 2, meal: 'dinner', id: 'hulk-whole-roasted-chicken', recipe: 'Whole Roasted Chicken Demolition' },
                { day: 3, meal: 'dinner', id: 'hulk-shepherd-pie', recipe: "Hulk's Shepherd's Pie" },
                { day: 4, meal: 'dinner', id: 'mediterranean-baked-cod', recipe: 'Mediterranean Baked Cod' },
                { day: 5, meal: 'dinner', id: 'braised-lamb-shanks', recipe: 'Braised Lamb Shanks with Herbs' },
                { day: 6, meal: 'dinner', id: 'hulk-lamb-leg-roast', recipe: "Warrior's Roasted Lamb Leg" }
            ],
            'kid-friendly': [
                { day: 0, meal: 'dinner', id: 'chicken-rice-bowl', recipe: 'Garlic Herb Chicken Rice Bowl' },
                { day: 1, meal: 'dinner', id: 'df-orange-chicken', recipe: 'Crispy Orange Chicken' },
                { day: 2, meal: 'dinner', id: 'turkey-rice-meatballs', recipe: 'Turkey Rice Meatballs in Tomato Sauce' },
                { day: 3, meal: 'dinner', id: 'creamy-tomato-basil-soup', recipe: 'Creamy Tomato Basil Soup' },
                { day: 4, meal: 'dinner', id: 'stuffed-bell-peppers', recipe: 'Classic Stuffed Bell Peppers' },
                { day: 5, meal: 'dinner', id: 'hawaiian-chicken-rice', recipe: 'Hawaiian Chicken Rice Bowls' },
                { day: 6, meal: 'dinner', id: 'banana-pancakes', recipe: '3-Ingredient Banana Pancakes' }
            ],
            'meal-prep': [
                { day: 0, meal: 'dinner', id: 'chicken-rice-bowl', recipe: 'Garlic Herb Chicken Rice Bowl' },
                { day: 1, meal: 'dinner', id: 'grilled-chicken-salad-ranch', recipe: 'Grilled Chicken Salad with Ranch' },
                { day: 2, meal: 'dinner', id: 'df-lamb-kofta-lettuce-wraps', recipe: 'Lamb Kofta Lettuce Wraps' },
                { day: 3, meal: 'dinner', id: 'ginger-beef-rice', recipe: 'Ginger Beef with Broccoli and Rice' },
                { day: 4, meal: 'dinner', id: 'df-beef-vegetable-stir-fry', recipe: 'Beef and Vegetable Stir-Fry' },
                { day: 5, meal: 'dinner', id: 'hulk-double-chicken-bowl', recipe: 'Double Chicken Power Bowl' },
                { day: 6, meal: 'dinner', id: 'df-coconut-curry-chicken', recipe: 'Creamy Coconut Curry Chicken' }
            ]
        };

        async function applyMealPlan(planType) {
            const plan = PREMADE_MEAL_PLANS[planType];
            if (!plan) return;

            const today = new Date();
            // Find next Monday (or today if it's Monday)
            const dayOfWeek = today.getDay();
            const daysUntilMonday = dayOfWeek === 0 ? 1 : dayOfWeek === 1 ? 0 : 8 - dayOfWeek;
            const startDate = new Date(today);
            startDate.setDate(today.getDate() + daysUntilMonday);

            let added = 0;
            for (const item of plan) {
                const mealDate = new Date(startDate);
                mealDate.setDate(startDate.getDate() + item.day);
                // Use local date, not UTC
                const dateStr = mealDate.getFullYear() + '-' + String(mealDate.getMonth() + 1).padStart(2, '0') + '-' + String(mealDate.getDate()).padStart(2, '0');

                try {
                    await fetch('/api/meal-plans', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            plan_date: dateStr,
                            meal_type: item.meal,
                            recipe_id: item.id,
                            recipe_name: item.recipe
                        })
                    });
                    added++;
                } catch (e) {
                    console.error('Error adding meal:', e);
                }
            }

            showToast(`Added ${added} meals to your plan starting ${startDate.toLocaleDateString()}`);
            loadMealPlanner();
        }

        // ============== Meal Suggestion Sidebar ==============
        let _sidebarDate = null;
        let _sidebarMealType = 'all';

        let _sidebarDayPlans = [];
        let _sidebarShowingAdd = false;

        async function openMealSidebar(dateStr) {
            _sidebarDate = dateStr;
            _sidebarMealType = 'all';
            _sidebarDayPlans = [];

            // Format the date nicely
            const d = new Date(dateStr + 'T12:00:00');
            const days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
            const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            document.getElementById('mealSidebarDate').textContent = days[d.getDay()] + ', ' + months[d.getMonth()] + ' ' + d.getDate();

            // Fetch meals for this day
            try {
                const res = await fetch(`/api/meal-plans?start_date=${dateStr}&end_date=${dateStr}`);
                _sidebarDayPlans = await res.json();
            } catch (e) {
                _sidebarDayPlans = [];
            }

            // If no meals, go straight to add mode
            _sidebarShowingAdd = _sidebarDayPlans.length === 0;

            // Reset filter buttons
            document.querySelectorAll('.meal-type-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('.meal-type-btn[onclick="filterSidebarMealType(\'all\')"]').classList.add('active');

            // Ensure recipes are loaded
            if (allRecipes.length === 0) await loadRecipes();

            document.getElementById('mealSidebarTitle').textContent = _sidebarShowingAdd ? 'Add Meal' : "Today's Menu";
            document.getElementById('mealSidebarFilters').style.display = _sidebarShowingAdd ? '' : 'none';
            renderMealSidebar();
            document.getElementById('mealSidebarBackdrop').classList.add('show');
            document.getElementById('mealSidebar').classList.add('show');
        }

        function showSidebarAddMeal() {
            _sidebarShowingAdd = true;
            document.getElementById('mealSidebarTitle').textContent = 'Add Meal';
            document.getElementById('mealSidebarFilters').style.display = '';
            renderMealSidebar();
        }

        function showSidebarDayMenu() {
            _sidebarShowingAdd = false;
            document.getElementById('mealSidebarTitle').textContent = "Today's Menu";
            document.getElementById('mealSidebarFilters').style.display = 'none';
            renderMealSidebar();
        }

        function closeMealSidebar() {
            document.getElementById('mealSidebarBackdrop').classList.remove('show');
            document.getElementById('mealSidebar').classList.remove('show');
        }

        function filterSidebarMealType(type) {
            _sidebarMealType = type;
            document.querySelectorAll('.meal-type-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            renderMealSidebar();
        }

        function renderMealSidebar() {
            const body = document.getElementById('mealSidebarBody');

            if (!_sidebarShowingAdd) {
                // Day menu view — show existing meals + add button
                let html = '';
                const mealOrder = ['breakfast', 'lunch', 'dinner', 'snack'];
                const grouped = {};
                _sidebarDayPlans.forEach(p => {
                    if (!grouped[p.meal_type]) grouped[p.meal_type] = [];
                    grouped[p.meal_type].push(p);
                });

                mealOrder.forEach(type => {
                    if (!grouped[type]) return;
                    html += `<div class="sidebar-meal-group">
                        <div class="sidebar-meal-type">${type.charAt(0).toUpperCase() + type.slice(1)}</div>`;
                    grouped[type].forEach(p => {
                        html += `<div class="sidebar-meal-item">
                            <div class="sidebar-meal-name" ${p.recipe_id ? `onclick="if(allRecipes.length===0){loadRecipes().then(()=>showRecipe('${p.recipe_id}'))}else{showRecipe('${p.recipe_id}')}" style="cursor:pointer; color: var(--accent);"` : ''}>${escapeHtml(p.recipe_name)}</div>
                            <button onclick="deleteMealPlan(${p.id})" class="delete-btn" aria-label="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m2 0v14a2 2 0 01-2 2H8a2 2 0 01-2-2V6h12z"/></svg></button>
                        </div>`;
                    });
                    html += '</div>';
                });

                html += `<button class="sidebar-add-meal-btn" onclick="showSidebarAddMeal()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M12 5v14M5 12h14"/></svg>
                    Add Meal
                </button>`;

                body.innerHTML = html;
                return;
            }

            // Add meal view — recipe browser
            const catMap = { hulk: 'dinner', side: 'dinner', soup: 'dinner', salad: 'lunch' };

            // Filter recipes by auto-filter and meal type
            let pool = allRecipes.slice();
            if (recipeAutoFilter && recipeAutoFilter.length) {
                pool = pool.filter(r => {
                    const fw = r.frameworks || [];
                    return recipeAutoFilter.every(f => fw.includes(f));
                });
            }
            if (_sidebarMealType !== 'all') {
                pool = pool.filter(r => {
                    const mapped = catMap[r.category] || r.category;
                    return mapped === _sidebarMealType;
                });
            }

            const cookedMap = {};
            recipeCookLog.forEach(c => {
                if (!cookedMap[c.recipe_id] || c.cooked_at > cookedMap[c.recipe_id]) {
                    cookedMap[c.recipe_id] = c.cooked_at;
                }
            });

            const now = new Date();
            const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();

            // 1. Favorites
            const favorites = pool.filter(r => recipeFavorites.has(r.id))
                .sort((a, b) => a.title.localeCompare(b.title));

            // 2. Recently Cooked (last 30 days)
            const recentlyCooked = pool
                .filter(r => cookedMap[r.id] && cookedMap[r.id] >= thirtyDaysAgo)
                .sort((a, b) => (cookedMap[b.id] || '').localeCompare(cookedMap[a.id] || ''))
                .slice(0, 6);

            // 3. Try Something New (never cooked)
            const cookedIds = new Set(recipeCookLog.map(c => c.recipe_id));
            const tryNew = pool.filter(r => !cookedIds.has(r.id));
            // Shuffle
            for (let i = tryNew.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [tryNew[i], tryNew[j]] = [tryNew[j], tryNew[i]];
            }
            const tryNewSlice = tryNew.slice(0, 8);

            // 4. All recipes
            const allSorted = pool.slice().sort((a, b) => a.title.localeCompare(b.title));

            let html = '';
            // Back button when day has meals
            if (_sidebarDayPlans.length > 0) {
                html += `<button class="sidebar-back-btn" onclick="showSidebarDayMenu()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                    Back to menu
                </button>`;
            }
            if (favorites.length) html += renderSuggestionGroup('Favorites', favorites);
            if (recentlyCooked.length) html += renderSuggestionGroup('Recently Cooked', recentlyCooked);
            if (tryNewSlice.length) html += renderSuggestionGroup('Try Something New', tryNewSlice);
            html += renderSuggestionGroup('All Recipes', allSorted);

            if (!html) html = '<div style="text-align: center; padding: 2rem; color: var(--text-dim);">No recipes match filters</div>';
            body.innerHTML = html;
        }

        function renderSuggestionGroup(title, recipes) {
            if (!recipes.length) return '';
            const catMap = { hulk: 'dinner', side: 'dinner', soup: 'dinner', salad: 'lunch' };
            const cards = recipes.map(r => {
                const cookCount = getRecipeCookCount(r.id);
                const totalTime = (r.prepTime || 0) + (r.cookTime || 0);
                const protein = r.nutrition?.protein || 0;
                const mapped = catMap[r.category] || r.category;
                return `<div class="suggestion-card">
                    <div class="suggestion-card-info" onclick="event.stopPropagation(); if(allRecipes.length===0){loadRecipes().then(()=>showRecipe('${r.id}'))}else{showRecipe('${r.id}')}">
                        <div class="sc-title">${escapeHtml(r.title)}</div>
                        <div class="sc-meta">
                            <span>${totalTime}min</span>
                            <span>${protein}g protein</span>
                            ${cookCount > 0 ? '<span>' + cookCount + 'x cooked</span>' : ''}
                        </div>
                    </div>
                    <button class="suggestion-card-add" onclick="event.stopPropagation(); addSidebarRecipeToPlan('${r.id}', '${mapped}')" title="Add to plan">+</button>
                </div>`;
            }).join('');
            return `<div class="suggestion-group"><div class="suggestion-group-title">${title}</div>${cards}</div>`;
        }

        async function addSidebarRecipeToPlan(recipeId, mappedCategory) {
            const recipe = allRecipes.find(r => r.id === recipeId);
            if (!recipe || !_sidebarDate) return;

            const mealType = _sidebarMealType !== 'all' ? _sidebarMealType : mappedCategory;

            try {
                const res = await fetch('/api/meal-plans', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        plan_date: _sidebarDate,
                        meal_type: mealType,
                        recipe_id: recipe.id,
                        recipe_name: recipe.title
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Added ${recipe.title} to ${mealType} on ${_sidebarDate}`);
                } else {
                    showToast('Error: ' + (data.error || 'Failed to add'), 'error');
                    return;
                }
                // Refresh sidebar day plans and show day menu
                try {
                    const refreshRes = await fetch(`/api/meal-plans?start_date=${_sidebarDate}&end_date=${_sidebarDate}`);
                    _sidebarDayPlans = await refreshRes.json();
                } catch (e2) { /* ignore */ }
                _sidebarShowingAdd = false;
                document.getElementById('mealSidebarTitle').textContent = "Today's Menu";
                document.getElementById('mealSidebarFilters').style.display = 'none';
                renderMealSidebar();
                loadMealPlanner();
                if (_mpView === 'month') loadMealPlanMonth();
            } catch (e) {
                showToast('Error adding meal', 'error');
            }
        }

        // ============== Grocery List Functions ==============
        const GROCERY_CATEGORIES = {
            produce: { emoji: '🥬', label: 'Produce', color: '#22c55e' },
            meat: { emoji: '🥩', label: 'Meat', color: '#ef4444' },
            dairy: { emoji: '🧈', label: 'Dairy', color: '#f59e0b' },
            pantry: { emoji: '🥫', label: 'Pantry', color: '#8b5cf6' },
            frozen: { emoji: '🧊', label: 'Frozen', color: '#3b82f6' },
            bakery: { emoji: '🍞', label: 'Bakery', color: '#d97706' },
            other: { emoji: '📦', label: 'Other', color: '#6b7280' }
        };

        async function loadGroceryList() {
            try {
                const res = await fetch('/api/grocery');
                const items = await res.json();

                const listDiv = document.getElementById('groceryListItems');
                const emptyDiv = document.getElementById('groceryEmptyState');

                if (!items.length || items.error) {
                    listDiv.innerHTML = '';
                    emptyDiv.style.display = 'block';
                    return;
                }

                emptyDiv.style.display = 'none';

                // Group by category
                const grouped = {};
                items.forEach(item => {
                    const cat = item.category || 'other';
                    if (!grouped[cat]) grouped[cat] = [];
                    grouped[cat].push(item);
                });

                let html = '';
                for (const [cat, catItems] of Object.entries(grouped)) {
                    const catInfo = GROCERY_CATEGORIES[cat] || GROCERY_CATEGORIES.other;
                    html += `<div style="margin-bottom: 0.75rem;">
                        <div style="font-size: 0.8rem; font-weight: 600; color: ${catInfo.color}; margin-bottom: 0.25rem;">${catInfo.emoji} ${catInfo.label}</div>`;

                    catItems.forEach(item => {
                        const checkedStyle = item.checked ? 'text-decoration: line-through; opacity: 0.5;' : '';
                        html += `
                            <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; background: var(--bg); border-radius: 6px; margin-bottom: 0.25rem; ${checkedStyle}">
                                <input type="checkbox" ${item.checked ? 'checked' : ''} onchange="toggleGroceryItem(${item.id}, this.checked)" style="width: 18px; height: 18px; cursor: pointer;">
                                <span style="flex: 1;">${escapeHtml(item.item)}</span>
                                ${item.quantity ? `<span style="color: var(--text-dim); font-size: 0.85rem;">${escapeHtml(item.quantity)}</span>` : ''}
                                <button onclick="deleteGroceryItem(${item.id})" class="delete-btn" title="Delete" aria-label="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m2 0v14a2 2 0 01-2 2H8a2 2 0 01-2-2V6h12z"/></svg></button>
                            </div>`;
                    });

                    html += '</div>';
                }

                listDiv.innerHTML = html;
            } catch (e) {
                console.error('Error loading grocery list:', e);
            }
        }

        async function addGroceryItem() {
            const itemInput = document.getElementById('groceryItem');
            const qtyInput = document.getElementById('groceryQty');
            const catSelect = document.getElementById('groceryCategory');

            const item = itemInput.value.trim();
            if (!item) {
                showToast('Please enter an item name', 'error');
                return;
            }

            try {
                const res = await fetch('/api/grocery', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        item: item,
                        quantity: qtyInput.value.trim() || null,
                        category: catSelect.value
                    })
                });
                const data = await res.json();
                if (data.success) {
                    itemInput.value = '';
                    qtyInput.value = '';
                    loadGroceryList();
                } else {
                    showToast('Error adding item', 'error');
                }
            } catch (e) {
                showToast('Error adding item', 'error');
            }
        }

        async function toggleGroceryItem(id, checked) {
            try {
                await fetch(`/api/grocery/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ checked: checked ? 1 : 0 })
                });
                loadGroceryList();
            } catch (e) {
                console.error('Error toggling item:', e);
            }
        }

        async function deleteGroceryItem(id) {
            try {
                await fetch(`/api/grocery/${id}`, { method: 'DELETE' });
                loadGroceryList();
            } catch (e) {
                console.error('Error deleting item:', e);
            }
        }

        async function clearCheckedGroceries() {
            if (!confirm('Clear all checked items?')) return;
            try {
                await fetch('/api/grocery/checked', { method: 'DELETE' });
                loadGroceryList();
                showToast('Checked items cleared');
            } catch (e) {
                showToast('Error clearing items', 'error');
            }
        }

        async function clearAllGroceries() {
            if (!confirm('Clear entire grocery list?')) return;
            try {
                await fetch('/api/grocery/all', { method: 'DELETE' });
                loadGroceryList();
                showToast('Grocery list cleared');
            } catch (e) {
                showToast('Error clearing list', 'error');
            }
        }

        async function generateGroceryList() {
            try {
                showToast('Generating grocery list...', 'info');
                const res = await fetch('/api/grocery/generate', { method: 'POST' });
                const data = await res.json();

                if (data.error) {
                    showToast(data.error, 'error');
                    return;
                }

                if (data.success) {
                    showToast(`Added ${data.added} items from ${data.from_meals} meals`);
                    loadGroceryList();
                }
            } catch (e) {
                showToast('Error generating list', 'error');
                console.error('Error generating grocery list:', e);
            }
        }

        // Add Enter key support for grocery input
        document.addEventListener('DOMContentLoaded', () => {
            const groceryInput = document.getElementById('groceryItem');
            if (groceryInput) {
                groceryInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') addGroceryItem();
                });
            }
        });

        async function loadTodaySchedule() {
            const container = document.getElementById('todayScheduleEvents');
            const dateEl = document.getElementById('todayScheduleDate');
            if (!container) return;

            try {
                const today = new Date();
                if (dateEl) {
                    dateEl.textContent = today.toLocaleDateString('en-US', {
                        weekday: 'long', month: 'short', day: 'numeric'
                    });
                }

                const res = await fetch('/api/calendar/events');
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const events = await res.json();

                if (events.length === 0) {
                    container.innerHTML = '<div class="today-schedule-empty">No events today</div>';
                    return;
                }

                let html = '';

                // Next-up banner
                const now = new Date();
                const next = events.find(e => !e.all_day && new Date(e.start) > now);
                if (next) {
                    const diff = new Date(next.start) - now;
                    const mins = Math.floor(diff / 60000);
                    const timeStr = mins < 60 ? mins + 'm' : Math.floor(mins/60) + 'h ' + (mins%60 > 0 ? (mins%60) + 'm' : '');
                    html += `<div class="today-schedule-next">Next: <strong>${escapeHtml(next.summary)}</strong> in ${timeStr}</div>`;
                }

                html += events.map(e => {
                    const isNow = !e.all_day && new Date(e.start) <= now && now < new Date(e.end);
                    const cls = isNow ? ' happening-now' : (e.all_day ? ' all-day-event' : '');
                    const time = e.all_day ? 'All day' : new Date(e.start).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
                    return `<div class="today-schedule-item${cls}">
                        <span class="today-schedule-time">${time}</span>
                        <span class="today-schedule-name">${escapeHtml(e.summary)}</span>
                    </div>`;
                }).join('');

                container.innerHTML = html;
            } catch (e) {
                container.innerHTML = '<div class="today-schedule-empty">Calendar unavailable</div>';
            }
        }

        async function loadDashboard() {
            try {
                const [analyticsRes, sessionsRes, topicsRes, gapsRes, historyRes] = await Promise.all([
                    fetch('/api/analytics'),
                    fetch('/api/sessions?limit=50'),
                    fetch('/api/topics'),
                    fetch('/api/gap-analysis'),
                    fetch('/api/history?limit=50')
                ]);

                analyticsData = await analyticsRes.json();
                sessionsData = await sessionsRes.json();
                allTopicsData = await topicsRes.json();
                const gapsData = await gapsRes.json();
                allHistoryData = await historyRes.json();

                const overview = analyticsData.overview || {};

                // Today's schedule
                loadTodaySchedule();

                // Unified sessions feed
                if (typeof loadUnifiedSessions === 'function') loadUnifiedSessions();

                // Overview stats
                renderAnalyticsOverview(overview);

                // 12-week trend
                renderWeeklyTrend(analyticsData.weekly_totals || []);

                // 90-day heatmap
                renderActivityHeatmap(analyticsData.daily_activity || {});

                // Streak calendar
                renderStreakCalendar(analyticsData.streak?.active_days || []);

                // Activity calendar (month view)
                renderActivityCalendar(analyticsData.daily_activity || {});

                // Confidence distribution
                renderConfidenceDistribution(analyticsData.confidence_distribution || {});

                // Session types
                renderSessionTypes(analyticsData.session_types || {});

                // New vs Review
                renderNewVsReview(analyticsData.new_vs_review || {});

                // Topic frequency
                renderTopicFrequency(analyticsData.topic_frequency || {});

                // Review timeline
                renderReviewTimeline(analyticsData.review_timeline || {});

                // All topics - re-apply filters
                filterTopics();

                // Gap analysis
                renderHealthGaps(gapsData);

                // Protocol widget
                loadProtocolWidget();

                // Protein tracker widget
                loadProteinTracker();

                // Smart gap suggestions
                renderGapSuggestions(gapsData);

                // Check reminders
                checkReminders();

            } catch (e) {
                console.error('Failed to load dashboard:', e);
                showToast('Failed to load dashboard. Please refresh.', 'error');
            }
        }

        function renderAnalyticsOverview(overview) {
            const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
            el('statTotalTopics', overview.total_topics || 0);
            el('statTotalSessions', overview.total_sessions || 0);
            el('statThisWeek', overview.this_week || 0);
            el('statCurrentStreak', overview.current_streak || 0);
            el('statDueReviews', overview.due_reviews || 0);
        }

        function renderWeeklyTrend(weeklyTotals) {
            const container = document.getElementById('weeklyTrend');
            if (!container || weeklyTotals.length === 0) return;
            const maxVal = Math.max(...weeklyTotals.map(w => w.total), 1);
            container.innerHTML = weeklyTotals.map(w => {
                const h = Math.max((w.total / maxVal) * 90, 2);
                return `<div class="trend-bar" title="${w.week}: ${w.total} topics">
                    <div class="trend-bar-value">${w.total || ''}</div>
                    <div class="trend-bar-fill${w.current ? ' current' : ''}" style="height: ${h}px;"></div>
                    <div class="trend-bar-label">${w.week}</div>
                </div>`;
            }).join('');
        }

        function renderActivityHeatmap(dailyActivity) {
            const grid = document.getElementById('activityHeatmap');
            const monthsEl = document.getElementById('heatmapMonths');
            if (!grid) return;

            const today = new Date();
            const cells = [];
            const months = new Set();

            // 91 days = 13 full weeks
            for (let i = 90; i >= 0; i--) {
                const d = new Date(today);
                d.setDate(d.getDate() - i);
                const key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
                const count = dailyActivity[key] || 0;
                const monthLabel = d.toLocaleDateString('en-US', { month: 'short' });
                months.add(monthLabel);

                let color;
                if (count === 0) color = 'var(--bg)';
                else if (count <= 2) color = 'rgba(16, 185, 129, 0.25)';
                else if (count <= 5) color = 'rgba(16, 185, 129, 0.5)';
                else if (count <= 10) color = 'rgba(16, 185, 129, 0.75)';
                else color = 'var(--accent)';

                cells.push(`<div class="heatmap-cell" style="background: ${color};" title="${key}: ${count} topics"></div>`);
            }

            grid.innerHTML = cells.join('');
            if (monthsEl) {
                const uniqueMonths = [...months];
                monthsEl.innerHTML = uniqueMonths.map(m => `<span>${m}</span>`).join('');
            }
        }

        function renderConfidenceDistribution(dist) {
            const container = document.getElementById('confidenceDistribution');
            if (!container) return;
            const buckets = [
                { key: 'mastered', label: 'Mastered', color: 'var(--green)' },
                { key: 'strong', label: 'Strong', color: 'var(--accent)' },
                { key: 'learning', label: 'Learning', color: 'var(--cyan)' },
                { key: 'weak', label: 'Weak', color: 'var(--orange)' },
            ];
            container.innerHTML = '<div class="conf-dist">' + buckets.map(b =>
                `<div class="conf-bucket">
                    <div class="conf-bucket-value" style="color: ${b.color};">${dist[b.key] || 0}</div>
                    <div class="conf-bucket-label">${b.label}</div>
                </div>`
            ).join('') + '</div>';
        }

        function renderTopicFrequency(topicFreq) {
            const container = document.getElementById('topicFrequency');
            if (!container) return;
            const entries = Object.entries(topicFreq);
            if (entries.length === 0) {
                container.innerHTML = '<p style="color: var(--text-dim);">No topic data yet</p>';
                return;
            }
            const maxCount = Math.max(...entries.map(([, v]) => v), 1);
            container.innerHTML = entries.map(([name, count]) => {
                const pct = Math.max((count / maxCount) * 100, 8);
                return `<div class="freq-item">
                    <span class="freq-name">${escapeHtml(name)}</span>
                    <div class="freq-bar-track">
                        <div class="freq-bar-fill" style="width: ${pct}%;"><span>${count}</span></div>
                    </div>
                </div>`;
            }).join('');
        }

        function renderNewVsReview(data) {
            const container = document.getElementById('newVsReview');
            if (!container) return;
            const weeks = data.weeks || [];
            if (weeks.length === 0) {
                container.innerHTML = '<p style="color: var(--text-dim);">No data yet</p>';
                return;
            }
            const maxVal = Math.max(...weeks.map(w => w.new + w.review), 1);
            const bars = weeks.map(w => {
                const total = w.new + w.review;
                const newH = Math.max((w.new / maxVal) * 90, total > 0 ? 2 : 0);
                const revH = Math.max((w.review / maxVal) * 90, total > 0 ? 2 : 0);
                return `<div class="nvr-col">
                    <div class="nvr-stack">
                        <div class="nvr-segment" style="height: ${revH}px; background: var(--cyan);" title="Review: ${w.review}"></div>
                        <div class="nvr-segment" style="height: ${newH}px; background: var(--accent);" title="New: ${w.new}"></div>
                    </div>
                    <div class="nvr-label"${w.current ? ' style="color: var(--accent); font-weight: 600;"' : ''}>${w.week}</div>
                </div>`;
            }).join('');
            container.innerHTML = `<div class="nvr-chart">${bars}</div>
                <div class="nvr-legend">
                    <span><span class="nvr-legend-dot" style="background: var(--accent);"></span>New</span>
                    <span><span class="nvr-legend-dot" style="background: var(--cyan);"></span>Review</span>
                </div>`;
        }

        function renderReviewTimeline(timeline) {
            const container = document.getElementById('reviewTimeline');
            if (!container) return;

            const buckets = [
                { key: 'overdue', label: 'Overdue', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.3)' },
                { key: 'this_week', label: 'This Week', color: 'var(--orange)', bg: 'rgba(245, 158, 11, 0.15)', border: 'rgba(245, 158, 11, 0.3)' },
                { key: 'next_week', label: 'Next Week', color: 'var(--cyan)', bg: 'rgba(6, 182, 212, 0.15)', border: 'rgba(6, 182, 212, 0.3)' },
                { key: 'later', label: 'Later', color: 'var(--text-dim)', bg: 'var(--bg)', border: 'var(--border)' },
                { key: 'solid', label: 'Solid (90%+)', color: 'var(--green)', bg: 'rgba(34, 197, 94, 0.1)', border: 'rgba(34, 197, 94, 0.3)' },
            ];

            let html = '';
            for (const b of buckets) {
                const items = timeline[b.key] || [];
                if (items.length === 0) continue;
                html += `<div class="review-bucket">
                    <div class="review-bucket-header">
                        <span class="review-bucket-label" style="color: ${b.color};">${b.label}</span>
                        <span class="review-bucket-count" style="background: ${b.bg}; color: ${b.color};">${items.length}</span>
                    </div>
                    <div class="review-bucket-topics">
                        ${items.slice(0, 30).map(t => `<span class="review-tag" style="border-color: ${b.border}; color: ${b.color}; cursor:pointer;" onclick="showTopicReview('${escapeHtml(t.name).replace(/'/g, "\\'")}')">${escapeHtml(t.name)}</span>`).join('')}
                        ${items.length > 30 ? `<span class="review-tag" style="color: var(--text-dim);">+${items.length - 30} more</span>` : ''}
                    </div>
                </div>`;
            }

            if (!html) {
                html = '<p style="color: var(--green);">All topics are on track!</p>';
            }
            container.innerHTML = html;
        }

        function showTopicReview(topicName) {
            const key = topicName.toLowerCase();
            // 1) Check for a hand-written prompt for this exact topic
            const specific = (typeof healthGapPrompts !== 'undefined') && healthGapPrompts[key];
            let prompt, category;
            if (specific) {
                prompt = specific;
            } else {
                // 2) Look up category from per-profile topic→category map
                const catMap = (typeof healthTopicCategories !== 'undefined') && healthTopicCategories[currentProfileId];
                category = catMap && catMap[key];
                if (category && typeof healthGapDefaultPrompt !== 'undefined') {
                    prompt = healthGapDefaultPrompt.replace('$TOPIC$', topicName).replace('$CATEGORY$', category);
                } else {
                    // 3) Generic fallback — no category context available
                    prompt = 'Write a detailed, practical article about "' + topicName +
                        '". Cover key techniques, drills, progressions, and real-world application. ' +
                        'Be specific — include sets/reps/durations where relevant, common mistakes, and how to progress over time.';
                }
            }
            prompt += ' Format as markdown with an H1 title. Then feed it to the current profile\'s health inbox.';

            document.getElementById('gapModalTitle').textContent = 'Review: ' + topicName;
            document.getElementById('gapModalCategory').innerHTML = category
                ? '<span class="gap-topic missing" style="cursor:default;">' + escapeHtml(category) + '</span>'
                : '';
            document.getElementById('gapModalPrompt').textContent = prompt;
            document.getElementById('gapModalHint').textContent = 'Click to copy prompt';
            document.getElementById('gapModalHint').style.color = 'var(--text-dim)';
            document.getElementById('gapPromptModal').classList.add('show');
        }

        // Render recent history (profile-filtered) for dashboard
        function renderRecentHistory(history) {
            const container = document.getElementById('recentSessions');
            if (!container) return;

            if (history.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="icon">💬</div>
                        <p>No sessions yet for this profile.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = history.map((h, i) => `
                <div class="session-item" onclick="showHistoryEntry(${h.id})">
                    <div class="session-header">
                        <span class="session-type ${h.session_type || 'session'}">${escapeHtml(h.session_type)}</span>
                        <span class="session-date">${h.created_at ? new Date(h.created_at + 'Z').toLocaleDateString() : 'Recent'}</span>
                    </div>
                    <div class="session-title">${escapeHtml(h.topic || 'Session')}</div>
                </div>
            `).join('');
        }

        function filterHistory() {
            if (!document.getElementById('recentSessions')) return;
            const searchEl = document.getElementById('historySearch');
            const search = searchEl ? searchEl.value.toLowerCase() : '';

            let filtered = allHistoryData;
            if (search) {
                filtered = filtered.filter(h =>
                    (h.topic || '').toLowerCase().includes(search) ||
                    (h.session_type || '').toLowerCase().includes(search)
                );
                historyDisplayCount = filtered.length; // show all when searching
            } else {
                // Reset to 5 only if no search active and user hasn't expanded
                if (!searchEl || !searchEl.value) {
                    // Preserve current display count on refresh
                    historyDisplayCount = Math.max(historyDisplayCount, 5);
                }
            }

            const visible = filtered.slice(0, historyDisplayCount);
            renderRecentHistory(visible);
            updateHistoryLoadMore(filtered.length);
        }

        function showMoreHistory() {
            historyDisplayCount += 10;
            filterHistory();
        }

        function updateHistoryLoadMore(totalCount) {
            const btn = document.getElementById('historyLoadMore');
            const countEl = document.getElementById('historyResultCount');
            const searchVal = (document.getElementById('historySearch')?.value || '').trim();

            if (searchVal) {
                countEl.textContent = totalCount + ' result' + (totalCount !== 1 ? 's' : '');
                btn.style.display = 'none';
            } else if (totalCount > historyDisplayCount) {
                const showing = Math.min(historyDisplayCount, totalCount);
                countEl.textContent = '';
                btn.textContent = 'Show more (' + showing + ' of ' + totalCount + ')';
                btn.style.display = 'block';
            } else {
                countEl.textContent = totalCount > 0 ? totalCount + ' entries' : '';
                btn.style.display = 'none';
            }
        }

        // Show history entry in modal
        async function showHistoryEntry(id) {
            try {
                const res = await fetch(`/api/history/${id}`);
                if (!res.ok) return;
                const entry = await res.json();

                currentHistoryId = id;
                currentSession = { topic: entry.topic, name: null, historyId: id };

                document.getElementById('modalTitle').textContent = entry.topic || 'Session';
                document.getElementById('modalContentMd').innerHTML = marked.parse(entry.response || entry.prompt || '');
                document.getElementById('modalContentMd').style.display = 'block';
                document.getElementById('modalTopics').innerHTML = '';
                lastFocusedElement = document.activeElement;
                const modal = document.getElementById('sessionModal');
                modal.classList.add('show');
                setTimeout(() => {
                    modal.scrollTo(0, 0);
                    const mc = modal.querySelector('.modal-content');
                    if (mc) mc.scrollTo(0, 0);
                }, 0);
            } catch (e) {
                console.error('Error loading history entry:', e);
            }
        }

        function renderRecentSessions(sessions) {
            const container = document.getElementById('recentSessions');

            if (sessions.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="icon">💬</div>
                        <p>No sessions yet. Chat with Claude Code and I'll track your learning!</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = sessions.map((s, i) => `
                <div class="session-item" onclick="showSession(${i})">
                    <div class="session-header">
                        <span class="session-type ${s.type || 'session'}">${escapeHtml(s.type)}</span>
                        <span class="session-date">${s.created ? new Date(s.created + 'Z').toLocaleDateString() : 'Recent'}</span>
                    </div>
                    <div class="session-title">${escapeHtml(s.topic)}</div>
                    <div class="session-topics">
                        ${(s.topics || []).slice(0, 4).map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('')}
                    </div>
                </div>
            `).join('');
        }

        function renderTopTopics(topicFreq) {
            const container = document.getElementById('topTopics');
            if (!container) return;
            const entries = Object.entries(topicFreq).slice(0, 5);

            if (entries.length === 0) {
                container.innerHTML = '<p style="color: var(--text-dim);">Topics will appear as you learn</p>';
                return;
            }

            container.innerHTML = entries.map(([name, count]) => `
                <div class="topic-item">
                    <span class="topic-name">${escapeHtml(name)}</span>
                    <span class="topic-count">${count} sessions</span>
                </div>
            `).join('');
        }

        function renderStreakCalendar(activeDays) {
            const container = document.getElementById('streakCalendar');
            const activeDaySet = new Set(activeDays);
            let html = '';

            for (let i = 27; i >= 0; i--) {
                const d = new Date();
                d.setDate(d.getDate() - i);
                // Use local date, not UTC
                const key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
                const isActive = activeDaySet.has(key);
                const isToday = i === 0;
                html += `<div class="streak-day ${isActive ? 'active' : ''} ${isToday ? 'today' : ''}" title="${key}"></div>`;
            }

            container.innerHTML = html;
        }

        function renderActivityCalendar(dailyActivity) {
            const container = document.getElementById('activityCalendar');
            const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                               'July', 'August', 'September', 'October', 'November', 'December'];

            // Update label
            document.getElementById('calendarMonthLabel').textContent = monthNames[calendarMonth] + ' ' + calendarYear;

            // Get first day of month and number of days
            const firstDay = new Date(calendarYear, calendarMonth, 1);
            const lastDay = new Date(calendarYear, calendarMonth + 1, 0);
            const daysInMonth = lastDay.getDate();
            const startDayOfWeek = firstDay.getDay();

            // Today for highlighting
            const today = new Date();
            const todayKey = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');

            let html = '';

            // Empty cells for days before month starts
            for (let i = 0; i < startDayOfWeek; i++) {
                html += '<div class="calendar-day empty"></div>';
            }

            // Days of the month
            for (let day = 1; day <= daysInMonth; day++) {
                const dateKey = calendarYear + '-' + String(calendarMonth + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
                const count = dailyActivity[dateKey] || 0;
                const isToday = dateKey === todayKey;
                const hasActivity = count > 0;
                const isHigh = count >= 3;

                html += '<div class="calendar-day' +
                    (hasActivity ? ' has-activity' : '') +
                    (isHigh ? ' high' : '') +
                    (isToday ? ' today' : '') +
                    '" title="' + dateKey + ': ' + count + ' sessions">' +
                    day +
                    (count > 1 ? '<span class="activity-count">' + count + '</span>' : '') +
                    '</div>';
            }

            container.innerHTML = html;
        }

        function changeMonth(delta) {
            calendarMonth += delta;
            if (calendarMonth > 11) {
                calendarMonth = 0;
                calendarYear++;
            } else if (calendarMonth < 0) {
                calendarMonth = 11;
                calendarYear--;
            }
            renderActivityCalendar(analyticsData.daily_activity || {});
        }

        function renderSessionTypes(types) {
            const container = document.getElementById('sessionTypes');
            const entries = Object.entries(types);

            if (entries.length === 0) {
                container.innerHTML = '<p style="color: var(--text-dim);">Session types will appear here</p>';
                return;
            }

            const total = entries.reduce((a, [, v]) => a + v, 0);

            container.innerHTML = entries.map(([type, count]) => {
                const pct = Math.round((count / total) * 100);
                return `
                    <div class="progress-item">
                        <div class="progress-header">
                            <span>${escapeHtml(type)}</span>
                            <span>${count} (${pct}%)</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${pct}%;"></div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        let _sessionTopicsList = [];
        let _selectedTopic = '';
        let _highlightedIdx = -1;

        function openTopicDropdown() {
            filterTopicDropdown();
            document.getElementById('topicDropdown').classList.add('open');
            _highlightedIdx = -1;
        }

        function closeTopicDropdown() {
            setTimeout(() => document.getElementById('topicDropdown')?.classList.remove('open'), 150);
        }

        function filterTopicDropdown() {
            const input = document.getElementById('sessionTopicInput');
            const dropdown = document.getElementById('topicDropdown');
            const query = input.value.toLowerCase();

            const matches = query
                ? _sessionTopicsList.filter(t => t.toLowerCase().includes(query))
                : _sessionTopicsList;

            dropdown.innerHTML = `<div class="combo-option${!_selectedTopic ? ' active' : ''}" onmousedown="selectTopic('')">All Topics</div>` +
                matches.map(t => `<div class="combo-option${t === _selectedTopic ? ' active' : ''}" onmousedown="selectTopic('${escapeHtml(t)}')">${escapeHtml(t)}</div>`).join('');

            _highlightedIdx = -1;
            dropdown.classList.add('open');
        }

        function selectTopic(topic) {
            const input = document.getElementById('sessionTopicInput');
            const clearBtn = document.getElementById('topicComboClear');
            _selectedTopic = topic;
            if (topic) {
                input.value = topic;
                input.placeholder = topic;
                clearBtn.style.display = '';
            } else {
                input.value = '';
                input.placeholder = 'All Topics';
                clearBtn.style.display = 'none';
            }
            document.getElementById('topicDropdown').classList.remove('open');
            filterUnifiedSessions();
        }

        function clearTopicFilter() {
            selectTopic('');
            document.getElementById('sessionTopicInput').focus();
        }

        // Close dropdown on outside click
        document.addEventListener('click', (e) => {
            const box = document.getElementById('topicComboBox');
            if (box && !box.contains(e.target)) {
                document.getElementById('topicDropdown').classList.remove('open');
            }
        });

        // Keyboard nav for topic combo
        document.addEventListener('DOMContentLoaded', () => {
            const input = document.getElementById('sessionTopicInput');
            if (input) {
                input.addEventListener('blur', closeTopicDropdown);
                input.addEventListener('keydown', (e) => {
                    const dropdown = document.getElementById('topicDropdown');
                    const opts = dropdown.querySelectorAll('.combo-option');
                    if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        _highlightedIdx = Math.min(_highlightedIdx + 1, opts.length - 1);
                        opts.forEach((o, i) => o.classList.toggle('highlighted', i === _highlightedIdx));
                        opts[_highlightedIdx]?.scrollIntoView({ block: 'nearest' });
                    } else if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        _highlightedIdx = Math.max(_highlightedIdx - 1, 0);
                        opts.forEach((o, i) => o.classList.toggle('highlighted', i === _highlightedIdx));
                        opts[_highlightedIdx]?.scrollIntoView({ block: 'nearest' });
                    } else if (e.key === 'Enter' && _highlightedIdx >= 0) {
                        e.preventDefault();
                        opts[_highlightedIdx]?.dispatchEvent(new Event('mousedown'));
                    } else if (e.key === 'Escape') {
                        dropdown.classList.remove('open');
                        input.blur();
                    }
                });
            }
        });

        function filterTopics() {
            const search = (document.getElementById('topicSearch')?.value || '').toLowerCase();
            const masteryFilter = document.getElementById('topicMasteryFilter')?.value || '';
            const sortVal = document.getElementById('topicSortFilter')?.value || 'recent';

            let filtered = allTopicsData.slice();

            if (search) {
                filtered = filtered.filter(t => (t.name || '').toLowerCase().includes(search));
            }

            if (masteryFilter) {
                filtered = filtered.filter(t => {
                    const pct = Math.round((t.confidence_score || 0) * 100);
                    switch (masteryFilter) {
                        case 'new': return pct <= 25;
                        case 'learning': return pct > 25 && pct < 75;
                        case 'mastered': return pct >= 75;
                        default: return true;
                    }
                });
            }

            switch (sortVal) {
                case 'most-reviewed':
                    filtered.sort((a, b) => (b.review_count || 0) - (a.review_count || 0));
                    break;
                case 'least-reviewed':
                    filtered.sort((a, b) => (a.review_count || 0) - (b.review_count || 0));
                    break;
                case 'highest':
                    filtered.sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0));
                    break;
                case 'lowest':
                    filtered.sort((a, b) => (a.confidence_score || 0) - (b.confidence_score || 0));
                    break;
                case 'az':
                    filtered.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
                    break;
                default: // recent - keep original order from API
                    break;
            }

            const countEl = document.getElementById('topicResultCount');
            if (search || masteryFilter) {
                countEl.textContent = filtered.length + ' of ' + allTopicsData.length + ' topics';
            } else {
                countEl.textContent = allTopicsData.length + ' topics';
            }

            renderFilteredTopics(filtered);
        }

        function renderFilteredTopics(topics) {
            const container = document.getElementById('allTopics');

            if (topics.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="icon">🧠</div>
                        <p>No topics match your filters</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = topics.map(t => {
                const pct = Math.round((t.confidence_score || 0) * 100);
                const tier = pct >= 80 ? 'var(--green)' : pct >= 60 ? '#06b6d4' : pct >= 30 ? 'var(--yellow, #eab308)' : 'var(--pink, #ec4899)';
                return `
                    <div class="card" style="padding: 1rem; cursor: pointer;" onclick="showTopicReview('${escapeHtml(t.name).replace(/'/g, "\\'")}')">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 600;">${escapeHtml(t.name)}</span>
                            <span style="color: ${tier}; font-weight: 600;">${pct}%</span>
                        </div>
                        <div class="progress-bar" style="margin-top: 0.5rem;">
                            <div class="progress-fill" style="width: ${pct}%; background: ${tier};"></div>
                        </div>
                        <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 0.5rem;">
                            Reviewed ${t.review_count || 0} times
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Gap rendering functions (renderHealthGaps, etc.) provided by generate_gap_js in plugin.py

        let currentSession = null;
        let currentHistoryId = null;

        function showSession(index) {
            const session = sessionsData[index];
            if (!session) return;
            currentSession = session;

            document.getElementById('modalTitle').textContent = session.topic || 'Session';
            document.getElementById('modalTopics').innerHTML = (session.topics || []).map(t =>
                `<span class="topic-tag">${escapeHtml(t)}</span>`
            ).join('');

            // Render markdown as HTML
            document.getElementById('modalContentMd').style.display = 'block';
            document.getElementById('modalContentMd').innerHTML = marked.parse(session.content || 'No content');
            lastFocusedElement = document.activeElement;
            const modal = document.getElementById('sessionModal');
            modal.classList.add('show');
            // Scroll to top - use setTimeout to ensure DOM has rendered
            setTimeout(() => {
                modal.scrollTo(0, 0);
                const mc = modal.querySelector('.modal-content');
                if (mc) mc.scrollTo(0, 0);
            }, 0);
            // Focus the close button for accessibility
            modal.querySelector('.close-btn').focus();
        }

        let lastFocusedElement = null;

        function closeModal() {
            const modal = document.getElementById('sessionModal');
            modal.classList.remove('show');
            // Reset scroll position for next open
            modal.scrollTop = 0;
            const mc = modal.querySelector('.modal-content');
            if (mc) mc.scrollTop = 0;
            // Reset content
            document.getElementById('modalContentMd').innerHTML = '';
            currentSession = null;
            currentHistoryId = null;
            // Return focus to trigger element
            if (lastFocusedElement) {
                lastFocusedElement.focus();
                lastFocusedElement = null;
            }
        }

        async function deleteSession() {
            if (!currentSession) return;
            const title = currentSession.topic || currentSession.name || 'this session';
            if (!confirm('Permanently delete "' + title + '"?')) return;
            try {
                let res;
                if (currentSession._homesteadId) {
                    // Delete homestead entry
                    res = await fetch('/api/homestead/history/' + currentSession._homesteadId, {method: 'DELETE'});
                } else if (currentSession.historyId) {
                    // Delete history entry
                    res = await fetch('/api/history/' + currentSession.historyId, {method: 'DELETE'});
                } else if (currentSession.name) {
                    // Delete inbox file
                    res = await fetch('/api/sessions/' + encodeURIComponent(currentSession.name), {method: 'DELETE'});
                } else {
                    showToast('Nothing to delete', 'error');
                    return;
                }
                if (res.ok) {
                    showToast('Session deleted', 'success');
                    closeModal();
                    loadDashboard();
                } else {
                    const data = await res.json().catch(() => ({}));
                    showToast(data.error || 'Delete failed', 'error');
                }
            } catch (e) {
                showToast('Delete failed: ' + e.message, 'error');
            }
        }

        function downloadSessionHTML() {
            if (!currentSession) return;
            const title = currentSession.topic || 'Session';
            const content = document.getElementById('modalContentMd').innerHTML;
            const html = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>${escapeHtml(title)}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }
        h1, h2, h3 { margin-top: 1.5rem; }
        code { background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; }
        pre { background: #f4f4f4; padding: 1rem; overflow-x: auto; border-radius: 5px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
        th { background: #f4f4f4; }
    </style>
</head>
<body>
    <h1>${escapeHtml(title)}</h1>
    ${content}
</body>
</html>`;
            const blob = new Blob([html], {type: 'text/html'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
            a.download = slug + '.html';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('Downloaded: ' + slug + '.html', 'success');
        }

        function toggleShareDropdown(e) {
            e.stopPropagation();
            const dd = document.getElementById('shareDropdown');
            if (dd.style.display !== 'none') {
                dd.style.display = 'none';
                return;
            }
            // Build list of other profiles
            fetch('/api/profiles').then(r => r.json()).then(profiles => {
                dd.innerHTML = profiles
                    .filter(p => p.id !== currentProfileId)
                    .map(p => `<div onclick="shareSessionTo(${p.id}, '${escapeHtml(p.display_name)}')" style="padding: 0.6rem 1rem; cursor: pointer; white-space: nowrap; border-bottom: 1px solid var(--border);" onmouseenter="this.style.background='var(--bg-hover)'" onmouseleave="this.style.background=''">${escapeHtml(p.display_name)}</div>`)
                    .join('');
                dd.style.display = 'block';
            });
        }

        async function shareSessionTo(profileId, name) {
            document.getElementById('shareDropdown').style.display = 'none';
            if (!currentSession) return;
            try {
                const payload = { profile_id: profileId };
                if (currentSession.name) {
                    payload.filename = currentSession.name;
                } else if (currentSession.historyId) {
                    payload.history_id = currentSession.historyId;
                } else {
                    showToast('Nothing to share', 'error');
                    return;
                }
                const res = await fetch('/api/sessions/share', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Shared to ' + name, 'success');
                } else {
                    showToast(data.error || 'Share failed', 'error');
                }
            } catch (e) {
                showToast('Share failed: ' + e.message, 'error');
            }
        }

        // Close share dropdown when clicking elsewhere
        document.addEventListener('click', () => {
            document.getElementById('shareDropdown').style.display = 'none';
        });

        // WebSocket handled by shell.py connectWebSocket() with debounce

        // Export data as JSON file
        async function exportData() {
            try {
                const response = await fetch('/api/export');
                const data = await response.json();

                const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const _now = new Date();
                a.download = 'health-bot-backup-' + _now.getFullYear() + '-' + String(_now.getMonth() + 1).padStart(2, '0') + '-' + String(_now.getDate()).padStart(2, '0') + '.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                showToast('Export complete! File downloaded.', 'success');
            } catch (e) {
                showToast('Export failed: ' + e.message, 'error');
            }
        }

        // Import data from JSON file
        async function importData(event) {
            const file = event.target.files[0];
            if (!file) return;

            const merge = confirm('Merge with existing data?\\n\\nOK = Merge (keep existing + add new)\\nCancel = Replace (clear existing, import all)');

            try {
                const text = await file.text();
                const data = JSON.parse(text);
                data.merge = merge;

                const response = await fetch('/api/import', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (result.success) {
                    showToast('Import complete! Topics: ' + result.stats.topics + ', Files: ' + result.stats.inbox_files, 'success');
                    loadDashboard();
                } else {
                    showToast('Import failed: ' + result.error, 'error');
                }
            } catch (e) {
                showToast('Import failed: ' + e.message, 'error');
            }

            event.target.value = '';  // Reset file input
        }

        // toggleSettings and rescanFiles are defined in base.js — do not override here

        // Keyboard handlers for accessibility
        document.addEventListener('keydown', (e) => {
            // Escape key closes sidebar, modal, and settings menu
            if (e.key === 'Escape') {
                const sidebar = document.getElementById('mealSidebar');
                const modal = document.getElementById('sessionModal');
                const settingsMenu = document.getElementById('settingsMenu');

                if (sidebar && sidebar.classList.contains('show')) {
                    closeMealSidebar();
                } else if (modal.classList.contains('show')) {
                    closeModal();
                } else if (settingsMenu && settingsMenu.style.display === 'block') {
                    toggleSettings();
                    document.getElementById('settingsBtn').focus();
                }
            }
        });

        // Body Map - Issue selector
        let currentBodyMapIssue = 'demo';

        function switchBodyMapIssue(issue) {
            currentBodyMapIssue = issue;
            const demoMap = document.getElementById('demoBodyMap');
            const viewToggle = document.querySelector('.view-toggle');

            if (demoMap) demoMap.style.display = 'block';
            if (viewToggle) viewToggle.style.display = 'flex';
            showBodyView('anterior');

            document.getElementById('muscleInfoCard').style.display = 'none';
            document.querySelectorAll('.muscle.selected').forEach(m => m.classList.remove('selected'));
        }

        // Body Map - View toggle
        function showBodyView(view) {
            const title = document.getElementById('bodyMapTitle');
            const btnPosterior = document.getElementById('btnPosterior');
            const btnAnterior = document.getElementById('btnAnterior');

            if (currentBodyMapIssue === 'demo') {
                const anteriorSvg = document.getElementById('demoSvgAnterior');
                const posteriorSvg = document.getElementById('demoSvgPosterior');

                if (view === 'posterior') {
                    posteriorSvg.style.display = 'block';
                    anteriorSvg.style.display = 'none';
                    title.textContent = 'Posterior View';
                } else {
                    posteriorSvg.style.display = 'none';
                    anteriorSvg.style.display = 'block';
                    title.textContent = 'Anterior View';
                }
            }

            if (view === 'posterior') {
                btnPosterior.classList.add('active');
                btnAnterior.classList.remove('active');
            } else {
                btnPosterior.classList.remove('active');
                btnAnterior.classList.add('active');
            }

            // Hide muscle info when switching views
            document.getElementById('muscleInfoCard').style.display = 'none';
            document.querySelectorAll('.muscle.selected').forEach(m => m.classList.remove('selected'));
        }

        // Body Map - Muscle click handlers
        function initBodyMap() {
            const muscles = document.querySelectorAll('.muscle.clickable');
            muscles.forEach(muscle => {
                muscle.addEventListener('click', () => showMuscleInfo(muscle));
            });
        }

        let currentMuscleLink = null;

        function showMuscleInfo(muscle) {
            // Remove previous selection
            document.querySelectorAll('.muscle.selected').forEach(m => m.classList.remove('selected'));
            muscle.classList.add('selected');

            const name = muscle.dataset.name;
            const status = muscle.dataset.status;
            const info = muscle.dataset.info;
            const exercises = muscle.dataset.exercises;
            const link = muscle.dataset.link;

            const card = document.getElementById('muscleInfoCard');
            card.style.display = 'block';

            document.getElementById('muscleInfoName').textContent = name;

            const statusBadge = document.getElementById('muscleInfoStatus');
            statusBadge.textContent = status;
            statusBadge.className = 'muscle-status-badge ' + status;

            document.getElementById('muscleInfoText').textContent = info;

            const exerciseList = exercises.split(', ');
            document.getElementById('muscleInfoExercises').innerHTML = exerciseList
                .map(ex => `<div class="exercise-item">${escapeHtml(ex)}</div>`)
                .join('');

            // Show/hide link button
            const linkBtn = document.getElementById('muscleInfoLink');
            if (link) {
                currentMuscleLink = link;
                linkBtn.style.display = 'block';
            } else {
                currentMuscleLink = null;
                linkBtn.style.display = 'none';
            }

            // Scroll to info card on mobile
            if (window.innerWidth < 600) {
                card.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }

        function goToMuscleLink() {
            if (currentMuscleLink) {
                // Simulate clicking the tab
                if (typeof switchPanel === 'function') switchPanel(currentMuscleLink);
            }
        }

        // Initialize body map when DOM is ready
        document.addEventListener('DOMContentLoaded', initBodyMap);

        // Dry Needling - Show technique info
        function showNeedleTechnique(target) {
            // Hide all info cards first
            document.querySelectorAll('.needle-info-card').forEach(card => {
                card.classList.remove('visible');
            });

            // Show selected target's info
            const infoCard = document.getElementById('info-' + target);
            if (infoCard) {
                infoCard.classList.add('visible');
            }

            // Highlight the diagram
            document.querySelectorAll('.needle-diagram').forEach(d => {
                d.style.borderColor = 'var(--border)';
            });
            const diagram = document.getElementById('diagram-' + target);
            if (diagram) {
                diagram.style.borderColor = '#ef4444';
                diagram.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }

        // Dry Needling - Show target from table click
        function showNeedleTarget(target) {
            showNeedleTechnique(target);
        }

        // ============== HULK Protocol Functions ==============

        // Profile-specific workout types
        const PROFILE_WORKOUT_TYPES = {
            1: [
                { type: 'strength-a', label: 'Strength A' },
                { type: 'strength-b', label: 'Strength B' },
                { type: 'conditioning', label: 'Conditioning' },
                { type: 'cardio', label: 'Cardio' },
                { type: 'recovery', label: 'Recovery' }
            ],
            2: [
                { type: 'strength-upper', label: 'Strength Upper' },
                { type: 'strength-lower', label: 'Strength Lower' },
                { type: 'metcon', label: 'MetCon' },
                { type: 'conditioning', label: 'Conditioning' },
                { type: 'active', label: 'Active Recovery' }
            ]
        };

        function updateWorkoutTypeSelector() {
            const selector = document.getElementById('workoutTypeSelector');
            if (!selector) return;

            const types = PROFILE_WORKOUT_TYPES[currentProfileId] || PROFILE_WORKOUT_TYPES[1];
            selector.innerHTML = types.map((t, i) =>
                `<button class="workout-type-btn${i === 0 ? ' active' : ''}" data-type="${t.type}" onclick="selectWorkoutType(this)">${t.label}</button>`
            ).join('');

            // Reset current workout type to first option
            currentWorkoutType = types[0].type;
        }

        function updateTabVisibility() {
            const allowedTabs = PROFILE_TABS[currentProfileId] || PROFILE_TABS[1];
            // Shell-level tabs are always visible regardless of profile
            const shellTabs = ['dashboard'];

            // Hide/show tabs based on profile
            document.querySelectorAll('.tab[data-panel]').forEach(tab => {
                const panel = tab.dataset.panel;
                if (shellTabs.includes(panel)) return;
                tab.style.display = allowedTabs.includes(panel) ? '' : 'none';
            });

            // Hide/show direct nav tabs
            document.querySelectorAll('.nav-tab-direct[data-panel]').forEach(tab => {
                const panel = tab.dataset.panel;
                if (shellTabs.includes(panel)) return;
                tab.style.display = allowedTabs.includes(panel) ? '' : 'none';
            });

            // Hide dropdown groups that have no visible tabs
            document.querySelectorAll('.nav-item').forEach(item => {
                const visibleTabs = item.querySelectorAll('.tab:not([style*="display: none"])');
                item.style.display = visibleTabs.length > 0 ? '' : 'none';
            });

            // If current tab is hidden, switch to dashboard
            const activeTab = document.querySelector('.tab.active');
            if (activeTab && activeTab.style.display === 'none') {
                if (typeof switchPanel === 'function') switchPanel('dashboard');
            }

            // Update workout type selector for profile
            updateWorkoutTypeSelector();
        }

        // Training Panel
        let currentWorkoutType = 'strength-a';
        let currentExercises = [];
        let restTimerInterval = null;
        let restTimeRemaining = 0;

        function selectWorkoutType(btn) {
            document.querySelectorAll('.workout-type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentWorkoutType = btn.dataset.type;
        }

        function addExercise() {
            const name = document.getElementById('exerciseName').value.trim();
            const sets = document.getElementById('exerciseSets').value;
            const reps = document.getElementById('exerciseReps').value;
            const weight = document.getElementById('exerciseWeight').value;
            const rpe = document.getElementById('exerciseRpe').value;

            if (!name) {
                showToast('Enter exercise name', 'error');
                return;
            }

            currentExercises.push({ name, sets, reps, weight, rpe });
            renderCurrentExercises();

            // Clear inputs
            document.getElementById('exerciseName').value = '';
            document.getElementById('exerciseSets').value = '';
            document.getElementById('exerciseReps').value = '';
            document.getElementById('exerciseWeight').value = '';
            document.getElementById('exerciseRpe').value = '';
            document.getElementById('exerciseName').focus();
        }

        function renderCurrentExercises() {
            const container = document.getElementById('currentExerciseList');
            if (currentExercises.length === 0) {
                container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No exercises added yet</p>';
                return;
            }
            container.innerHTML = currentExercises.map((ex, i) => `
                <div class="exercise-item-row">
                    <div>
                        <div class="name">${escapeHtml(ex.name)}</div>
                        <div class="details">${ex.sets || '-'} sets × ${ex.reps || '-'} reps @ ${ex.weight || '-'} ${ex.rpe ? '(RPE ' + ex.rpe + ')' : ''}</div>
                    </div>
                    <button class="delete-btn" onclick="removeExercise(${i})" aria-label="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m2 0v14a2 2 0 01-2 2H8a2 2 0 01-2-2V6h12z"/></svg></button>
                </div>
            `).join('');
        }

        function removeExercise(index) {
            currentExercises.splice(index, 1);
            renderCurrentExercises();
        }

        async function saveWorkout() {
            if (currentExercises.length === 0) {
                showToast('Add at least one exercise', 'error');
                return;
            }

            const rpe = document.getElementById('workoutRpe').value;
            const notes = document.getElementById('workoutNotes').value;

            try {
                const res = await fetch('/api/workouts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type: currentWorkoutType,
                        rpe: rpe ? parseInt(rpe) : null,
                        notes: notes || null,
                        exercises: currentExercises
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Workout saved!', 'success');
                    currentExercises = [];
                    renderCurrentExercises();
                    document.getElementById('workoutRpe').value = '';
                    document.getElementById('workoutNotes').value = '';
                    loadRecentWorkouts();
                    loadHulkStreaks();
                } else {
                    showToast('Failed to save workout', 'error');
                }
            } catch (e) {
                showToast('Error saving workout', 'error');
            }
        }

        async function loadRecentWorkouts() {
            try {
                const res = await fetch('/api/workouts?limit=10');
                const workouts = await res.json();
                const container = document.getElementById('recentWorkouts');

                if (workouts.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No workouts logged yet</p>';
                    return;
                }

                container.innerHTML = workouts.map(w => `
                    <div class="workout-history-item" onclick="showWorkoutDetail(${w.id})" style="cursor: pointer;">
                        <div class="header">
                            <span class="type">${escapeHtml(w.type.replace('-', ' '))}</span>
                            <span class="date">${new Date(w.date + 'T12:00:00').toLocaleDateString()}</span>
                        </div>
                        <div class="stats">${w.duration ? w.duration + ' min • ' : ''}${w.total_sets || 0} sets ${w.rpe ? '• RPE ' + w.rpe : ''}</div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Failed to load workouts:', e);
            }
        }

        async function showWorkoutDetail(workoutId) {
            try {
                const res = await fetch(`/api/workouts/${workoutId}`);
                const workout = await res.json();

                if (workout.error) {
                    showToast('Workout not found', 'error');
                    return;
                }

                const workoutType = workout.type.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                document.getElementById('workoutModalTitle').textContent = workoutType;

                // Format notes with markdown-like styling
                let notesHtml = '';
                if (workout.notes) {
                    notesHtml = workout.notes
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\\n- /g, '<br>• ')
                        .replace(/\\n/g, '<br>');
                }

                const content = `
                    <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; padding: 0.75rem; background: var(--bg); border-radius: 8px;">
                        <div><span style="color: var(--text-dim);">Date:</span> <strong>${new Date(workout.date + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</strong></div>
                        ${workout.duration ? `<div><span style="color: var(--text-dim);">Duration:</span> <strong>${workout.duration} min</strong></div>` : ''}
                        ${workout.rpe ? `<div><span style="color: var(--text-dim);">RPE:</span> <strong>${workout.rpe}/10</strong></div>` : ''}
                        ${workout.total_sets ? `<div><span style="color: var(--text-dim);">Sets:</span> <strong>${workout.total_sets}</strong></div>` : ''}
                    </div>

                    ${workout.exercises && workout.exercises.length > 0 ? `
                        <div style="margin-bottom: 1rem;">
                            <h4 style="color: var(--text); margin-bottom: 0.5rem;">Exercises</h4>
                            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                ${workout.exercises.map(ex => `
                                    <div style="padding: 0.75rem; background: var(--bg); border-radius: 8px; border-left: 3px solid var(--accent);">
                                        <div style="font-weight: 600; color: var(--text);">${escapeHtml(ex.name)}</div>
                                        <div style="font-size: 0.85rem; color: var(--text-dim);">
                                            ${ex.sets ? ex.sets + ' sets' : ''} ${ex.reps ? '× ' + ex.reps : ''} ${ex.weight ? '@ ' + ex.weight : ''}
                                            ${ex.notes ? '<br><em>' + escapeHtml(ex.notes) + '</em>' : ''}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    ${notesHtml ? `
                        <div>
                            <h4 style="color: var(--text); margin-bottom: 0.5rem;">Notes</h4>
                            <div style="padding: 0.75rem; background: var(--bg); border-radius: 8px; color: var(--text-dim); font-size: 0.9rem; line-height: 1.6;">
                                ${notesHtml}
                            </div>
                        </div>
                    ` : ''}
                `;

                document.getElementById('workoutModalContent').innerHTML = content;
                document.getElementById('workoutModal').classList.add('show');
            } catch (e) {
                console.error('Error loading workout:', e);
                showToast('Error loading workout details', 'error');
            }
        }

        function closeWorkoutModal() {
            document.getElementById('workoutModal').classList.remove('show');
        }

        // Weekly Training Detail Modal
        function showWeeklyTrainingDetail() {
            document.getElementById('weeklyTrainingModal').classList.add('show');
        }

        function closeWeeklyTrainingModal() {
            document.getElementById('weeklyTrainingModal').classList.remove('show');
        }

        function showBreathingProtocolDetail() {
            document.getElementById('breathingProtocolModal').classList.add('show');
        }

        function closeBreathingProtocolModal() {
            document.getElementById('breathingProtocolModal').classList.remove('show');
        }

        // Rest Timer
        function setRestTimer(seconds) {
            stopRestTimer();
            restTimeRemaining = seconds;
            updateRestTimerDisplay();
            restTimerInterval = setInterval(() => {
                restTimeRemaining--;
                updateRestTimerDisplay();
                if (restTimeRemaining <= 0) {
                    stopRestTimer();
                    // Play sound or notification
                    try { new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==').play(); } catch(e) {}
                    showToast('Rest complete!', 'success');
                }
            }, 1000);
        }

        function stopRestTimer() {
            if (restTimerInterval) {
                clearInterval(restTimerInterval);
                restTimerInterval = null;
            }
            restTimeRemaining = 0;
            updateRestTimerDisplay();
        }

        function updateRestTimerDisplay() {
            const mins = Math.floor(restTimeRemaining / 60);
            const secs = restTimeRemaining % 60;
            document.getElementById('restTimerDisplay').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
        }

        // Recovery Panel
        function initRecoverySliders() {
            const sliders = ['SleepQuality', 'Soreness', 'Energy', 'Stress', 'Motivation'];
            sliders.forEach(name => {
                const slider = document.getElementById('recovery' + name);
                const display = document.getElementById(name.toLowerCase() + 'Val');
                if (slider && display) {
                    slider.addEventListener('input', () => {
                        display.textContent = slider.value;
                    });
                }
            });
        }

        async function saveRecovery() {
            const data = {
                sleep_hours: parseFloat(document.getElementById('recoverySleepHours').value) || null,
                sleep_quality: parseInt(document.getElementById('recoverySleepQuality').value),
                soreness: parseInt(document.getElementById('recoverySoreness').value),
                energy: parseInt(document.getElementById('recoveryEnergy').value),
                stress: parseInt(document.getElementById('recoveryStress').value),
                motivation: parseInt(document.getElementById('recoveryMotivation').value),
                notes: document.getElementById('recoveryNotes').value || null
            };

            try {
                const res = await fetch('/api/recovery', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.success) {
                    showToast('Recovery logged!', 'success');
                    loadReadiness();
                    loadRecoveryHistory();
                    loadHulkStreaks();
                } else {
                    showToast('Failed to log recovery', 'error');
                }
            } catch (e) {
                showToast('Error logging recovery', 'error');
            }
        }

        async function loadReadiness() {
            try {
                const res = await fetch('/api/readiness');
                const data = await res.json();
                const container = document.getElementById('readinessDisplay');

                if (data.score === null) {
                    container.className = 'readiness-score';
                    container.innerHTML = `
                        <div class="score">--</div>
                        <div class="status">${data.message || 'Log recovery to see readiness'}</div>
                    `;
                } else {
                    container.className = 'readiness-score ' + data.status;
                    container.innerHTML = `
                        <div class="score">${data.score}</div>
                        <div class="status">${data.message}</div>
                    `;
                }
            } catch (e) {
                console.error('Failed to load readiness:', e);
            }
        }

        async function loadRecoveryHistory() {
            try {
                const res = await fetch('/api/recovery?limit=7');
                const history = await res.json();
                const container = document.getElementById('recoveryHistory');

                if (history.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No recovery logs yet</p>';
                    return;
                }

                container.innerHTML = history.map(r => {
                    const avg = Math.round(((r.sleep_quality || 5) + (r.energy || 5) + (11 - (r.soreness || 5)) + (11 - (r.stress || 5)) + (r.motivation || 5)) / 5 * 10);
                    return `
                        <div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
                            <span>${new Date(r.date + 'T12:00:00').toLocaleDateString()}</span>
                            <span style="color: var(--text-dim);">${r.sleep_hours || '-'}h sleep</span>
                            <span style="color: ${avg >= 60 ? 'var(--green)' : avg >= 40 ? 'var(--orange)' : 'var(--pink)'};">${avg}%</span>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('Failed to load recovery history:', e);
            }
        }

        // Nutrition Panel - defaults, overridden by profile goals from API
        let MACRO_TARGETS = { calories: 2500, protein: 180, carbs: 250, fat: 80 };

        async function logMeal() {
            const name = document.getElementById('mealName').value.trim();
            if (!name) {
                showToast('Enter meal name', 'error');
                return;
            }

            const data = {
                meal_name: name,
                calories: parseInt(document.getElementById('mealCalories').value) || null,
                protein: parseInt(document.getElementById('mealProtein').value) || null,
                carbs: parseInt(document.getElementById('mealCarbs').value) || null,
                fat: parseInt(document.getElementById('mealFat').value) || null
            };

            try {
                const res = await fetch('/api/meals', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.success) {
                    showToast('Meal logged!', 'success');
                    // Clear form
                    document.getElementById('mealName').value = '';
                    document.getElementById('mealCalories').value = '';
                    document.getElementById('mealProtein').value = '';
                    document.getElementById('mealCarbs').value = '';
                    document.getElementById('mealFat').value = '';
                    loadTodayMeals();
                    loadHulkStreaks();
                } else {
                    showToast('Failed to log meal', 'error');
                }
            } catch (e) {
                showToast('Error logging meal', 'error');
            }
        }

        async function loadTodayMeals() {
            try {
                const res = await fetch('/api/meals/today');
                const data = await res.json();
                const meals = data.meals || [];
                const totals = data.totals || {};

                // Use profile goals from API if available
                if (data.goals) {
                    MACRO_TARGETS = {
                        calories: data.goals.calories || MACRO_TARGETS.calories,
                        protein: data.goals.protein || MACRO_TARGETS.protein,
                        carbs: data.goals.carbs || MACRO_TARGETS.carbs,
                        fat: data.goals.fat || MACRO_TARGETS.fat,
                    };
                }

                // Update macro rings
                updateMacroRing('calories', totals.calories || 0, MACRO_TARGETS.calories);
                updateMacroRing('protein', totals.protein || 0, MACRO_TARGETS.protein);
                updateMacroRing('carbs', totals.carbs || 0, MACRO_TARGETS.carbs);
                updateMacroRing('fat', totals.fat || 0, MACRO_TARGETS.fat);

                // Update values
                document.getElementById('caloriesValue').textContent = totals.calories || 0;
                document.getElementById('proteinValue').textContent = (totals.protein || 0) + 'g';
                document.getElementById('carbsValue').textContent = (totals.carbs || 0) + 'g';
                document.getElementById('fatValue').textContent = (totals.fat || 0) + 'g';

                // Render meal list
                const container = document.getElementById('todayMeals');
                if (meals.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No meals logged today</p>';
                    return;
                }

                container.innerHTML = meals.map(m => `
                    <div class="meal-item">
                        <div class="name">${escapeHtml(m.meal_name)}</div>
                        <div class="macros">
                            <span class="cal">${m.calories || 0} kcal</span>
                            <span class="p">P: ${m.protein || 0}g</span>
                            <span class="c">C: ${m.carbs || 0}g</span>
                            <span class="f">F: ${m.fat || 0}g</span>
                        </div>
                        <button class="delete-btn" onclick="deleteMeal(${m.id})" aria-label="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m2 0v14a2 2 0 01-2 2H8a2 2 0 01-2-2V6h12z"/></svg></button>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Failed to load meals:', e);
            }
        }

        function updateMacroRing(type, current, target) {
            const ring = document.getElementById(type + 'Ring');
            if (!ring) return;
            const pct = Math.min(100, (current / target) * 100);
            const offset = 100 - pct;
            ring.style.strokeDashoffset = offset;
        }

        async function deleteMeal(mealId) {
            try {
                await fetch(`/api/meals/${mealId}`, { method: 'DELETE' });
                loadTodayMeals();
            } catch (e) {
                console.error('Failed to delete meal:', e);
            }
        }

        // Progress Panel
        async function loadHulkStreaks() {
            try {
                const res = await fetch('/api/hulk-streaks');
                const data = await res.json();
                document.getElementById('workoutStreak').textContent = data.workout || 0;
                document.getElementById('recoveryStreak').textContent = data.recovery || 0;
                document.getElementById('nutritionStreak').textContent = data.nutrition || 0;
            } catch (e) {
                console.error('Failed to load streaks:', e);
            }
        }

        async function loadVolumeChart() {
            try {
                const res = await fetch('/api/volume?days=30');
                const data = await res.json();
                const container = document.getElementById('volumeChart');
                const dailyVolume = data.daily_volume || {};

                document.getElementById('totalSetsValue').textContent = data.total_sets || 0;
                document.getElementById('avgSetsValue').textContent = data.avg_sets_per_week || 0;

                // Create 30 bars
                const bars = [];
                for (let i = 29; i >= 0; i--) {
                    const d = new Date();
                    d.setDate(d.getDate() - i);
                    const key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
                    bars.push(dailyVolume[key] || 0);
                }

                const maxVal = Math.max(...bars, 1);
                container.innerHTML = bars.map(v => `<div class="bar" style="height: ${Math.max((v / maxVal) * 100, 4)}px;"></div>`).join('');
            } catch (e) {
                console.error('Failed to load volume:', e);
            }
        }

        async function loadPRs() {
            try {
                const res = await fetch('/api/prs');
                const prs = await res.json();
                const container = document.getElementById('prList');

                if (prs.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No PRs recorded yet</p>';
                    return;
                }

                container.innerHTML = prs.map(pr => `
                    <div class="pr-item">
                        <div>
                            <div class="exercise">${escapeHtml(pr.exercise)}</div>
                            <div class="date">${new Date(pr.date + 'T12:00:00').toLocaleDateString()}</div>
                        </div>
                        <div class="record">${pr.weight} × ${pr.reps} (e1RM: ${Math.round(pr.best_1rm)})</div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Failed to load PRs:', e);
            }
        }

        async function loadGoals() {
            try {
                const res = await fetch('/api/goals');
                const goals = await res.json();
                const container = document.getElementById('goalsList');

                if (goals.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No goals set</p>';
                    return;
                }

                container.innerHTML = goals.map(g => {
                    const pct = g.target > 0 ? Math.min(100, Math.round((g.current || 0) / g.target * 100)) : 0;
                    return `
                        <div class="goal-card">
                            <div class="goal-header">
                                <span class="goal-name">${escapeHtml(g.name)}</span>
                                <span class="goal-category">${escapeHtml(g.category)}</span>
                            </div>
                            <div class="goal-progress">
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${pct}%;"></div>
                                </div>
                                <div class="values">${g.current || 0} / ${g.target} ${g.unit}</div>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('Failed to load goals:', e);
            }
        }

        async function loadBodyWeightChart() {
            try {
                const res = await fetch('/api/body?limit=30');
                const logs = await res.json();
                const container = document.getElementById('weightChart');

                if (logs.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No weight data</p>';
                    return;
                }

                const weights = logs.filter(l => l.weight).map(l => l.weight).reverse();
                if (weights.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No weight data</p>';
                    return;
                }

                const minW = Math.min(...weights) - 5;
                const maxW = Math.max(...weights) + 5;
                const range = maxW - minW || 1;

                container.innerHTML = weights.map(w => `<div class="bar" style="height: ${((w - minW) / range) * 100}px;"></div>`).join('');
            } catch (e) {
                console.error('Failed to load weight chart:', e);
            }
        }

        function showAddGoalForm() {
            const name = prompt('Goal name:');
            if (!name) return;
            const category = prompt('Category (strength, body, nutrition, habit):') || 'general';
            const target = parseFloat(prompt('Target value:'));
            if (isNaN(target)) return;
            const unit = prompt('Unit (lbs, kg, days, etc):') || '';

            fetch('/api/goals', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, category, target, unit, current: 0 })
            }).then(() => {
                showToast('Goal created!', 'success');
                loadGoals();
            }).catch(() => {
                showToast('Failed to create goal', 'error');
            });
        }

        // Load HULK data
        async function loadHulkData() {
            await Promise.all([
                loadRecentWorkouts(),
                loadReadiness(),
                loadRecoveryHistory(),
                loadTodayMeals(),
                loadHulkStreaks(),
                loadVolumeChart(),
                loadPRs(),
                loadGoals(),
                loadBodyWeightChart()
            ]);
        }

        // Initialize
        // ============== Protocol Widget ==============
        let _protocolCache = {};

        async function loadProtocolWidget() {
            try {
                const res = await fetch('/api/protocols');
                const protocols = await res.json();
                const widget = document.getElementById('protocolWidget');
                const list = document.getElementById('protocolList');
                if (!widget || !list) return;

                if (!protocols || protocols.length === 0) {
                    widget.style.display = 'none';
                    return;
                }

                // Remember which protocol detail was open before re-render
                const _openProtoId = document.querySelector('.protocol-detail.open')?.id?.replace('protocolDetail-', '');

                // Cache protocols for detail rendering
                _protocolCache = {};
                protocols.forEach(p => { _protocolCache[p.id] = p; });

                widget.style.display = '';
                list.innerHTML = protocols.map(p => {
                    const phaseName = p.phase_name || 'Active';
                    const phaseDay = p.phase_day || 0;
                    const phaseDuration = p.phase_duration || 1;
                    const elapsed = p.elapsed_days || 0;
                    const total = p.total_days || 1;
                    const isComplete = p.status === 'completed';
                    const isPaused = p.status === 'paused';
                    const cycleComplete = p.cycle_complete || false;
                    const daysPast = p.days_past || 0;

                    let phaseText, daysText, overallPct, statusClass, statusLabel;

                    if (isComplete) {
                        overallPct = 100;
                        phaseText = 'All phases complete — ' + total + ' days';
                        daysText = '<span>' + total + ' days total</span><span>Completed</span>';
                        statusClass = 'completed';
                        statusLabel = 'completed';
                    } else if (isPaused) {
                        overallPct = 0;
                        phaseText = 'Not started';
                        daysText = '<span>Waiting to begin</span>';
                        statusClass = 'paused';
                        statusLabel = 'paused';
                    } else if (cycleComplete) {
                        overallPct = 100;
                        phaseText = 'Cycle done — ' + daysPast + ' days past ' + total + '-day cycle';
                        daysText = '<span>Started ' + escapeHtml(p.started_at || '') + '</span><span>Day ' + elapsed + ' overall</span>';
                        statusClass = 'cycle-done';
                        statusLabel = 'cycle done';
                    } else {
                        overallPct = Math.min(100, Math.round((elapsed / total) * 100));
                        const remaining = Math.max(0, total - elapsed);
                        phaseText = escapeHtml(phaseName) + ' — Day ' + phaseDay + '/' + phaseDuration;
                        daysText = '<span>Day ' + elapsed + ' of ' + total + '</span><span>' + remaining + ' days remaining</span>';
                        statusClass = 'active';
                        statusLabel = 'active';
                    }

                    return '<div class="protocol-item" onclick="toggleProtocolDetail(' + p.id + ')">' +
                        '<div class="protocol-header">' +
                        '<span class="protocol-name">' + escapeHtml(p.name) + '</span>' +
                        '<span class="protocol-status ' + statusClass + '">' + escapeHtml(statusLabel) + '</span>' +
                        '</div>' +
                        '<div class="protocol-phase">' + phaseText + '</div>' +
                        '<div class="protocol-progress"><div class="protocol-progress-fill" style="width:' + overallPct + '%;"></div></div>' +
                        '<div class="protocol-days">' + daysText + '</div>' +
                        '<div class="protocol-detail" id="protocolDetail-' + p.id + '"></div>' +
                        '</div>';
                }).join('');

                // Restore open protocol detail if it was open before re-render
                if (_openProtoId) {
                    toggleProtocolDetail(parseInt(_openProtoId));
                }
            } catch (e) {
                console.error('Failed to load protocols:', e);
            }
        }

        function toggleProtocolDetail(id) {
            const detail = document.getElementById('protocolDetail-' + id);
            if (!detail) return;

            // If already open, collapse
            if (detail.classList.contains('open')) {
                detail.classList.remove('open');
                return;
            }

            // Collapse any other open detail
            document.querySelectorAll('.protocol-detail.open').forEach(el => el.classList.remove('open'));

            const p = _protocolCache[id];
            if (!p) return;

            let phases = [];
            try { phases = p.phases_parsed || (p.phases ? JSON.parse(p.phases) : []); } catch (e) {}

            const isComplete = p.status === 'completed';
            const isPaused = p.status === 'paused';
            const cycleComplete = p.cycle_complete || false;
            const computedPhase = p.computed_phase || 0;

            // Phase timeline
            let timeline = '';
            if (phases.length > 0) {
                timeline = '<div class="phase-timeline">' + phases.map((ph, i) => {
                    let cls = '';
                    if (isComplete || (cycleComplete && i <= computedPhase)) cls = 'done';
                    else if (!isPaused && i < computedPhase) cls = 'done';
                    else if (!isPaused && i === computedPhase) cls = 'active';
                    const dot = cls === 'done' ? '&#10003;' : (i + 1);
                    return '<div class="phase-step ' + cls + '">' +
                        '<div class="phase-step-dot">' + dot + '</div>' +
                        '<div class="phase-step-line"></div>' +
                        '<div class="phase-step-label">' + escapeHtml(ph.name || ('Phase ' + (i + 1))) + '</div>' +
                        '</div>';
                }).join('') + '</div>';
            }

            // Description
            let desc = p.description ? '<div class="protocol-description">' + escapeHtml(p.description) + '</div>' : '';

            // Phase list
            let phaseList = '';
            if (phases.length > 0) {
                phaseList = '<div class="phase-list">' + phases.map((ph, i) => {
                    let cls = '';
                    let icon = '<span style="color:var(--text-dim);">' + (i + 1) + '</span>';
                    if (isComplete || (cycleComplete && i <= computedPhase)) {
                        cls = 'done';
                        icon = '<span style="color:var(--accent);">&#10003;</span>';
                    } else if (!isPaused && i < computedPhase) {
                        cls = 'done';
                        icon = '<span style="color:var(--accent);">&#10003;</span>';
                    } else if (!isPaused && i === computedPhase) {
                        cls = 'active';
                        icon = '<span style="color:var(--cyan);">&#9654;</span>';
                    }
                    const dur = ph.duration_days ? ph.duration_days + 'd' : '';
                    const phDesc = ph.description ? '<br><span style="font-size:0.75rem;opacity:0.7;">' + escapeHtml(ph.description) + '</span>' : '';
                    return '<div class="phase-list-item ' + cls + '">' +
                        '<div class="phase-list-icon">' + icon + '</div>' +
                        '<div class="phase-list-text">' + escapeHtml(ph.name || ('Phase ' + (i + 1))) + phDesc + '</div>' +
                        '<div class="phase-list-duration">' + dur + '</div>' +
                        '</div>';
                }).join('') + '</div>';
            }

            // Action buttons
            let actions = '<div class="protocol-actions">';
            if (isComplete) {
                actions += '<button class="proto-btn proto-btn-start" onclick="event.stopPropagation(); protocolAction(' + id + ',\'restart\')">Restart</button>';
            } else if (isPaused) {
                actions += '<button class="proto-btn proto-btn-start" onclick="event.stopPropagation(); protocolAction(' + id + ',\'start\')">Start</button>';
            } else if (cycleComplete) {
                actions += '<button class="proto-btn" onclick="event.stopPropagation(); protocolAction(' + id + ',\'restart\')">Restart</button>';
                actions += '<button class="proto-btn proto-btn-done" onclick="event.stopPropagation(); protocolAction(' + id + ',\'complete\')">Done</button>';
            } else {
                actions += '<button class="proto-btn proto-btn-pause" onclick="event.stopPropagation(); protocolAction(' + id + ',\'pause\')">Pause</button>';
            }
            actions += '</div>';

            detail.innerHTML = '<div class="protocol-detail-inner">' + timeline + desc + phaseList + actions + '</div>';
            detail.classList.add('open');
        }

        async function protocolAction(id, action) {
            const today = new Date().toISOString().slice(0, 10);
            let body = {};
            if (action === 'start' || action === 'restart') {
                body = { status: 'active', started_at: today };
            } else if (action === 'pause') {
                body = { status: 'paused' };
            } else if (action === 'complete') {
                body = { status: 'completed' };
            }
            try {
                await fetch('/api/protocols/' + id, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                loadProtocolWidget();
            } catch (e) {
                console.error('Protocol action failed:', e);
            }
        }

        // ============== Smart Gap Suggestions ==============

        function renderGapSuggestions(gapsData) {
            const container = document.getElementById('gapSuggestions');
            if (!container) return;
            const widget = document.getElementById('suggestionsWidget');

            if (!gapsData || !gapsData.categories || gapsData.categories.length === 0) {
                if (widget) widget.style.display = 'none';
                return;
            }

            const priorityWeight = { critical: 4, high: 3, medium: 2, low: 1 };
            const scored = [];

            for (const cat of gapsData.categories) {
                if (cat.gaps.length === 0) continue;
                const weight = priorityWeight[cat.priority] || 1;
                const score = weight * (100 - cat.coverage) * cat.gaps.length;
                for (const gap of cat.gaps.slice(0, 2)) {
                    const topicName = typeof gap === 'object' ? gap.name : gap;
                    scored.push({ topic: topicName, category: cat.name, priority: cat.priority, score });
                }
            }

            scored.sort((a, b) => b.score - a.score);
            const top = scored.slice(0, 5);

            if (top.length === 0) {
                if (widget) widget.style.display = 'none';
                return;
            }

            if (widget) widget.style.display = '';
            container.innerHTML = top.map(s =>
                '<div class="suggestion-item" onclick="showHealthGapPrompt(\'' + escapeHtml(s.topic) + '\', \'' + escapeHtml(s.category) + '\')">' +
                '<span class="suggestion-topic">' + escapeHtml(s.topic) + '</span>' +
                '<span class="suggestion-category">' + escapeHtml(s.category) + '</span>' +
                '</div>'
            ).join('');
        }

        // ============== Reminders ==============

        let _remindersDismissed = new Set();

        async function checkReminders() {
            try {
                const res = await fetch('/api/reminders/due');
                const due = await res.json();
                const banner = document.getElementById('reminderBanner');
                if (!banner) return;

                const active = due.filter(r => !_remindersDismissed.has(r.id));
                if (active.length === 0) {
                    banner.style.display = 'none';
                    return;
                }

                banner.style.display = '';
                banner.innerHTML = active.map(r =>
                    '<div class="reminder-banner">' +
                    '<span class="reminder-banner-icon">&#9200;</span>' +
                    '<div class="reminder-banner-text">' +
                    '<strong>' + escapeHtml(r.title) + '</strong>' +
                    (r.description ? '<br><span style="font-size:0.8rem;color:var(--text-dim);">' + escapeHtml(r.description) + '</span>' : '') +
                    '</div>' +
                    '<button class="reminder-banner-dismiss" onclick="dismissReminder(' + r.id + ')" title="Dismiss">&times;</button>' +
                    '</div>'
                ).join('');

                // Browser Notification API (if permitted)
                if ('Notification' in window && Notification.permission === 'granted') {
                    active.forEach(r => {
                        const key = 'reminder-notified-' + r.id + '-' + new Date().toDateString();
                        if (!sessionStorage.getItem(key)) {
                            new Notification('SAPA Reminder', { body: r.title, icon: '/icon-192.svg' });
                            sessionStorage.setItem(key, '1');
                        }
                    });
                }
            } catch (e) {
                console.error('Failed to check reminders:', e);
            }
        }

        function dismissReminder(id) {
            _remindersDismissed.add(id);
            checkReminders();
        }

        // Request notification permission on first interaction
        document.addEventListener('click', function requestNotifPermission() {
            if ('Notification' in window && Notification.permission === 'default') {
                Notification.requestPermission();
            }
            document.removeEventListener('click', requestNotifPermission);
        }, { once: true });

        // ============== Family Activity Feed ==============

        let _familyFeedLoaded = false;

        async function loadFamilyFeed() {
            try {
                const res = await fetch('/api/family-feed?limit=30');
                const items = await res.json();
                const container = document.getElementById('familyFeedList');
                if (!container) return;
                _familyFeedLoaded = true;

                if (!items || items.length === 0) {
                    container.innerHTML = '<div style="color: var(--text-dim); font-size: 0.85rem; text-align: center; padding: 2rem 0;">No activity yet</div>';
                    return;
                }

                const profileColors = { 1: '1', 2: '2', 3: '3', 4: '4', 0: 'family' };

                // Collapse consecutive entries with the same topic into one row
                const collapsed = [];
                for (const item of items) {
                    const prev = collapsed[collapsed.length - 1];
                    if (prev && prev.topic === item.topic) {
                        // Add this profile to the existing group
                        if (!prev._profiles.some(p => p.id === item.profile_id)) {
                            prev._profiles.push({ id: item.profile_id, name: item.profile_name });
                        }
                    } else {
                        item._profiles = [{ id: item.profile_id, name: item.profile_name }];
                        collapsed.push(item);
                    }
                }

                container.innerHTML = collapsed.map(item => {
                    const time = item.created_at ? relativeTime(item.created_at) : '';
                    const catBadge = item.category === 'homestead'
                        ? '<span class="category-badge homestead" style="font-size:0.65rem;">Homestead</span>'
                        : '<span class="category-badge health" style="font-size:0.65rem;">Health</span>';

                    // Render stacked avatars for all profiles in this group
                    const avatars = item._profiles.map(p => {
                        const colorClass = 'profile-color-' + (profileColors[p.id] || 'family');
                        const initial = (p.name || '?')[0].toUpperCase();
                        return '<div class="family-feed-avatar ' + colorClass + '">' + initial + '</div>';
                    }).join('');

                    const names = item._profiles.map(p => escapeHtml(p.name || 'Unknown')).join(', ');

                    return '<div class="family-feed-item">' +
                        '<div class="family-feed-avatars">' + avatars + '</div>' +
                        '<div class="family-feed-content">' +
                        '<span class="family-feed-name">' + names + '</span> ' +
                        catBadge +
                        '<div class="family-feed-topic">' + escapeHtml(item.topic || 'Untitled') + '</div>' +
                        '<div class="family-feed-time">' + escapeHtml(time) + '</div>' +
                        '</div></div>';
                }).join('');
            } catch (e) {
                console.error('Failed to load family feed:', e);
            }
        }

        function relativeTime(dateStr) {
            const d = new Date(dateStr + (dateStr.includes('Z') ? '' : 'Z'));
            const now = new Date();
            const diff = Math.floor((now - d) / 1000);
            if (diff < 60) return 'just now';
            if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
            if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
            if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }

        async function init() {
            await loadProfiles();
            updateTabVisibility();
            await loadDashboard();
            await loadHulkData();
            initRecoverySliders();
            renderCurrentExercises();
            connectWebSocket();
        }
        init();

        // Refresh every 30 seconds
        setInterval(loadDashboard, 30000);
