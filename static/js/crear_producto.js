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