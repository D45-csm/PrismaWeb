document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-confirm-reservation-cancel]').forEach(form => {
        form.addEventListener('submit', async event => {
            event.preventDefault();

            if (!window.Swal) {
                if (window.confirm(`¿Cancelar la reserva #${form.dataset.reservationId}?`)) {
                    form.submit();
                }
                return;
            }

            const isPaid = form.dataset.isPaid === 'true';
            const result = await window.Swal.fire({
                title: '¿Cancelar esta reserva?',
                html: `
                    <div class="reservation-cancel-summary">
                        <span class="reservation-cancel-icon" aria-hidden="true">
                            <i class="fas fa-calendar-xmark"></i>
                        </span>
                        <p>Vas a cancelar la reserva <strong>#${form.dataset.reservationId}</strong>.</p>
                        <p class="reservation-cancel-note">
                            Se liberarán los insumos y el espacio reservados.
                        </p>
                        ${isPaid ? '<p class="reservation-cancel-warning"><i class="fas fa-circle-exclamation" aria-hidden="true"></i> El pago ya fue confirmado; recuerda gestionar la devolución.</p>' : ''}
                    </div>
                `,
                showCancelButton: true,
                reverseButtons: true,
                focusCancel: true,
                confirmButtonText: 'Sí, cancelar reserva',
                cancelButtonText: 'Conservar reserva',
                confirmButtonColor: '#a33c50',
                cancelButtonColor: '#f1edf5',
                customClass: {
                    popup: 'reservation-cancel-popup',
                    title: 'reservation-cancel-title',
                    htmlContainer: 'reservation-cancel-content',
                    confirmButton: 'reservation-cancel-confirm',
                    cancelButton: 'reservation-cancel-dismiss',
                },
            });

            if (result.isConfirmed) form.submit();
        });
    });

    const form = document.getElementById('reservaForm');
    const productList = document.getElementById('reservaProductosList');
    if (!form || !productList) return;

    const cards = [...productList.querySelectorAll('[data-reserva-producto-slot]')];
    const addButton = document.getElementById('addReservaProducto');
    const total = document.getElementById('reservaTotalEstimate');
    const modality = document.getElementById('tipo_reserva');
    const guests = document.getElementById('numero_personas');
    const date = document.getElementById('fecha');
    const formatCOP = value => new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        maximumFractionDigits: 0,
    }).format(value);

    productList.classList.add('is-interactive');

    const updateForm = () => {
        const visibleCards = cards.filter(card => card.classList.contains('is-visible'));
        const selectedCards = visibleCards.filter(card => card.querySelector('select').value);
        let amount = 0;

        visibleCards.forEach(card => {
            const select = card.querySelector('select');
            const quantity = Number(card.querySelector('input[type="number"]').value) || 0;
            amount += (Number(select.selectedOptions[0]?.dataset.price) || 0) * quantity;
            select.required = selectedCards.length === 0 && card === visibleCards[0];
            const removeButton = card.querySelector('[data-remove-reserva-producto]');
            if (removeButton) removeButton.hidden = visibleCards.length === 1;
        });

        if (total) total.textContent = formatCOP(amount);
        if (addButton) {
            const hasSlot = cards.some(card => !card.classList.contains('is-visible'));
            addButton.hidden = !hasSlot;
            addButton.disabled = !hasSlot;
        }
        if (modality && guests) guests.required = modality.value === 'Mesa';
    };

    cards.forEach(card => {
        const select = card.querySelector('select');
        const quantity = card.querySelector('input[type="number"]');
        select.required = false;
        select.addEventListener('change', updateForm);
        quantity.addEventListener('input', updateForm);
        card.querySelector('[data-remove-reserva-producto]').addEventListener('click', () => {
            select.value = '';
            quantity.value = '1';
            card.classList.remove('is-visible');
            updateForm();
        });
    });

    if (addButton) {
        addButton.hidden = false;
        addButton.addEventListener('click', () => {
            const nextCard = cards.find(card => !card.classList.contains('is-visible'));
            if (!nextCard) return;
            nextCard.classList.add('is-visible');
            updateForm();
            nextCard.querySelector('select').focus({ preventScroll: true });
        });
    }

    if (modality && guests) modality.addEventListener('change', updateForm);
    if (date) {
        const now = new Date();
        date.min = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    }
    updateForm();
});
