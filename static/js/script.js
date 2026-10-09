document.addEventListener('DOMContentLoaded', () => {

    // ============================================
    // 0. RUTAS DE DJANGO (definidas en base_prisma.html)
    // ============================================
    const CFG = window.PRISMA || {};
    const URLS = CFG.urls || {};
    const IMG_BASE = CFG.imgBase || '';
    // Convierte 'postre_1.jpeg' en '/static/img/postre_1.jpeg'
    const imgUrl = (nombre) => IMG_BASE + encodeURI(nombre);

    // ============================================
    // 1. CONFIGURACIÓN Y DATOS
    // ============================================
    const productos = [
        { id: 1, nombre: 'Manzana Verde', precio: 15000, img: 'mangue_azul_julho2023_dmr__420___1_-23855745.jpg', categoria: 'frutas', desc: 'Delicioso postre con sabor a manzana verde, textura suave y cremosa.' },
        { id: 2, nombre: 'Café Chocolate', precio: 15000, img: 'postre_1.jpeg', categoria: 'chocolate', desc: 'La combinación perfecta de café y chocolate. Intenso y aromático.' },
        { id: 3, nombre: 'Naranja Fresca', precio: 15000, img: 'postre_2.jpeg', categoria: 'frutas', desc: 'Refrescante postre con sabor cítrico a naranja natural.' },
        { id: 4, nombre: 'Coco Tropical', precio: 15000, img: 'postre_3.jpg', categoria: 'especiales', desc: 'Exótico postre con coco rallado y crema tropical.' },
        { id: 5, nombre: 'Mango Exótico', precio: 15000, img: 'postre_4.jpg', categoria: 'frutas', desc: 'Sabor tropical intenso a mango maduro.' },
        { id: 6, nombre: 'Fresa Chocolate', precio: 15000, img: 'postre_5.jpg', categoria: 'chocolate', desc: 'Fresa fresca cubierta de chocolate suave.' },
        { id: 7, nombre: 'Piña Amarilla', precio: 15000, img: 'postre_6.jpg', categoria: 'frutas', desc: 'Dulce y tropical postre con piña fresca.' },
        { id: 8, nombre: 'Corazón Rojo', precio: 15000, img: 'postre_7.jpg', categoria: 'especiales', desc: 'Especial romántico con frutos rojos y chocolate.' }
    ];

    const temporada = [
        { id: 101, nombre: 'Cheesecake Frutos Rojos', desc: 'Suave y cremoso con coulis artesanal.', precio: 15000, img: 'frutos rojos.jpeg', categoria: 'especiales' },
        { id: 102, nombre: 'Arándano', desc: 'Cítrica y refrescante con merengue.', precio: 15000, img: 'Arándano.jpeg', categoria: 'frutas' },
        { id: 103, nombre: 'Mango', desc: 'Relleno de chocolate belga fundido.', precio: 15000, img: 'mango.jpeg', categoria: 'chocolate' },
        { id: 104, nombre: 'Coulant Maracuyá', desc: 'Puro sabor a la pasión.', precio: 15000, img: 'postre de maracuyá.jpeg', categoria: 'especiales' },
        { id: 105, nombre: 'Tiramisú Clásico', desc: 'El italiano tradicional.', precio: 15000, img: 'postre_6.jpg', categoria: 'especiales' },
        { id: 106, nombre: 'Mousse Maracuyá', desc: 'Aireada y refrescante.', precio: 15000, img: 'postre_7.jpg', categoria: 'frutas' }
    ];

    let carrito = JSON.parse(localStorage.getItem('prismaCarrito')) || [];
    let productoActual = null;
    let origenActual = 'productos';
    let tamañoSeleccionado = 'personal';

    // ============================================
    // 2. UTILIDADES
    // ============================================
    const mostrarNotificacion = (mensaje) => {
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.textContent = mensaje;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    };


    const escapeHTML = (t) => String(t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const capitalizar = (t) => t ? t.charAt(0).toUpperCase() + t.slice(1) : t;

    const hoyISO = () => {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    };

    // "2026-10-03" -> "03/10/2026 (sábado)"
    const formatearFecha = (valor) => {
        if (!valor) return 'Lo antes posible';
        const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(valor);
        if (!m) return valor;
        const f = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
        const dia = f.toLocaleDateString('es-CO', { weekday: 'long' });
        return `${m[3]}/${m[2]}/${m[1]} (${dia})`;
    };

    // ---------- Diálogos Prisma (reemplazan alert / confirm / prompt) ----------
    const abrirModalPrisma = ({ claseExtra = '', html, alMontar, alAceptar }) => new Promise((resolve) => {
        const previo = document.activeElement;
        const overlay = document.createElement('div');
        overlay.className = 'pz-overlay';
        overlay.innerHTML = `<div class="pz-dialog ${claseExtra}" role="dialog" aria-modal="true">${html}</div>`;
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';
        const dialog = overlay.firstElementChild;
        let cerrado = false;

        const onKey = (e) => { if (e.key === 'Escape') cerrar(null); };
        const cerrar = (valor) => {
            if (cerrado) return;
            cerrado = true;
            document.removeEventListener('keydown', onKey);
            overlay.classList.add('closing');
            document.body.style.overflow = document.body.classList.contains('menu-open') ? 'hidden' : '';
            setTimeout(() => { overlay.remove(); if (previo && previo.focus) previo.focus(); }, 220);
            resolve(valor);
        };

        document.addEventListener('keydown', onKey);
        overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) cerrar(null); });
        dialog.querySelectorAll('[data-cancel]').forEach(b => b.addEventListener('click', () => cerrar(null)));
        dialog.querySelectorAll('[data-accept]').forEach(b => b.addEventListener('click', () => {
            const valor = alAceptar ? alAceptar(dialog) : true;
            if (valor) cerrar(valor);
        }));

        if (alMontar) alMontar(dialog);
        requestAnimationFrame(() => {
            overlay.classList.add('open');
            const foco = dialog.querySelector('[data-autofocus]');
            if (foco) foco.focus({ preventScroll: true });
        });
    });

    const confirmarPrisma = ({ icono = 'fa-circle-question', inicial = '', titulo, mensaje, confirmar = 'Aceptar', cancelar = 'Cancelar' }) =>
        abrirModalPrisma({
            claseExtra: 'pz-confirm',
            html: `
                <div class="pz-rainbow"></div>
                <div class="pz-icon">${inicial ? `<span>${escapeHTML(inicial)}</span>` : `<i class="fas ${icono}"></i>`}</div>
                <h3 class="pz-title">${titulo}</h3>
                <p class="pz-text">${mensaje}</p>
                <div class="pz-actions">
                    <button type="button" class="pz-btn pz-btn-ghost" data-cancel>${cancelar}</button>
                    <button type="button" class="pz-btn pz-btn-primary" data-accept data-autofocus>${confirmar}</button>
                </div>`
        }).then(r => r === true);

    // ---------- Chips y contador para el campo "¿Cómo quieres tu reserva?" ----------
    const CHIPS_RESERVA = [
        { etiqueta: '🎁 Es para regalo', texto: 'Es para regalo' },
        { etiqueta: '🕯️ Con vela', texto: 'Con vela' },
        { etiqueta: '✍️ Mensaje en el postre', texto: 'Mensaje en el postre: ' },
        { etiqueta: '🍬 Poco dulce', texto: 'Poco dulce' },
        { etiqueta: '⚠️ Alergias', texto: 'Alergia a: ' }
    ];

    const activarDetalles = (textarea, contenedorChips, contador) => {
        if (!textarea) return;
        const max = textarea.maxLength > 0 ? textarea.maxLength : 500;
        const actualizar = () => { if (contador) contador.textContent = textarea.value.length; };
        textarea.addEventListener('input', actualizar);
        if (contenedorChips) {
            contenedorChips.innerHTML = CHIPS_RESERVA
                .map((c, i) => `<button type="button" class="pz-chip" data-i="${i}">${c.etiqueta}</button>`).join('');
            contenedorChips.addEventListener('click', (e) => {
                const chip = e.target.closest('.pz-chip');
                if (!chip) return;
                const { texto } = CHIPS_RESERVA[Number(chip.dataset.i)];
                const previo = textarea.value.trim();
                textarea.value = (previo ? previo + '\n' : '') + '• ' + texto;
                textarea.value = textarea.value.slice(0, max);
                textarea.focus();
                textarea.setSelectionRange(textarea.value.length, textarea.value.length);
                actualizar();
            });
        }
        actualizar();
    };

    // ---------- Ventana de reserva (desde el carrito) ----------
    const pedirDatosReserva = ({ totalPostres, total }) => abrirModalPrisma({
        claseExtra: 'pz-reserva',
        html: `
            <div class="pz-rainbow"></div>
            <button type="button" class="pz-close" data-cancel aria-label="Cerrar"><i class="fas fa-xmark"></i></button>
            <div class="pz-icon"><i class="fas fa-calendar-check"></i></div>
            <h3 class="pz-title">Reserva tu pedido</h3>
            <p class="pz-text">Cuéntanos para cuándo lo quieres y cómo lo imaginas. Prisma te confirmará la reserva por WhatsApp.</p>
            <div class="pz-summary">
                <span><i class="fas fa-cake-candles"></i>${totalPostres} ${totalPostres === 1 ? 'postre' : 'postres'}</span>
                <strong>Total estimado: $${total.toLocaleString('es-CO')}</strong>
            </div>
            <div class="pz-field">
                <label for="pzFecha">¿Para qué fecha?</label>
                <div class="pz-input" id="pzFechaWrap"><i class="fas fa-calendar-days"></i><input type="date" id="pzFecha" min="${hoyISO()}" data-autofocus></div>
                <label class="pz-check"><input type="checkbox" id="pzAsap"> Lo quiero lo antes posible</label>
                <p class="pz-error" id="pzError" hidden>Elige una fecha o marca “lo antes posible”.</p>
            </div>
            <div class="pz-field">
                <label for="pzNotas">¿Cómo quieres tu reserva? <small>(opcional)</small></label>
                <textarea id="pzNotas" rows="4" maxlength="400" placeholder="Ej: Es para un cumpleaños, con el mensaje “Feliz cumpleaños Ana”, sin nueces y poco dulce…"></textarea>
                <div class="pz-chips" id="pzChips"></div>
                <div class="pz-counter"><span id="pzCount">0</span>/400</div>
            </div>
            <div class="pz-actions">
                <button type="button" class="pz-btn pz-btn-ghost" data-cancel>Cancelar</button>
                <button type="button" class="pz-btn pz-btn-primary" data-accept><i class="fab fa-whatsapp"></i> Enviar reserva</button>
            </div>`,
        alMontar: (dlg) => {
            const asap = dlg.querySelector('#pzAsap');
            const fecha = dlg.querySelector('#pzFecha');
            const wrap = dlg.querySelector('#pzFechaWrap');
            const error = dlg.querySelector('#pzError');
            asap.addEventListener('change', () => {
                fecha.disabled = asap.checked;
                wrap.classList.toggle('disabled', asap.checked);
                if (asap.checked) { fecha.value = ''; error.hidden = true; }
            });
            fecha.addEventListener('input', () => { error.hidden = true; });
            activarDetalles(dlg.querySelector('#pzNotas'), dlg.querySelector('#pzChips'), dlg.querySelector('#pzCount'));
        },
        alAceptar: (dlg) => {
            const asap = dlg.querySelector('#pzAsap').checked;
            const fecha = dlg.querySelector('#pzFecha').value;
            const error = dlg.querySelector('#pzError');
            if (!asap && (!fecha || fecha < hoyISO())) {
                error.textContent = fecha ? 'La fecha no puede ser anterior a hoy.' : 'Elige una fecha o marca “lo antes posible”.';
                error.hidden = false;
                dlg.querySelector('#pzFecha').focus();
                return false;
            }
            return { fecha: asap ? '' : fecha, notas: dlg.querySelector('#pzNotas').value.trim() };
        }
    });

    // ---------- Menú móvil (se construye solo, sirve para todas las páginas) ----------
    let setMenuMovil = () => {};
    const construirMenuMovil = () => {
        const nav = document.getElementById('navMenu');
        if (!nav || nav.dataset.built) return;
        nav.dataset.built = '1';

        const logo = document.querySelector('.logo img');
        const head = document.createElement('div');
        head.className = 'drawer-head';
        head.innerHTML = `
            ${logo ? `<img src="${logo.getAttribute('src')}" alt="Prisma">` : ''}
            <div class="drawer-brand"><strong>Prisma</strong><span>El arte del postre</span></div>
            <button type="button" class="drawer-close" aria-label="Cerrar menú"><i class="fas fa-xmark"></i></button>`;
        nav.prepend(head);

        const iconos = { [URLS.inicio]: 'fa-house', [URLS.productos]: 'fa-cake-candles', [URLS.reservas]: 'fa-calendar-check', [URLS.contactos]: 'fa-comments', [URLS.temporada]: 'fa-apple-whole' };
        nav.querySelectorAll('ul a').forEach(a => {
            const ic = iconos[a.getAttribute('href')] || 'fa-star';
            a.insertAdjacentHTML('afterbegin', `<span class="nav-ico"><i class="fas ${ic}"></i></span>`);
        });

        const textoWa = encodeURIComponent('Hola Prisma 👋 Quisiera información para hacer una reserva.');
        const foot = document.createElement('div');
        foot.className = 'drawer-foot';
        foot.innerHTML = `
            <a class="drawer-wa" href="https://wa.me/573118689862?text=${textoWa}" target="_blank" rel="noopener"><i class="fab fa-whatsapp"></i> Reservar por WhatsApp</a>
            <p><i class="fas fa-phone"></i> +57 311 868 9862</p>`;
        nav.appendChild(foot);

        const backdrop = document.createElement('div');
        backdrop.className = 'nav-backdrop';
        (document.getElementById('header') || document.body).appendChild(backdrop);

        const btnBurger = document.querySelector('.mobile-menu-btn');
        setMenuMovil = (abierto) => {
            nav.classList.toggle('mobile-open', abierto);
            backdrop.classList.toggle('show', abierto);
            document.body.classList.toggle('menu-open', abierto);
            if (btnBurger) {
                btnBurger.setAttribute('aria-expanded', abierto);
                btnBurger.innerHTML = `<i class="fas ${abierto ? 'fa-xmark' : 'fa-bars'}"></i>`;
            }
        };

        head.querySelector('.drawer-close').addEventListener('click', () => setMenuMovil(false));
        backdrop.addEventListener('click', () => setMenuMovil(false));
        nav.querySelectorAll('ul a').forEach(a => a.addEventListener('click', () => setMenuMovil(false)));
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setMenuMovil(false); });
        window.addEventListener('resize', () => { if (window.innerWidth > 768) setMenuMovil(false); });
    };

    const actualizarContadorCarrito = () => {
        const count = carrito.reduce((sum, item) => sum + item.cantidad, 0);
        document.querySelectorAll('.cart-count').forEach(el => el.textContent = count);
    };

    // ============================================
    // 3. LÓGICA DEL CARRITO
    // ============================================
    const agregarAlCarrito = (id, origen = 'productos', tamañoForzado = null) => {
        const lista = origen === 'productos' ? productos : temporada;
        const producto = lista.find(p => p.id === id);
        if (!producto) return;

        const tamaño = tamañoForzado || 'personal';
        const multiplicadores = { personal: 1, mediano: 1.8, grande: 2.5 };
        const precioFinal = Math.round(producto.precio * multiplicadores[tamaño]);

        const itemExistente = carrito.find(i => i.id === id && i.tamaño === tamaño);
        if (itemExistente) {
            itemExistente.cantidad++;
        } else {
            carrito.push({ ...producto, precio: precioFinal, cantidad: 1, tamaño });
        }

        localStorage.setItem('prismaCarrito', JSON.stringify(carrito));
        actualizarContadorCarrito();
        mostrarNotificacion(`✅ ${producto.nombre} agregado`);
    };

    const agregarDesdeModal = () => {
        if (!productoActual) return;
        agregarAlCarrito(productoActual.id, origenActual, tamañoSeleccionado);
        cerrarModal();
    };

    const cambiarCantidad = (id, delta) => {
        const item = carrito.find(i => i.id === id);
        if (!item) return;
        item.cantidad += delta;
        if (item.cantidad <= 0) {
            carrito = carrito.filter(i => i.id !== id);
        }
        localStorage.setItem('prismaCarrito', JSON.stringify(carrito));
        actualizarContadorCarrito();
        renderizarCarrito();
    };

    const eliminarItem = (id) => {
        carrito = carrito.filter(i => i.id !== id);
        localStorage.setItem('prismaCarrito', JSON.stringify(carrito));
        actualizarContadorCarrito();
        renderizarCarrito();
        mostrarNotificacion('🗑️ Producto eliminado');
    };

    const renderizarCarrito = () => {
        const container = document.getElementById('cartItemsList');
        if (!container) return;

        if (carrito.length === 0) {
            container.innerHTML = '<div class="empty-cart"><i class="fas fa-shopping-basket"></i><p>Tu carrito está vacío 😢</p></div>';
            document.getElementById('subtotal').textContent = '$0';
            document.getElementById('total').textContent = '$0';
            return;
        }

        let subtotal = 0;
        container.innerHTML = carrito.map(item => {
            subtotal += item.precio * item.cantidad;
            return `
                <div class="cart-item">
                    <img src="${imgUrl(item.img)}" alt="${item.nombre}">
                    <div class="cart-item-info">
                        <h4>${item.nombre}</h4>
                        <p class="item-size">Tamaño: ${item.tamaño}</p>
                        <p class="item-price">$${item.precio.toLocaleString('es-CO')}</p>
                        <div class="cart-item-actions">
                            <button class="qty-btn" onclick="cambiarCantidad(${item.id}, -1)">−</button>
                            <span>${item.cantidad}</span>
                            <button class="qty-btn" onclick="cambiarCantidad(${item.id}, 1)">+</button>
                            <button class="cart-item-remove" onclick="eliminarItem(${item.id})" title="Quitar"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        document.getElementById('subtotal').textContent = '$' + subtotal.toLocaleString('es-CO');
        document.getElementById('total').textContent = '$' + (subtotal + 5000).toLocaleString('es-CO');
    };

    const obtenerUsuario = () => JSON.parse(localStorage.getItem('prismaUsuario') || sessionStorage.getItem('prismaUsuario') || 'null');

    const checkout = async () => {
        if (carrito.length === 0) {
            mostrarNotificacion('🛒 Tu carrito está vacío');
            return;
        }
        const usuario = obtenerUsuario();
        if (!usuario) {
            mostrarNotificacion('🔒 Inicia sesión para finalizar tu reserva');
            sessionStorage.setItem('redirectAfterLogin', URLS.carrito);
            setTimeout(() => { window.location.href = URLS.login; }, 1200);
            return;
        }

        const totalPostres = carrito.reduce((sum, i) => sum + i.cantidad, 0);
        const subtotal = carrito.reduce((sum, i) => sum + (i.precio * i.cantidad), 0);
        const envio = 5000;
        const total = subtotal + envio;
        const fmt = (n) => '$' + n.toLocaleString('es-CO');

        const datos = await pedirDatosReserva({ totalPostres, total });
        if (!datos) return;

        const lineas = carrito.map((i, n) =>
            `${n + 1}. ${i.nombre} (${capitalizar(i.tamaño)}) ×${i.cantidad} — ${fmt(i.precio * i.cantidad)}`
        ).join('\n');

        const texto = [
            '🌈 *RESERVA · PRISMA*',
            '━━━━━━━━━━━━━━',
            `👤 *Cliente:* ${capitalizar(usuario.nombre)}`,
            `📅 *Fecha de la reserva:* ${formatearFecha(datos.fecha)}`,
            '',
            '🍰 *Postres a reservar*',
            lineas,
            '',
            `🔢 Total de postres: ${totalPostres}`,
            `🧾 Subtotal: ${fmt(subtotal)}`,
            `🚚 Envío: ${fmt(envio)}`,
            `💰 *Total estimado: ${fmt(total)}*`,
            '',
            '📝 *¿Cómo quiero mi reserva?*',
            datos.notas || 'Sin indicaciones especiales.',
            '━━━━━━━━━━━━━━',
            'Quedo atento(a) a la confirmación. ¡Gracias! 🙌'
        ].join('\n');

        mostrarNotificacion('📲 Abriendo WhatsApp con tu reserva…');
        window.open(`https://wa.me/573118689862?text=${encodeURIComponent(texto)}`, '_blank');
    };

    // ============================================
    // SESIÓN DE USUARIO
    // ============================================
    const actualizarBotonLogin = () => {
        const btn = document.querySelector('.btn-login');
        if (!btn) return;
        const usuario = obtenerUsuario();
        if (usuario) {
            btn.innerHTML = '<i class="fas fa-user-check"></i>';
            btn.title = `Cerrar sesión (${usuario.nombre})`;
            btn.onclick = async () => {
                const nombre = capitalizar(usuario.nombre);
                const ok = await confirmarPrisma({
                    inicial: nombre.charAt(0),
                    titulo: '¿Cerrar sesión?',
                    mensaje: `Hola, <strong>${escapeHTML(nombre)}</strong>. Tu carrito seguirá guardado para cuando vuelvas. 🍰`,
                    confirmar: 'Sí, cerrar sesión',
                    cancelar: 'Seguir aquí'
                });
                if (!ok) return;
                localStorage.removeItem('prismaUsuario');
                sessionStorage.removeItem('prismaUsuario');
                mostrarNotificacion(`👋 ¡Hasta pronto, ${nombre}!`);
                actualizarBotonLogin();
            };
        } else {
            btn.innerHTML = '<i class="fas fa-user"></i>';
            btn.title = 'Iniciar sesión';
            btn.onclick = () => { window.location.href = URLS.login; };
        }
    };

    // ============================================
    // 4. RENDERIZADO DE PRODUCTOS
    // ============================================
    const renderProductos = (lista) => {
        const grid = document.getElementById('productosGrid');
        if (!grid) return;
        grid.innerHTML = lista.map(p => `
            <div class="product-card">
                <img src="${imgUrl(p.img)}" alt="${p.nombre}">
                <div class="product-overlay">
                    <button class="btn-buy-now" onclick="abrirModal(${p.id})">
                        <i class="fas fa-cart-shopping"></i> Comprar Ahora
                    </button>
                </div>
                <div class="product-body">
                    <h3>${p.nombre}</h3>
                    <span class="price">$${p.precio.toLocaleString('es-CO')}</span>
                </div>
            </div>
        `).join('');
    };

    const renderTemporada = () => {
        const grid = document.getElementById('temporadaGrid');
        if (!grid) return;
        grid.innerHTML = temporada.map(p => `
            <div class="seasonal-card">
                <img src="${imgUrl(p.img)}" alt="${p.nombre}">
                <div class="seasonal-body">
                    <h3>${p.nombre}</h3>
                    <p>${p.desc}</p>
                    <span class="price">$${p.precio.toLocaleString('es-CO')}</span>
                    <button class="btn-add" onclick="abrirModal(${p.id}, 'temporada')">
                        <i class="fas fa-cart-shopping"></i> Comprar Ahora
                    </button>
                </div>
            </div>
        `).join('');
    };

    // ============================================
    // 5. MODAL DE PRODUCTO
    // ============================================
    let galeriaImagenes = [];
    let galeriaIndice = 0;

    const renderGaleria = (animar = false) => {
        const img = document.getElementById('modalMainImage');
        const dots = document.getElementById('modalDots');
        const thumbs = document.getElementById('modalThumbs');
        if (!img) return;

        const mostrarSrc = () => {
            img.src = galeriaImagenes[galeriaIndice];
            img.style.opacity = 1;
        };

        if (animar) {
            img.style.opacity = 0;
            setTimeout(mostrarSrc, 180);
        } else {
            mostrarSrc();
        }

        if (dots) {
            dots.innerHTML = galeriaImagenes.length > 1
                ? galeriaImagenes.map((_, i) => `<span class="${i === galeriaIndice ? 'active' : ''}"></span>`).join('')
                : '';
        }
        if (thumbs) {
            thumbs.innerHTML = galeriaImagenes.length > 1
                ? galeriaImagenes.map((src, i) => `<div class="modal-thumb ${i === galeriaIndice ? 'active' : ''}" data-index="${i}"><img src="${src}" alt=""></div>`).join('')
                : '';
        }
        document.querySelectorAll('.modal-nav').forEach(btn => btn.classList.toggle('hidden', galeriaImagenes.length <= 1));
    };

    const navegarGaleria = (delta) => {
        if (galeriaImagenes.length <= 1) return;
        galeriaIndice = (galeriaIndice + delta + galeriaImagenes.length) % galeriaImagenes.length;
        renderGaleria(true);
    };

    const abrirModal = (id, origen = 'productos') => {
        const lista = origen === 'productos' ? productos : temporada;
        productoActual = lista.find(p => p.id === id);
        origenActual = origen;
        if (!productoActual) return;

        const precios = {
            personal: productoActual.precio,
            mediano: Math.round(productoActual.precio * 1.8),
            grande: Math.round(productoActual.precio * 2.5)
        };

        tamañoSeleccionado = 'personal';
        galeriaImagenes = (productoActual.imgs && productoActual.imgs.length) ? productoActual.imgs : [productoActual.img];
        galeriaImagenes = galeriaImagenes.map(imgUrl);
        galeriaIndice = 0;
        renderGaleria(false);

        document.getElementById('modalTitle').textContent = productoActual.nombre;
        document.getElementById('modalDescription').textContent = productoActual.desc;
        document.getElementById('modalPrice').textContent = '$' + precios.personal.toLocaleString('es-CO');

        document.querySelectorAll('.size-option').forEach(opt => opt.classList.remove('active'));
        const personalOpt = document.querySelector('.size-option[data-size="personal"]');
        if (personalOpt) personalOpt.classList.add('active');

        document.getElementById('productModal').classList.add('active');
        document.body.style.overflow = 'hidden';
    };

    const cerrarModal = () => {
        const modal = document.getElementById('productModal');
        if (!modal) return;
        modal.classList.remove('active');
        document.body.style.overflow = '';
    };

    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('size-option') && productoActual) {
            document.querySelectorAll('.size-option').forEach(opt => opt.classList.remove('active'));
            e.target.classList.add('active');
            tamañoSeleccionado = e.target.dataset.size;

            const precios = {
                personal: productoActual.precio,
                mediano: Math.round(productoActual.precio * 1.8),
                grande: Math.round(productoActual.precio * 2.5)
            };
            document.getElementById('modalPrice').textContent = '$' + precios[tamañoSeleccionado].toLocaleString('es-CO');
        }
        const thumb = e.target.closest('.modal-thumb');
        if (thumb) {
            galeriaIndice = Number(thumb.dataset.index);
            renderGaleria(true);
        }
        if (e.target.classList.contains('product-modal-overlay')) cerrarModal();
    });

    // ============================================
    // 6. FILTROS DE PRODUCTOS
    // ============================================
    const filtrarProductos = (categoria) => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        const btnActivo = [...document.querySelectorAll('.filter-btn')]
            .find(b => b.textContent.trim().toLowerCase() === categoria || (categoria === 'todos' && b.textContent.trim().toLowerCase() === 'todos'));
        if (btnActivo) btnActivo.classList.add('active');
        renderProductos(categoria === 'todos' ? productos : productos.filter(p => p.categoria === categoria));
    };

    // ============================================
    // 7. ANIMACIONES E INICIALIZACIÓN
    // ============================================
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.product-card, .seasonal-card, .featured-card, .contact-card').forEach(el => {
        observer.observe(el);
    });

    // Efecto de header al hacer scroll
    const header = document.getElementById('header');
    if (header) {
        window.addEventListener('scroll', () => {
            header.classList.toggle('scrolled', window.scrollY > 40);
        });
    }

    // Inicializar componentes según la página
    if (document.getElementById('productosGrid')) {
        renderProductos(productos);
        document.getElementById('searchInput').addEventListener('input', (e) => {
            const filtrados = productos.filter(p => p.nombre.toLowerCase().includes(e.target.value.toLowerCase()));
            renderProductos(filtrados);
        });
    }

    if (document.getElementById('temporadaGrid')) renderTemporada();
    if (document.getElementById('cartItemsList')) renderizarCarrito();

    actualizarContadorCarrito();

    // Formularios
    const reservaForm = document.getElementById('reservaForm');
    if (reservaForm) {
        const inputCantidad = document.getElementById('cantidad');
        const selectPostre = document.getElementById('postre');
        const summaryQty = document.getElementById('summaryQty');
        const summaryPostre = document.getElementById('summaryPostre');
        const btnMenos = document.getElementById('qtyMenos');

        // Campo "¿Cómo quieres tu reserva?" (se agrega solo si la página aún no lo tiene)
        let detalles = document.getElementById('detalles');
        if (!detalles) {
            const grupo = document.createElement('div');
            grupo.className = 'form-group-icon detalles-group';
            grupo.innerHTML = `
                <label for="detalles"><i class="fas fa-pen-to-square"></i> ¿Cómo quieres tu reserva? <small>(opcional)</small></label>
                <textarea id="detalles" name="detalles" rows="4" maxlength="500" placeholder="Cuéntanos los detalles: ocasión, mensaje en el postre, sabores, alergias, hora de entrega, si es para regalo…"></textarea>
                <div class="pz-chips" id="detallesChips"></div>
                <div class="pz-counter"><span id="detallesCount">0</span>/500</div>`;
            const ancla = reservaForm.querySelector('.reservas-summary') || reservaForm.querySelector('[type="submit"]');
            if (ancla && ancla.parentNode) ancla.parentNode.insertBefore(grupo, ancla);
            else reservaForm.appendChild(grupo);
            detalles = document.getElementById('detalles');
        }
        activarDetalles(detalles, document.getElementById('detallesChips'), document.getElementById('detallesCount'));
        const btnMas = document.getElementById('qtyMas');

        const actualizarResumenReserva = () => {
            if (!inputCantidad || !summaryQty) return;
            let cantidad = parseInt(inputCantidad.value, 10);
            if (isNaN(cantidad) || cantidad < 1) cantidad = 1;
            if (cantidad > 50) cantidad = 50;
            inputCantidad.value = cantidad;
            summaryQty.textContent = cantidad;
            if (summaryPostre) {
                summaryPostre.textContent = selectPostre && selectPostre.value ? selectPostre.value : 'selecciona un postre';
            }
        };

        if (btnMenos) btnMenos.addEventListener('click', () => {
            inputCantidad.value = Math.max(1, (parseInt(inputCantidad.value, 10) || 1) - 1);
            actualizarResumenReserva();
        });
        if (btnMas) btnMas.addEventListener('click', () => {
            inputCantidad.value = Math.min(50, (parseInt(inputCantidad.value, 10) || 1) + 1);
            actualizarResumenReserva();
        });
        if (inputCantidad) inputCantidad.addEventListener('input', actualizarResumenReserva);
        if (selectPostre) selectPostre.addEventListener('change', actualizarResumenReserva);
        actualizarResumenReserva();
        const fechaEntrega = document.getElementById('fecha');
        if (fechaEntrega) fechaEntrega.min = hoyISO();

        reservaForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!reservaForm.reportValidity()) return;

            const submitButton = reservaForm.querySelector('[type="submit"]');
            const ventanaWhatsApp = window.open('about:blank', '_blank');
            if (submitButton) submitButton.disabled = true;

            try {
                const respuesta = await fetch(reservaForm.action || window.location.href, {
                    method: 'POST',
                    body: new FormData(reservaForm),
                    headers: { 'Accept': 'application/json' },
                    credentials: 'same-origin',
                });
                const resultado = await respuesta.json();
                if (!respuesta.ok || !resultado.ok) {
                    throw new Error(resultado.error || 'No se pudo registrar la reserva.');
                }

                mostrarNotificacion(resultado.message);
                if (ventanaWhatsApp) {
                    ventanaWhatsApp.location.href = resultado.whatsapp_url;
                } else {
                    window.location.assign(resultado.whatsapp_url);
                }
                reservaForm.reset();
                if (detalles) detalles.dispatchEvent(new Event('input'));
                actualizarResumenReserva();
                if (fechaEntrega) fechaEntrega.min = hoyISO();
            } catch (error) {
                if (ventanaWhatsApp) ventanaWhatsApp.close();
                mostrarNotificacion(error.message || 'Ocurrió un error al enviar la reserva.');
            } finally {
                if (submitButton) submitButton.disabled = false;
            }
        });
    }

    if (document.getElementById('loginForm')) {
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const emailInput = document.getElementById('loginEmail') || e.target.querySelector('input[type="email"]');
            const nombreInput = document.getElementById('nombre');
            const email = emailInput && emailInput.value ? emailInput.value : 'cliente@prisma.com';
            const nombre = nombreInput && nombreInput.value ? nombreInput.value : email.split('@')[0];
            const recordar = document.getElementById('rememberMe');
            const datosUsuario = { email, nombre };

            if (recordar && recordar.checked) {
                localStorage.setItem('prismaUsuario', JSON.stringify(datosUsuario));
            } else {
                sessionStorage.setItem('prismaUsuario', JSON.stringify(datosUsuario));
            }

            mostrarNotificacion(`✅ ¡Bienvenido, ${nombre}!`);
            const destino = sessionStorage.getItem('redirectAfterLogin');
            sessionStorage.removeItem('redirectAfterLogin');
            setTimeout(() => { window.location.href = destino || URLS.inicio; }, 900);
        });
    }

    if (document.getElementById('registroForm')) {
        document.getElementById('registroForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const nombre = document.getElementById('regNombre').value;
            const email = document.getElementById('regEmail').value;
            const password = document.getElementById('regPassword').value;
            const password2 = document.getElementById('regPassword2').value;
            const inputPassword2 = document.getElementById('regPassword2');
            const error = document.getElementById('regPasswordError');

            if (password !== password2) {
                inputPassword2.classList.add('input-error');
                error.style.display = 'block';
                return;
            }
            inputPassword2.classList.remove('input-error');
            error.style.display = 'none';

            const datosUsuario = { email, nombre };
            localStorage.setItem('prismaUsuario', JSON.stringify(datosUsuario));

            mostrarNotificacion(`✅ ¡Cuenta creada! Bienvenido, ${nombre}`);
            const destino = sessionStorage.getItem('redirectAfterLogin');
            sessionStorage.removeItem('redirectAfterLogin');
            setTimeout(() => { window.location.href = destino || URLS.inicio; }, 900);
        });
    }

    if (document.getElementById('recuperarForm')) {
        document.getElementById('recuperarForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const password = document.getElementById('nuevaPassword').value;
            const password2 = document.getElementById('nuevaPassword2').value;
            const inputPassword2 = document.getElementById('nuevaPassword2');
            const error = document.getElementById('recuperarPasswordError');

            if (password !== password2) {
                inputPassword2.classList.add('input-error');
                error.style.display = 'block';
                return;
            }
            inputPassword2.classList.remove('input-error');
            error.style.display = 'none';

            mostrarNotificacion('✅ Tu contraseña se actualizó correctamente');
            setTimeout(() => { window.location.href = URLS.login; }, 1000);
        });
    }

    actualizarBotonLogin();
    construirMenuMovil();
    window.toggleMobileMenu = () => {
        const nav = document.getElementById('navMenu');
        if (nav) setMenuMovil(!nav.classList.contains('mobile-open'));
    };

    const authHint = document.getElementById('authHint');
    if (authHint && sessionStorage.getItem('redirectAfterLogin')) {
        authHint.textContent = '🔒 Inicia sesión para finalizar tu reserva';
        authHint.style.display = 'block';
    }

    // Exponer al ámbito global lo que necesitan los onclick del HTML
    window.agregarAlCarrito = agregarAlCarrito;
    window.agregarDesdeModal = agregarDesdeModal;
    window.cambiarCantidad = cambiarCantidad;
    window.eliminarItem = eliminarItem;
    window.checkout = checkout;
    window.abrirModal = abrirModal;
    window.cerrarModal = cerrarModal;
    window.navegarGaleria = navegarGaleria;
    window.filtrarProductos = filtrarProductos;
});
