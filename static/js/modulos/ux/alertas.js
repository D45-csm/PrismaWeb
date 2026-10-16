(() => {
    const messages = document.querySelectorAll('#django-messages [data-tags]');
    const showMessages = async () => {
        for (const message of messages) {
            const tags = message.dataset.tags.split(/\s+/);
            const icon = tags.includes('error')
                ? 'error'
                : tags.includes('success')
                    ? 'success'
                    : tags.includes('warning')
                        ? 'warning'
                        : 'info';
            await window.Swal.fire({
                icon,
                text: message.textContent.trim(),
                confirmButtonText: 'Aceptar',
            });
        }
    };
    showMessages();

    document.addEventListener('submit', (event) => {
        const form = event.target.closest('form[data-confirm-post]');
        if (!form || form.dataset.confirmed === 'true') return;

        event.preventDefault();
        window.Swal.fire({
            icon: 'warning',
            title: form.dataset.confirmTitle || '¿Confirmas esta acción?',
            text: form.dataset.confirmText || 'Esta acción no se puede deshacer.',
            showCancelButton: true,
            confirmButtonText: form.dataset.confirmButton || 'Confirmar',
            cancelButtonText: 'Cancelar',
            reverseButtons: true,
        }).then((result) => {
            if (!result.isConfirmed) return;
            form.dataset.confirmed = 'true';
            form.requestSubmit();
        });
    });
})();
