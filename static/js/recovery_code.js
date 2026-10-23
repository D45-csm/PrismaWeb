document.addEventListener('DOMContentLoaded', () => {
    const button = document.querySelector('[data-copy-recovery-code]');
    const code = document.getElementById('recovery-code-value');
    const status = document.querySelector('[data-copy-recovery-code-status]');

    if (!button || !code || !status) {
        return;
    }

    button.addEventListener('click', async () => {
        const value = code.textContent.trim();

        if (!navigator.clipboard || !window.isSecureContext) {
            status.textContent = 'No se pudo copiar automáticamente. Selecciona el código y cópialo manualmente.';
            return;
        }

        try {
            await navigator.clipboard.writeText(value);
            status.textContent = 'Código copiado. Guárdalo en un lugar privado.';
        } catch {
            status.textContent = 'No se pudo copiar automáticamente. Selecciona el código y cópialo manualmente.';
        }
    });
});
