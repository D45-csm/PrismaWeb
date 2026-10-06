document.addEventListener('DOMContentLoaded', function () {
    const formulariosEliminar = document.querySelectorAll('.form-eliminar');

    formulariosEliminar.forEach(form => {
        form.addEventListener('submit', function (event) {
            event.preventDefault();

            Swal.fire({
                // Título pequeño
                title: '<h3 style="font-family: Georgia, \'Times New Roman\', serif; font-size: 20px; color: #111827; margin: 0;">¿Estás seguro de que quieres eliminar este producto?</h3>',
                
                // TEXTO ORIGINAL RESTAURADO (con tamaño de letra adecuado)
                html: '<p style="color: #6b7280; font-size: 13px; margin-top: 8px; margin-bottom: 0; line-height: 1.4;">Una vez eliminado, ya no aparecerá en tu catálogo y no podrás recuperarlo.</p>',
                
                icon: 'warning',
                iconColor: '#ef4444', 
                background: '#ffffff',
                backdrop: 'rgba(17, 24, 39, 0.6)', 
                showCancelButton: true,
                
                confirmButtonColor: '#dc2626', 
                cancelButtonColor: '#111827',  
                
                // Botones pequeños
                confirmButtonText: '<span style="font-family: Georgia, \'Times New Roman\', serif; font-size: 13px;">Sí, eliminar</span>',
                cancelButtonText: '<span style="font-family: Georgia, \'Times New Roman\', serif; font-size: 13px;">Cancelar</span>',
                
                reverseButtons: true, 
                focusCancel: true,
                
                // Tamaño compacto de la alerta
                width: '25em', 
                padding: '1.5em 1em'
                
            }).then((result) => {
                if (result.isConfirmed) {
                    
                    // SEGUNDA ALERTA: ÉXITO (con el mismo tamaño y estilo compacto)
                    Swal.fire({
                        title: '<h3 style="font-family: Georgia, \'Times New Roman\', serif; font-size: 20px; color: #111827; margin: 0;">¡Producto eliminado!</h3>',
                        html: '<p style="color: #6b7280; font-size: 13px; margin-top: 8px; margin-bottom: 0;">El producto fue eliminado correctamente de tu catálogo.</p>',
                        icon: 'success',
                        iconColor: '#10b981', // Verde estilo Tailwind
                        background: '#ffffff',
                        backdrop: 'rgba(17, 24, 39, 0.6)',
                        showConfirmButton: false, // Sin botón, se cierra sola
                        timer: 1500, // Duración de 1.5 segundos
                        width: '25em',
                        padding: '1.5em 1em'
                    }).then(() => {
                        // El formulario se envía automáticamente tras cerrarse la alerta de éxito
                        form.submit();
                    });
                    
                }
            });
        });
    });
});