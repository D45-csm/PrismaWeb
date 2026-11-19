(() => {
    document.querySelectorAll('[data-cancel-movement]').forEach((form) => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const reasonField = form.querySelector('[name="motivo"]');
            let reason = '';

            if (window.Swal) {
                const summary = document.createElement('div');
                summary.className = 'reservation-cancel-summary';
                const icon = document.createElement('span');
                icon.className = 'reservation-cancel-icon';
                icon.setAttribute('aria-hidden', 'true');
                icon.innerHTML = '<i class="fas fa-boxes-stacked"></i>';
                const movement = document.createElement('p');
                movement.textContent = `${form.dataset.movementAction} de ${form.dataset.movementQuantity} para ${form.dataset.movementName}.`;
                const note = document.createElement('p');
                note.className = 'reservation-cancel-note';
                note.textContent = 'El registro se conservará en el historial y dejará de afectar el stock.';
                summary.append(icon, movement, note);

                const result = await window.Swal.fire({
                    title: '¿Anular este movimiento?',
                    html: summary,
                    input: 'textarea',
                    inputLabel: 'Motivo de anulación',
                    inputPlaceholder: 'Explica por qué se anula este movimiento',
                    inputAttributes: {maxlength: 500, 'aria-label': 'Motivo de anulación'},
                    inputValidator: (value) => (
                        (value || '').trim() ? undefined : 'El motivo es obligatorio.'
                    ),
                    showCancelButton: true,
                    reverseButtons: true,
                    focusCancel: true,
                    confirmButtonText: 'Sí, anular movimiento',
                    cancelButtonText: 'Conservar movimiento',
                    confirmButtonColor: '#a33c50',
                    cancelButtonColor: '#f1edf5',
                    customClass: {
                        popup: 'reservation-cancel-popup',
                        title: 'reservation-cancel-title',
                        htmlContainer: 'reservation-cancel-content',
                        input: 'inventory-cancel-reason-input',
                        inputLabel: 'inventory-cancel-reason-label',
                        confirmButton: 'reservation-cancel-confirm',
                        cancelButton: 'reservation-cancel-dismiss',
                    },
                });
                if (!result.isConfirmed) return;
                reason = result.value.trim();
            } else {
                if (!window.confirm('¿Deseas anular este movimiento?')) return;
                reason = window.prompt('Indica el motivo de anulación:')?.trim() || '';
                if (!reason) return;
            }

            reasonField.value = reason;
            form.submit();
        });
    });

    const dialog = document.querySelector('.inventory-dialog');
    if (!dialog) return;

    const mode = dialog.querySelector('#manualModo');
    const actionField = dialog.querySelector('#manualActionField');
    const quantityLabel = dialog.querySelector('#manualQuantityLabel');

    const syncMode = () => {
        const isCount = mode.value === 'conteo';
        actionField.hidden = isCount;
        quantityLabel.textContent = isCount
            ? 'Cantidad contada físicamente'
            : 'Cantidad del ajuste';
    };

    document.querySelector('[data-open-inventory-dialog]')
        ?.addEventListener('click', () => dialog.showModal());
    dialog.querySelectorAll('[data-close-inventory-dialog]')
        .forEach((button) => button.addEventListener('click', () => dialog.close()));
    mode.addEventListener('change', syncMode);
    syncMode();

    if (dialog.dataset.open === 'true') dialog.showModal();
})();
