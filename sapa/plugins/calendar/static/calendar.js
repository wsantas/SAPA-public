
        // Calendar plugin
        let _calView = 'today';
        let _calAutoRefresh = null;

        function formatCalTime(isoStr, allDay) {
            if (allDay) return 'All day';
            const d = new Date(isoStr);
            return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
        }

        function formatCalRange(start, end, allDay) {
            if (allDay) return 'All day';
            return formatCalTime(start) + ' \u2013 ' + formatCalTime(end);
        }

        function isEventNow(start, end, allDay) {
            if (allDay) return false;
            const now = new Date();
            return new Date(start) <= now && now < new Date(end);
        }

        function getNextEvent(events) {
            const now = new Date();
            for (const e of events) {
                if (e.all_day) continue;
                if (new Date(e.start) > now) return e;
            }
            return null;
        }

        function timeUntil(isoStr) {
            const diff = new Date(isoStr) - new Date();
            if (diff <= 0) return 'now';
            const mins = Math.floor(diff / 60000);
            if (mins < 60) return mins + 'm';
            const hrs = Math.floor(mins / 60);
            const rm = mins % 60;
            return hrs + 'h ' + (rm > 0 ? rm + 'm' : '');
        }

        function renderCalEvent(e) {
            const nowClass = isEventNow(e.start, e.end, e.all_day) ? ' now' : '';
            const allDayClass = e.all_day ? ' all-day' : '';
            const timeStr = e.all_day ? 'All day' : formatCalTime(e.start);
            const loc = e.location ? `<div class="cal-event-location">${escapeHtml(e.location)}</div>` : '';
            const desc = e.description ? `<div class="cal-event-desc">${escapeHtml(e.description)}</div>` : '';
            return `<div class="cal-event${nowClass}${allDayClass}">
                <div class="cal-event-time">${timeStr}</div>
                <div class="cal-event-body">
                    <div class="cal-event-title">${escapeHtml(e.summary)}</div>
                    ${loc}${desc}
                </div>
            </div>`;
        }

        async function loadCalendar() {
            const container = document.getElementById('calEvents');
            if (!container) return;
            container.innerHTML = '<div class="cal-loading">Loading events...</div>';

            try {
                const res = await fetch('/api/calendar/events');
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const events = await res.json();

                const dateLabel = document.getElementById('calDateLabel');
                if (dateLabel) {
                    const today = new Date();
                    dateLabel.textContent = today.toLocaleDateString('en-US', {
                        weekday: 'long', month: 'long', day: 'numeric'
                    });
                }

                if (events.length === 0) {
                    container.innerHTML = '<div class="cal-empty"><div class="cal-empty-icon">&#128197;</div><p>No events today</p></div>';
                    document.getElementById('calNextUp').style.display = 'none';
                    return;
                }

                // Next-up banner
                const nextUp = document.getElementById('calNextUp');
                const next = getNextEvent(events);
                if (next) {
                    nextUp.innerHTML = 'Next up: <strong>' + escapeHtml(next.summary) + '</strong> in ' + timeUntil(next.start);
                    nextUp.style.display = 'block';
                } else {
                    nextUp.style.display = 'none';
                }

                container.innerHTML = '<div class="cal-timeline">' +
                    events.map(renderCalEvent).join('') +
                    '</div>';
            } catch (e) {
                console.error('Calendar load failed:', e);
                container.innerHTML = '<div class="cal-error"><div class="cal-error-icon">&#9888;&#65039;</div><p>Failed to load calendar</p></div>';
            }
        }

        async function loadCalendarWeek() {
            const container = document.getElementById('calEvents');
            if (!container) return;
            container.innerHTML = '<div class="cal-loading">Loading week...</div>';

            try {
                const res = await fetch('/api/calendar/events/week');
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const events = await res.json();

                const dateLabel = document.getElementById('calDateLabel');
                if (dateLabel) {
                    dateLabel.textContent = 'This Week';
                }
                document.getElementById('calNextUp').style.display = 'none';

                if (events.length === 0) {
                    container.innerHTML = '<div class="cal-empty"><div class="cal-empty-icon">&#128197;</div><p>No events this week</p></div>';
                    return;
                }

                // Group by day
                const days = {};
                const todayStr = new Date().toDateString();
                for (const e of events) {
                    const dayKey = e.all_day
                        ? new Date(e.start + 'T00:00:00').toDateString()
                        : new Date(e.start).toDateString();
                    if (!days[dayKey]) days[dayKey] = [];
                    days[dayKey].push(e);
                }

                let html = '';
                const dayKeys = Object.keys(days).sort((a, b) => new Date(a) - new Date(b));
                for (const dayKey of dayKeys) {
                    const d = new Date(dayKey);
                    const isToday = dayKey === todayStr;
                    const label = d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
                    html += `<div class="cal-day-group">
                        <div class="cal-day-header${isToday ? ' today' : ''}">${label}${isToday ? ' (Today)' : ''}</div>
                        <div class="cal-timeline">${days[dayKey].map(renderCalEvent).join('')}</div>
                    </div>`;
                }

                container.innerHTML = html;
            } catch (e) {
                console.error('Calendar week load failed:', e);
                container.innerHTML = '<div class="cal-error"><div class="cal-error-icon">&#9888;&#65039;</div><p>Failed to load calendar</p></div>';
            }
        }

        function switchCalView(view) {
            _calView = view;
            document.querySelectorAll('.cal-toggle').forEach(b => b.classList.remove('active'));
            document.querySelector(`.cal-toggle[onclick="switchCalView('${view}')"]`)?.classList.add('active');
            if (view === 'today') loadCalendar();
            else loadCalendarWeek();
        }

        async function refreshCalendar() {
            try {
                await fetch('/api/calendar/refresh', { method: 'POST' });
                if (_calView === 'today') loadCalendar();
                else loadCalendarWeek();
                if (typeof showToast === 'function') showToast('Calendar refreshed', 'success');
            } catch (e) {
                if (typeof showToast === 'function') showToast('Refresh failed', 'error');
            }
        }

        // Auto-refresh every 5 minutes when calendar panel is visible
        function _startCalAutoRefresh() {
            if (_calAutoRefresh) return;
            _calAutoRefresh = setInterval(() => {
                const panel = document.getElementById('calendar');
                if (panel && panel.classList.contains('active')) {
                    if (_calView === 'today') loadCalendar();
                    else loadCalendarWeek();
                }
            }, 300000);
        }

        _startCalAutoRefresh();
