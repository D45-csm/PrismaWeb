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

});
