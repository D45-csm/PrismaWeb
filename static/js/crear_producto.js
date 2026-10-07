/* MOSTRAR IMÁGENES PEQUEÑAS */
function mostrarImagen(input, idImagen) {
    const imagen = document.getElementById(idImagen);
    const contenedor = input.parentElement;
    const plus = contenedor.querySelector(".plus");

    if (input.files && input.files[0]) {
        const lector = new FileReader();

        lector.onload = function (e) {
            imagen.src = e.target.result;
            imagen.classList.add("mostrar");
            if (plus) plus.style.display = "none";
        };

        lector.readAsDataURL(input.files[0]);
    }
}

/* MOSTRAR IMAGEN PRINCIPAL */
function mostrarImagenPrincipal(input) {
    const imagen = document.getElementById("previewPrincipal");
    const contenido = document.getElementById("contenidoPrincipal");

    if (input.files && input.files[0]) {
        const lector = new FileReader();

        lector.onload = function (e) {
            imagen.src = e.target.result;
            imagen.classList.add("mostrar");
            contenido.style.display = "none";
        };

        lector.readAsDataURL(input.files[0]);
    }
}

/* ELIMINAR IMAGEN PEQUEÑA */
function eliminarImagen(idImagen, boton) {
    const imagen = document.getElementById(idImagen);
    const contenedor = boton.closest(".contenedor-miniatura");
    const input = contenedor.querySelector('input[type="file"]');
    const plus = contenedor.querySelector(".plus");
    const eliminar = contenedor.querySelector('input[type="hidden"]');

    imagen.src = "";
    imagen.classList.remove("mostrar");
    input.value = "";
    if (plus) plus.style.display = "block";

    if (eliminar) {
        eliminar.value = "1";
    }
}

/* ELIMINAR IMAGEN PRINCIPAL */
function eliminarImagenPrincipal() {
    const imagen = document.getElementById("previewPrincipal");
    const contenido = document.getElementById("contenidoPrincipal");
    const input = document.querySelector('input[name="imagen_principal"]');
    const eliminar = document.getElementById("eliminarImagenPrincipalInput");

    imagen.src = "";
    imagen.classList.remove("mostrar");
    input.value = "";
    contenido.style.display = "flex";
    eliminar.value = "1";
}

/* CERRAR ALERTA */
function cerrarAlerta(boton) {
    const alerta = boton.parentElement;
    alerta.classList.add("ocultar");

    setTimeout(function () {
        alerta.remove();
    }, 300);
}

/* CERRAR ALERTA AUTOMÁTICAMENTE */
setTimeout(function () {
    const alerta = document.querySelector(".alerta");

    if (alerta) {
        alerta.classList.add("ocultar");

        setTimeout(function () {
            alerta.remove();
        }, 300);
    }
}, 4000);

/* CONFIRMAR ELIMINACIÓN */
function confirmarEliminacion() {
    return confirm("¿Estás segura de que quieres eliminar este producto?");
}

/* VALIDACIÓN DEL FORMULARIO CON SWEETALERT2 */
document.addEventListener('DOMContentLoaded', function () {
    const formulario = document.querySelector('form');

    if (formulario) {
        formulario.addEventListener('submit', function (event) {
            // 1. Obtener valores de texto
            const nombre = document.getElementById('nombre')?.value.trim();
            const precio = document.getElementById('precio')?.value.trim();
            const categoria = document.getElementById('categoria')?.value.trim();
            const descripcion = document.getElementById('descripcion')?.value.trim();

            // 2. Función para verificar si existe una imagen cargada o ya previsualizada
            function tieneImagen(idInput, idPreview) {
                const input = document.querySelector(`input[name="${idInput}"]`);
                const img = document.getElementById(idPreview);

                const archivoCargado = input && input.files && input.files.length > 0;
                const tienePrevisualizacion = img && img.classList.contains('mostrar') && img.getAttribute('src') !== '';

                return archivoCargado || tienePrevisualizacion;
            }

            const tienePrincipal = tieneImagen('imagen_principal', 'previewPrincipal');
            const tieneImg2 = tieneImagen('imagen_2', 'preview2');
            const tieneImg3 = tieneImagen('imagen_3', 'preview3');
            const tieneImg4 = tieneImagen('imagen_4', 'preview4');

            // 3. Validar si falta algún campo de texto o alguna de las 4 imágenes
            if (!nombre || !precio || !categoria || !descripcion || !tienePrincipal || !tieneImg2 || !tieneImg3 || !tieneImg4) {
                
                event.preventDefault(); // Cancela el envío a Django

                Swal.fire({
                    title: '<h3 style="font-family: Georgia, \'Times New Roman\', serif; font-size: 20px; color: #111827; margin: 0;">Campos incompletos</h3>',
                    html: '<p style="color: #6b7280; font-size: 13px; margin-top: 8px; margin-bottom: 0; line-height: 1.4;">Debes llenar todos los campos e incluir las 4 imágenes requeridas para poder guardar el producto.</p>',
                    icon: 'warning',
                    iconColor: '#f59e0b',
                    background: '#ffffff',
                    backdrop: 'rgba(17, 24, 39, 0.6)',
                    confirmButtonColor: '#111827',
                    confirmButtonText: '<span style="font-family: Georgia, \'Times New Roman\', serif; font-size: 13px;">Entendido</span>',
                    width: '25em',
                    padding: '1.5em 1em'
                });
            }
        });
    }
});