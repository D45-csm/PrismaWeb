const prismaMessageLevels = {
    success: { title: '¡Éxito!', icon: 'success' },
    error: { title: '¡Error!', icon: 'error' },
    warning: { title: 'Atención', icon: 'warning' },
    info: { title: 'Aviso', icon: 'info' },
};

window.showPrismaMessage = function (text, level = 'info') {
    const notification = prismaMessageLevels[level] || prismaMessageLevels.info;
    return Swal.fire({
        title: notification.title,
        text: text,
        icon: notification.icon,
        background: '#ffffff',
        backdrop: 'rgba(17, 24, 39, 0.6)',
        confirmButtonColor: '#111827',
        confirmButtonText: 'Aceptar',
        timer: 3500,
        timerProgressBar: true,
        width: '25em',
        padding: '1.5em 1em',
        customClass: {
            title: 'prisma-message-title',
            htmlContainer: 'prisma-message-text',
            confirmButton: 'prisma-message-confirm',
        },
    });
};

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('#django-messages .django-message').forEach(
        function (message) {
            const tags = (message.dataset.tags || '').split(/\s+/);
            const level = Object.keys(prismaMessageLevels).find(
                (tag) => tags.includes(tag)
            ) || 'info';
            window.showPrismaMessage(message.dataset.text || '', level);
        }
    );

    document.querySelectorAll('[data-confirm-receipt-action]').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (form.dataset.confirmed === 'true') return;

            event.preventDefault();
            const aprobar = form.dataset.confirmReceiptAction === 'approve';
            const reservaId = form.dataset.reservationId;
            const boton = form.querySelector('button[type="submit"]');
            if (boton) boton.disabled = true;

            const confirmacion = window.Swal
                ? window.Swal.fire({
                    title: aprobar ? '¿Aprobar el comprobante?' : '¿Rechazar el comprobante?',
                    text: aprobar
                        ? `La reserva #${reservaId} quedará confirmada.`
                        : `El cliente podrá enviar un nuevo comprobante para la reserva #${reservaId}.`,
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonText: aprobar ? 'Sí, aprobar' : 'Sí, rechazar',
                    cancelButtonText: 'Volver',
                    confirmButtonColor: aprobar ? '#198754' : '#dc3545',
                    cancelButtonColor: '#6c757d',
                })
                : Promise.resolve({
                    isConfirmed: window.confirm(
                        `${aprobar ? '¿Aprobar' : '¿Rechazar'} el comprobante de la reserva #${reservaId}?`,
                    ),
                });

            confirmacion.then(function (resultado) {
                if (resultado.isConfirmed) {
                    form.dataset.confirmed = 'true';
                    form.submit();
                } else if (boton) {
                    boton.disabled = false;
                }
            });
        });
    });
});
