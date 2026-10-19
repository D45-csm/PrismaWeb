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

    document.querySelectorAll('.form-eliminar-proveedor').forEach(function (form) {
        form.addEventListener('submit', async function (event) {
            event.preventDefault();
            const providerName = form.dataset.providerName || 'este proveedor';
            const result = await Swal.fire({
                title: '¿Eliminar proveedor?',
                text: `¿Confirmas la eliminación definitiva de ${providerName}?`,
                icon: 'warning',
                background: '#ffffff',
                backdrop: 'rgba(17, 24, 39, 0.6)',
                showCancelButton: true,
                confirmButtonColor: '#dc2626',
                cancelButtonColor: '#111827',
                confirmButtonText: 'Sí, eliminar',
                cancelButtonText: 'Cancelar',
                reverseButtons: true,
                focusCancel: true,
                width: '25em',
                padding: '1.5em 1em',
                customClass: {
                    title: 'prisma-message-title',
                    htmlContainer: 'prisma-message-text',
                    confirmButton: 'prisma-message-confirm',
                    cancelButton: 'prisma-message-confirm',
                },
            });

            if (result.isConfirmed) {
                HTMLFormElement.prototype.submit.call(form);
            }
        });
    });
});
