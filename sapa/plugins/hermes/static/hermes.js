
        // ============== Hermes ==============

        const hermesState = {
            history: [],   // [{role, content}, ...]
            inFlight: false,
        };

        function hermesEscape(t) {
            return (typeof escapeHtml === 'function') ? escapeHtml(t) : String(t);
        }

        function renderHermesMessages() {
            const box = document.getElementById('hermesMessages');
            if (!box) return;
            if (hermesState.history.length === 0) {
                box.innerHTML = '<div class="hermes-empty">Local AI ready. Ask anything.</div>';
                return;
            }
            box.innerHTML = hermesState.history.map(m => {
                const cls = m.role === 'user' ? 'hermes-msg-user'
                    : m.role === 'error' ? 'hermes-msg-error'
                    : 'hermes-msg-assistant';
                return `<div class="hermes-msg ${cls}">${hermesEscape(m.content)}</div>`;
            }).join('');
            box.scrollTop = box.scrollHeight;
        }

        async function hermesUpdateHealth() {
            try {
                const r = await fetch('/api/hermes/health');
                const data = await r.json();
                const dot = document.getElementById('hermesStatus');
                const meta = document.getElementById('hermesMeta');
                if (dot) {
                    dot.className = 'hermes-status ' + (data.online ? 'online' : 'offline');
                    dot.title = data.online ? 'Backend online' : 'Backend offline — install/start Ollama';
                }
                if (meta) {
                    meta.textContent = `${data.backend} · ${data.model}` + (data.online ? '' : ' · OFFLINE');
                }
            } catch (e) {
                const dot = document.getElementById('hermesStatus');
                if (dot) dot.className = 'hermes-status offline';
            }
        }

        async function sendHermesMessage(event) {
            if (event) event.preventDefault();
            if (hermesState.inFlight) return false;

            const input = document.getElementById('hermesInput');
            const sendBtn = document.getElementById('hermesSendBtn');
            const userMsg = (input.value || '').trim();
            if (!userMsg) return false;

            // Snapshot history pre-user-msg for the request
            const requestHistory = hermesState.history
                .filter(m => m.role === 'user' || m.role === 'assistant')
                .map(m => ({role: m.role, content: m.content}));

            hermesState.history.push({role: 'user', content: userMsg});
            // Add a placeholder assistant message we'll stream into
            hermesState.history.push({role: 'assistant', content: ''});
            renderHermesMessages();

            input.value = '';
            hermesState.inFlight = true;
            if (sendBtn) sendBtn.disabled = true;

            try {
                const resp = await fetch('/api/hermes/chat/stream', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: userMsg, history: requestHistory}),
                });

                if (!resp.ok || !resp.body) {
                    throw new Error(`HTTP ${resp.status}`);
                }

                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, {stream: true});
                    const lines = buffer.split('\n');
                    buffer = lines.pop();  // keep partial line
                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        const payload = line.slice(6);
                        if (!payload) continue;
                        try {
                            const event = JSON.parse(payload);
                            if (event.chunk) {
                                const last = hermesState.history[hermesState.history.length - 1];
                                last.content += event.chunk;
                                renderHermesMessages();
                            }
                            if (event.error) {
                                hermesState.history.pop();  // remove empty assistant
                                hermesState.history.push({role: 'error', content: 'Error: ' + event.error});
                                renderHermesMessages();
                            }
                        } catch (e) {
                            // ignore parse errors on partial chunks
                        }
                    }
                }
            } catch (e) {
                hermesState.history.pop();
                hermesState.history.push({role: 'error', content: 'Request failed: ' + e.message});
                renderHermesMessages();
            } finally {
                hermesState.inFlight = false;
                if (sendBtn) sendBtn.disabled = false;
                input.focus();
            }
            return false;
        }

        function clearHermesChat() {
            hermesState.history = [];
            renderHermesMessages();
        }

        // Submit on Enter (Shift+Enter = newline)
        document.addEventListener('DOMContentLoaded', () => {
            const input = document.getElementById('hermesInput');
            if (input) {
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendHermesMessage(e);
                    }
                });
            }
            renderHermesMessages();
            hermesUpdateHealth();
            // Refresh health indicator periodically
            setInterval(hermesUpdateHealth, 30000);
        });
