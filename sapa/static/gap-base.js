
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text || '';
            return div.innerHTML;
        }

        function closeGapModal() {
            document.getElementById('gapPromptModal').classList.remove('show');
        }

        function copyGapPrompt() {
            const text = document.getElementById('gapModalPrompt').textContent;
            const onSuccess = () => {
                const hint = document.getElementById('gapModalHint');
                hint.textContent = 'Copied!';
                hint.style.color = 'var(--green)';
                setTimeout(() => {
                    hint.textContent = 'Click to copy prompt';
                    hint.style.color = 'var(--text-dim)';
                }, 2000);
            };
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(onSuccess);
            } else {
                const ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.left = '-9999px';
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                onSuccess();
            }
        }
