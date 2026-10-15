document.addEventListener('DOMContentLoaded', function () {

    // 1. ALERTAS DE DJANGO MESSAGES (SWEETALERT2)
    const djangoMessages = document.querySelectorAll('#django-messages .django-message');

    djangoMessages.forEach(msg => {
        const tags = msg.getAttribute('data-tags') || '';
        const text = msg.getAttribute('data-text') || '';

        let title = 'Aviso';
        let icon = 'info';

        if (tags.includes('success')) {
            title = '¡Éxito!';
            icon = 'success';
        } else if (tags.includes('error')) {
            title = '¡Error!';
            icon = 'error';
        } else if (tags.includes('warning')) {
            title = 'Atención';
            icon = 'warning';
        }

        Swal.fire({
            title: `<h3 style="font-family: Georgia, 'Times New Roman', serif; font-size: 20px; color: #111827; margin: 0;">${title}</h3>`,
            html: `<p style="color: #6b7280; font-size: 13px; margin-top: 8px; margin-bottom: 0;">${text}</p>`,
            icon: icon,
            background: '#ffffff',
            backdrop: 'rgba(17, 24, 39, 0.6)',
            confirmButtonColor: '#111827',
            confirmButtonText: '<span style="font-family: Georgia, \'Times New Roman\', serif; font-size: 13px;">Aceptar</span>',
            timer: 3500,
            timerProgressBar: true,
            width: '25em',
            padding: '1.5em 1em'
        });
    });

    // 2. CONFIRMACIÓN DE ELIMINACIÓN DE PRODUCTO

    const formulariosEliminar = document.querySelectorAll('.form-eliminar');

    formulariosEliminar.forEach(form => {
        form.addEventListener('submit', function (event) {
            event.preventDefault();

            Swal.fire({
                title: '<h3 style="font-family: Georgia, \'Times New Roman\', serif; font-size: 20px; color: #111827; margin: 0;">¿Estás seguro de que quieres eliminar este producto?</h3>',
                html: '<p style="color: #6b7280; font-size: 13px; margin-top: 8px; margin-bottom: 0; line-height: 1.4;">Una vez eliminado, ya no aparecerá en tu catálogo y no podrás recuperarlo</p>',
                icon: 'warning',
                iconColor: '#ef4444', 
                background: '#ffffff',
                backdrop: 'rgba(17, 24, 39, 0.6)', 
                showCancelButton: true,
                confirmButtonColor: '#dc2626', 
                cancelButtonColor: '#111827',  
                confirmButtonText: '<span style="font-family: Georgia, \'Times New Roman\', serif; font-size: 13px;">Sí, eliminar</span>',
                cancelButtonText: '<span style="font-family: Georgia, \'Times New Roman\', serif; font-size: 13px;">Cancelar</span>',
                reverseButtons: true, 
                focusCancel: true,
                width: '25em', 
                padding: '1.5em 1em'
            }).then((result) => {
                if (result.isConfirmed) {
                    Swal.fire({
                        title: '<h3 style="font-family: Georgia, \'Times New Roman\', serif; font-size: 20px; color: #111827; margin: 0;">¡Producto eliminado!</h3>',
                        html: '<p style="color: #6b7280; font-size: 13px; margin-top: 8px; margin-bottom: 0;">El producto fue eliminado correctamente de tu catálogo</p>',
                        icon: 'success',
                        iconColor: '#10b981',
                        background: '#ffffff',
                        backdrop: 'rgba(17, 24, 39, 0.6)',
                        showConfirmButton: false,
                        timer: 1500,
                        width: '25em',
                        padding: '1.5em 1em'
                    }).then(() => {
                        form.submit();
                    });
                }
            });
        });
    });

});