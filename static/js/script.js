document.addEventListener('DOMContentLoaded', () => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ============================================
    // 0. RUTAS DE DJANGO (definidas en base_prisma.html)
    // ============================================
    const CFG = window.PRISMA || {};
    const URLS = CFG.urls || {};
    const IMG_BASE = CFG.imgBase || '';
    // Convierte 'postre_1.jpeg' en '/static/img/postre_1.jpeg'.
    // Si ya es una URL absoluta (p.ej. una imagen subida a /media/...), se deja tal cual.
    const imgUrl = (nombre) => (/^(https?:)?\//.test(nombre || '') ? nombre : IMG_BASE + encodeURI(nombre || ''));

    // ============================================
    // 1. CONFIGURACIÓN Y DATOS (productos reales desde la base de datos)
    // ============================================
    const leerDatosJSON = (id) => {
        const el = document.getElementById(id);
        if (!el) return [];
        try {
            return JSON.parse(el.textContent) || [];
        } catch (e) {
            return [];
        }
    };

    const productos = leerDatosJSON('productos-data');
    const temporada = leerDatosJSON('temporada-data');

    // ============================================
    // 1-B. REVELADO AL HACER SCROLL
    // (definido aquí porque el grid de productos/temporada se arma con
    // JavaScript: hay que poder observar tarjetas nuevas cada vez que se
    // vuelven a pintar, por ejemplo al buscar o filtrar)
    // ============================================
    let observadorRevelado = null;
    if ('IntersectionObserver' in window && !prefersReducedMotion) {
        observadorRevelado = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in', 'is-visible');
                    observadorRevelado.unobserve(entry.target);
                }
            });
        }, { threshold: 0.02, rootMargin: '0px 0px 80px 0px' });
    }
    const observarRevelado = (elementos) => {
        if (!elementos || !elementos.length) return;
        const vh = window.innerHeight || document.documentElement.clientHeight;
        elementos.forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.top < vh + 60 && rect.bottom > -60) {
                el.classList.add('motion-reveal', 'animate-in', 'is-visible');
            } else if (observadorRevelado) {
                el.classList.add('motion-reveal');
                observadorRevelado.observe(el);
            } else {
                el.classList.add('motion-reveal', 'animate-in', 'is-visible');
            }
        });
    };

    const carousel = document.getElementById('homeCarousel');
    if (carousel) {
        const slides = [...carousel.querySelectorAll('.hero-slide')];
        const dots = [...carousel.querySelectorAll('.hero-carousel-dot')];
        const autoplayToggle = carousel.querySelector('.hero-carousel-toggle');
        let currentSlide = 0;
        let timer = null;
        let isPaused = false;
        let isInView = true;

        const showSlide = (nextSlide) => {
            currentSlide = (nextSlide + slides.length) % slides.length;
            const image = slides[currentSlide].querySelector('.hero-slide-image');
            if (image && image.dataset.src) {
                image.src = image.dataset.src;
                image.loading = 'eager';
                image.fetchPriority = 'high';
                delete image.dataset.src;
            }
            slides.forEach((slide, index) => {
                const isActive = index === currentSlide;
                slide.classList.toggle('is-active', isActive);
                slide.setAttribute('aria-hidden', String(!isActive));
            });
            dots.forEach((dot, index) => {
                const isActive = index === currentSlide;
                dot.classList.toggle('is-active', isActive);
                dot.setAttribute('aria-pressed', String(isActive));
            });
        };

        const preloadNextSlide = () => {
            const nextImage = slides[(currentSlide + 1) % slides.length].querySelector('.hero-slide-image');
            if (!nextImage || !nextImage.dataset.src) return;
            nextImage.src = nextImage.dataset.src;
            nextImage.loading = 'eager';
            nextImage.fetchPriority = 'low';
            delete nextImage.dataset.src;
        };

        const stopAutoplay = () => {
            window.clearInterval(timer);
            timer = null;
        };
        const startAutoplay = () => {
            stopAutoplay();
            if (!isPaused && isInView && !prefersReducedMotion && !document.hidden && slides.length > 1) {
                preloadNextSlide();
                timer = window.setInterval(() => {
                    showSlide(currentSlide + 1);
                    preloadNextSlide();
                }, 6000);
            }
        };

        if (autoplayToggle) {
            const autoplayIcon = autoplayToggle.querySelector('i');
            const updateAutoplayToggle = () => {
                const label = isPaused ? 'Reanudar carrusel' : 'Pausar carrusel';
                autoplayToggle.setAttribute('aria-label', label);
                autoplayToggle.title = label;
                autoplayToggle.setAttribute('aria-pressed', String(isPaused));
                if (autoplayIcon) {
                    autoplayIcon.classList.toggle('fa-play', isPaused);
                    autoplayIcon.classList.toggle('fa-pause', !isPaused);
                }
            };

            autoplayToggle.hidden = prefersReducedMotion || slides.length < 2;
            autoplayToggle.addEventListener('click', () => {
                isPaused = !isPaused;
                updateAutoplayToggle();
                if (isPaused) stopAutoplay();
                else startAutoplay();
            });
        }

        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                showSlide(index);
                startAutoplay();
            });
        });
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                stopAutoplay();
                return;
            }
            startAutoplay();
        });
        if ('IntersectionObserver' in window) {
            const carouselObserver = new IntersectionObserver(([entry]) => {
                isInView = entry.isIntersecting;
                if (isInView) startAutoplay();
                else stopAutoplay();
            }, { threshold: 0.1 });
            carouselObserver.observe(carousel);
        }
        window.addEventListener('pagehide', () => {
            stopAutoplay();
        });
        window.addEventListener('pageshow', () => {
            startAutoplay();
        });
        startAutoplay();
    }

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

    const mostrarNotificacionCarrito = (titulo, mensaje) => {
        const toast = document.createElement('div');
        toast.className = 'toast-notification cart-toast';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');

        const contenido = document.createElement('span');
        contenido.className = 'cart-toast-content';
        const encabezado = document.createElement('strong');
        encabezado.textContent = titulo;
        const detalle = document.createElement('span');
        detalle.textContent = mensaje;
        contenido.append(encabezado, detalle);

        toast.append(contenido);
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3600);
    };

    const mostrarAccesoCarrito = () => {
        const toast = document.createElement('div');
        toast.className = 'cart-toast-action';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');

        const link = document.createElement('a');
        link.className = 'cart-toast-action-link';
        link.href = URLS.carrito || '/carrito/';
        link.setAttribute('aria-label', `Ir al carrito, ${carrito.reduce((sum, item) => sum + item.cantidad, 0)} productos`);

        const icon = document.createElement('i');
        icon.className = 'fas fa-cart-shopping';
        icon.setAttribute('aria-hidden', 'true');

        const label = document.createElement('span');
        label.textContent = 'Ir al carrito';

        const count = document.createElement('span');
        count.className = 'cart-toast-action-count';
        count.textContent = carrito.reduce((sum, item) => sum + item.cantidad, 0);
        count.setAttribute('aria-hidden', 'true');

        link.append(icon, label, count);
        toast.append(link);
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3600);
    };


    const escapeHTML = (t) => String(t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const capitalizar = (t) => t ? t.charAt(0).toUpperCase() + t.slice(1) : t;

    const hoyISO = () => {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    };

    // "2026-10-03" -> "03/10/2026 (sábado)"
    // ---------- Diálogos Prisma (reemplazan alert / confirm / prompt) ----------
    const abrirModalPrisma = ({ claseExtra = '', html, alMontar, alAceptar }) => new Promise((resolve) => {
        const previo = document.activeElement;
        const overlay = document.createElement('div');
        overlay.className = 'pz-overlay';
        if (claseExtra.split(/\s+/).includes('cart-clear-confirmation')) {
            overlay.classList.add('cart-clear-overlay');
        }
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

    const confirmarPrisma = ({ icono = 'fa-circle-question', inicial = '', titulo, mensaje, confirmar = 'Aceptar', cancelar = 'Cancelar', claseExtra = '' }) =>
        abrirModalPrisma({
            claseExtra: `pz-confirm ${claseExtra}`,
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
                btnBurger.setAttribute('aria-label', abierto ? 'Cerrar menú' : 'Abrir menú');
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
        mostrarAccesoCarrito();
    };

    const agregarDesdeModal = () => {
        if (!productoActual) return;
        agregarAlCarrito(productoActual.id, origenActual, tamañoSeleccionado);
        cerrarModal();
    };

    const cambiarCantidad = (id, delta, tamaño = 'personal') => {
        const item = carrito.find(i => i.id === id && i.tamaño === tamaño);
        if (!item) return;
        if (item.cantidad + delta <= 0) {
            eliminarItem(id, tamaño);
            return;
        }
        item.cantidad += delta;
        localStorage.setItem('prismaCarrito', JSON.stringify(carrito));
        actualizarContadorCarrito();
        renderizarCarrito();
    };

    const eliminarItem = async (id, tamaño = 'personal') => {
        const item = carrito.find(i => i.id === id && i.tamaño === tamaño);
        if (!item) return;

        const confirmado = await confirmarPrisma({
            icono: 'fa-trash-can',
            titulo: '¿Eliminar producto?',
            mensaje: `¿Estás seguro de que quieres eliminar <strong>${escapeHTML(item.nombre)}</strong> del carrito? Esta acción no se puede deshacer.`,
            confirmar: 'Eliminar producto',
            cancelar: 'Cancelar',
            claseExtra: 'cart-clear-confirmation'
        });
        if (!confirmado) return;

        carrito = carrito.filter(i => i !== item);
        localStorage.setItem('prismaCarrito', JSON.stringify(carrito));
        actualizarContadorCarrito();
        renderizarCarrito();
        mostrarNotificacionCarrito('¡Producto eliminado!', `${item.nombre} se eliminó del carrito`);
    };

    const vaciarCarrito = async () => {
        if (carrito.length === 0) return;

        const confirmado = await confirmarPrisma({
            icono: 'fa-trash-can',
            titulo: 'Vaciar carrito',
            mensaje: '¿Estás seguro de que quieres eliminar todos los productos del carrito? Esta acción no se puede deshacer.',
            confirmar: 'Vaciar carrito',
            cancelar: 'Cancelar',
            claseExtra: 'cart-clear-confirmation'
        });
        if (!confirmado) return;

        carrito = [];
        localStorage.setItem('prismaCarrito', JSON.stringify(carrito));
        actualizarContadorCarrito();
        renderizarCarrito();
        mostrarNotificacionCarrito('Carrito vaciado', 'Se eliminaron todos los productos.');
    };

    const renderizarCarrito = () => {
        const container = document.getElementById('cartItemsList');
        if (!container) return;
        const botonPago = document.getElementById('proceedToPayment');
        if (botonPago) botonPago.disabled = carrito.length === 0;
        const botonVaciar = document.getElementById('clearCartButton');
        if (botonVaciar) botonVaciar.hidden = carrito.length === 0;

        if (carrito.length === 0) {
            container.innerHTML = `
                <div class="empty-cart">
                    <span class="empty-cart-icon"><i class="fas fa-bag-shopping" aria-hidden="true"></i></span>
                    <span class="empty-cart-eyebrow">Aún no hay productos</span>
                    <h3>Tu próxima elección te espera</h3>
                    <p>Explora nuestros postres y agrega tus favoritos al carrito.</p>
                    <a class="empty-cart-link" href="${escapeHTML(URLS.productos || '/productos/catalogo/')}">
                        Explorar productos <i class="fas fa-arrow-right" aria-hidden="true"></i>
                    </a>
                </div>`;
            document.getElementById('subtotal').textContent = '$0';
            document.getElementById('total').textContent = '$0';
            document.getElementById('cartItemsCount').textContent = '0 productos';
            document.getElementById('cartSummaryCount').textContent = '0 artículos';
            const checkoutSection = document.getElementById('checkoutSection');
            if (checkoutSection) checkoutSection.hidden = true;
            return;
        }

        let subtotal = 0;
        let totalUnidades = 0;
        container.innerHTML = carrito.map(item => {
            subtotal += item.precio * item.cantidad;
            totalUnidades += item.cantidad;
            const detalleTamaño = item.tamaño !== 'personal'
                ? `<p class="item-size">Tamaño: ${escapeHTML(item.tamaño)}</p>`
                : '';
            return `
                <div class="cart-item">
                    <img src="${imgUrl(item.img)}" alt="${item.nombre}">
                    <div class="cart-item-info">
                        <div class="cart-item-details">
                            <h4>${escapeHTML(item.nombre)}</h4>
                            ${detalleTamaño}
                        </div>
                        <p class="item-price">$${item.precio.toLocaleString('es-CO')}</p>
                        <div class="cart-item-actions">
                            <button class="qty-btn" onclick="cambiarCantidad(${item.id}, -1, '${escapeHTML(item.tamaño)}')" aria-label="Disminuir cantidad de ${escapeHTML(item.nombre)}">−</button>
                            <span>${item.cantidad}</span>
                            <button class="qty-btn" onclick="cambiarCantidad(${item.id}, 1, '${escapeHTML(item.tamaño)}')" aria-label="Aumentar cantidad de ${escapeHTML(item.nombre)}">+</button>
                            <button class="cart-item-remove" onclick="eliminarItem(${item.id}, '${escapeHTML(item.tamaño)}')" title="Quitar" aria-label="Eliminar ${escapeHTML(item.nombre)} del carrito"><i class="fas fa-trash" aria-hidden="true"></i></button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        document.getElementById('subtotal').textContent = '$' + subtotal.toLocaleString('es-CO');
        document.getElementById('total').textContent = '$' + subtotal.toLocaleString('es-CO');
        const etiquetaUnidades = `${totalUnidades} ${totalUnidades === 1 ? 'artículo' : 'artículos'}`;
        document.getElementById('cartItemsCount').textContent = `${totalUnidades} ${totalUnidades === 1 ? 'producto' : 'productos'}`;
        document.getElementById('cartSummaryCount').textContent = etiquetaUnidades;
    };

    const checkout = () => {
        if (carrito.length === 0) return;
        window.location.assign(URLS.reservas || '/reserva/');
    };

    // ============================================
    // 4. RENDERIZADO DE PRODUCTOS
    // ============================================
    const renderProductos = (lista) => {
        const grid = document.getElementById('productosGrid');
        if (!grid) return;
        if (!lista.length) {
            grid.innerHTML = '<p class="product-search-empty">No encontramos postres con esa búsqueda. Prueba con otro nombre o categoría.</p>';
            return;
        }
        grid.innerHTML = lista.map(p => `
            <div class="product-card">
                <img src="${imgUrl(p.img)}" alt="${p.nombre}" loading="lazy" decoding="async">
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
        observarRevelado(grid.querySelectorAll('.product-card'));
    };

    const renderTemporada = () => {
        const grid = document.getElementById('temporadaGrid');
        if (!grid) return;
        grid.innerHTML = temporada.map(p => `
            <div class="seasonal-card">
                <img src="${imgUrl(p.img)}" alt="${p.nombre}" loading="lazy" decoding="async">
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
        observarRevelado(grid.querySelectorAll('.seasonal-card'));
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
            setTimeout(mostrarSrc, 90);
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
    let categoriaActiva = 'todos';
    let textoBusqueda = '';
    const normalizarBusqueda = (texto) => texto
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLocaleLowerCase('es-CO')
        .trim();
    const actualizarProductosFiltrados = () => {
        const termino = normalizarBusqueda(textoBusqueda);
        const filtrados = productos.filter(producto => {
            const coincideCategoria = categoriaActiva === 'todos' || producto.categoria === categoriaActiva;
            const contenido = normalizarBusqueda(`${producto.nombre} ${producto.categoria} ${producto.desc || ''}`);
            return coincideCategoria && (!termino || contenido.includes(termino));
        });
        renderProductos(filtrados);
    };
    const filtrarProductos = (categoria) => {
        categoriaActiva = categoria;
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        const btnActivo = document.querySelector(`.filter-btn[data-categoria="${categoria}"]`);
        if (btnActivo) btnActivo.classList.add('active');
        actualizarProductosFiltrados();
    };

    // ============================================
    // 7. ANIMACIONES E INICIALIZACIÓN
    // ============================================
    // .product-card y .seasonal-card se observan desde renderProductos() y
    // renderTemporada() (se pintan por JS); aquí solo falta lo que ya está
    // en el HTML desde el primer render del servidor.
    observarRevelado(document.querySelectorAll(
        '.reveal-entry, .section-title, .page-header, .auth-form-container, .auth-image, ' +
        '.featured-card, .contact-card, .contact-panel, .contact-channel-section, ' +
        '.social-channel-section, .contact-map-note, .info-item, .footer-section, ' +
        '.footer-bottom, [data-reveal]',
    ));

    // Efecto de header al hacer scroll
    const header = document.getElementById('header');
    if (header) {
        let scrollTicking = false;
        window.addEventListener('scroll', () => {
            if (scrollTicking) return;
            scrollTicking = true;
            // requestAnimationFrame evita recalcular en cada evento de scroll
            // (pueden ser decenas por segundo) y lo alinea con el repintado
            // del navegador: más fluido y más barato en CPU.
            requestAnimationFrame(() => {
                header.classList.toggle('scrolled', window.scrollY > 40);
                scrollTicking = false;
            });
        }, { passive: true });
    }

    // Inicializar componentes según la página
    if (document.getElementById('productosGrid')) {
        const sInput = document.getElementById('searchInput');
        if (sInput) {
            textoBusqueda = sInput.value;
            sInput.addEventListener('input', (e) => {
                textoBusqueda = e.target.value;
                actualizarProductosFiltrados();
            });
        }
        actualizarProductosFiltrados();
    }

    if (document.getElementById('temporadaGrid')) renderTemporada();
    if (document.getElementById('cartItemsList')) renderizarCarrito();

    actualizarContadorCarrito();

    const formatearCOP = (valor) => new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        maximumFractionDigits: 0,
    }).format(valor);

    // Helper Confetti Animado
    const lanzarConfetti = (duracionMs = 2500) => {
        if (typeof confetti === 'function') {
            confetti({
                particleCount: 120,
                spread: 80,
                origin: { y: 0.6 },
                colors: ['#df9f28', '#d97885', '#faecd3', '#2d8a5e', '#b87e14']
            });
            const fin = Date.now() + duracionMs;
            const intervalo = setInterval(() => {
                if (Date.now() > fin) return clearInterval(intervalo);
                confetti({
                    particleCount: 25,
                    angle: 60,
                    spread: 55,
                    origin: { x: 0 },
                    colors: ['#df9f28', '#d97885', '#f8dfcf']
                });
                confetti({
                    particleCount: 25,
                    angle: 120,
                    spread: 55,
                    origin: { x: 1 },
                    colors: ['#df9f28', '#d97885', '#faecd3']
                });
            }, 300);
        }
    };

    // Formularios y Módulo de Reservas
    const reservaForm = document.getElementById('reservaForm');
    if (reservaForm) {
        const reservaProductosList = document.getElementById('reservaProductosList');
        const reservaProductoCards = [...reservaForm.querySelectorAll('[data-reserva-producto-slot]')];
        const reservationTimeInputs = [...reservaForm.querySelectorAll('input[name="hora"]')];
        const addReservaProducto = document.getElementById('addReservaProducto');
        const reservaProductosHint = document.getElementById('reservaProductosHint');
        const modalidadCardMesa = document.getElementById('modalityCardMesa');
        const modalidadCardLlevar = document.getElementById('modalityCardLlevar');
        const groupNumeroPersonas = document.getElementById('groupNumeroPersonas');
        const takeawayAuthNotice = document.getElementById('takeawayAuthNotice');
        const numeroPersonasInput = document.getElementById('numero_personas');
        const totalNoteText = document.getElementById('totalNoteText');
        const btnSubmitReserva = document.getElementById('btnSubmitReserva');
        const paymentModalOverlay = document.getElementById('paymentModalOverlay');

        // Función para actualizar cálculos de productos
        const actualizarProductosReserva = () => {
            const visibles = reservaProductoCards.filter(card => card.classList.contains('is-visible'));
            const seleccionados = visibles.filter(card => card.querySelector('select')?.value);
            let totalEstimado = 0;
            visibles.forEach(card => {
                const select = card.querySelector('select');
                if (!select) return;
                const cantidad = Number(card.querySelector('input[type="number"]')?.value) || 0;
                const precio = Number(select.selectedOptions[0]?.dataset.price) || 0;
                const subtotal = precio * cantidad;
                totalEstimado += subtotal;
                const subtotalEl = card.querySelector('[data-reserva-line-total]');
                if (subtotalEl) {
                    subtotalEl.textContent = select.value
                        ? `${formatearCOP(precio)} c/u · Subtotal: ${formatearCOP(subtotal)}`
                        : '';
                }
                select.required = seleccionados.length === 0 && card === visibles[0];
                const removeButton = card.querySelector('[data-remove-reserva-producto]');
                if (removeButton) removeButton.hidden = visibles.length === 1;
            });
            const totalEl = document.getElementById('reservaTotalEstimate');
            if (totalEl) totalEl.textContent = formatearCOP(totalEstimado);
            if (addReservaProducto) {
                const quedaEspacio = reservaProductoCards.some(card => !card.classList.contains('is-visible'));
                addReservaProducto.hidden = !quedaEspacio;
                addReservaProducto.disabled = !quedaEspacio;
            }
            if (reservaProductosHint) {
                const cantidad = seleccionados.length;
                reservaProductosHint.textContent = cantidad
                    ? `${cantidad} postre${cantidad === 1 ? '' : 's'} seleccionado${cantidad === 1 ? '' : 's'} para tu reserva.`
                    : 'Elige al menos un postre para continuar.';
            }

        };

        if (reservaProductosList && reservaProductoCards.length) {
            reservaProductosList.classList.add('is-interactive');

            reservaProductoCards.forEach(card => {
                const select = card.querySelector('select');
                if (select) {
                    select.required = false;
                    select.addEventListener('change', actualizarProductosReserva);
                }
                const numInput = card.querySelector('input[type="number"]');
                if (numInput) numInput.addEventListener('input', actualizarProductosReserva);
                const removeButton = card.querySelector('[data-remove-reserva-producto]');
                if (removeButton) {
                    removeButton.addEventListener('click', () => {
                        if (select) select.value = '';
                        if (numInput) numInput.value = '1';
                        card.classList.remove('is-visible');
                        actualizarProductosReserva();
                    });
                }
            });

            if (addReservaProducto) {
                addReservaProducto.hidden = false;
                addReservaProducto.addEventListener('click', () => {
                    const siguiente = reservaProductoCards.find(card => !card.classList.contains('is-visible'));
                    if (!siguiente) return;
                    siguiente.classList.add('is-visible');
                    actualizarProductosReserva();
                    siguiente.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    siguiente.querySelector('select')?.focus({ preventScroll: true });
                });
            }
            actualizarProductosReserva();
        }

        // Stepper Quantity Buttons (+ / -)
        document.querySelectorAll('.qty-btn-minus').forEach(btn => {
            btn.addEventListener('click', () => {
                const target = document.getElementById(btn.dataset.target);
                if (target && Number(target.value) > 1) {
                    target.value = Number(target.value) - 1;
                    actualizarProductosReserva();
                }
            });
        });
        document.querySelectorAll('.qty-btn-plus').forEach(btn => {
            btn.addEventListener('click', () => {
                const target = document.getElementById(btn.dataset.target);
                if (target && Number(target.value) < 50) {
                    target.value = Number(target.value) + 1;
                    actualizarProductosReserva();
                }
            });
        });

        // Modality Switcher (Mesa vs Para Llevar)
        const actualizarModalidad = (modalidad) => {
            const esMesa = modalidad === 'Mesa';
            if (modalidadCardMesa && modalidadCardLlevar) {
                if (esMesa) {
                    modalidadCardMesa.classList.add('is-selected');
                    modalidadCardLlevar.classList.remove('is-selected');
                    const radioMesa = document.getElementById('modalidad_mesa');
                    if (radioMesa) radioMesa.checked = true;
                } else {
                    modalidadCardLlevar.classList.add('is-selected');
                    modalidadCardMesa.classList.remove('is-selected');
                    const radioLlevar = document.getElementById('modalidad_llevar');
                    if (radioLlevar) radioLlevar.checked = true;
                }
            }

            if (groupNumeroPersonas) {
                groupNumeroPersonas.hidden = !esMesa;
            }
            if (numeroPersonasInput) {
                numeroPersonasInput.required = esMesa;
            }

            if (takeawayAuthNotice) {
                takeawayAuthNotice.hidden = esMesa;
            }

            if (totalNoteText) {
                totalNoteText.textContent = esMesa
                    ? 'Las mesas no requieren pago anticipado. Te recibimos en nuestro local.'
                    : 'Para llevar requiere inicio de sesión y pago anticipado.';
            }

            if (btnSubmitReserva) {
                const btnText = btnSubmitReserva.querySelector('.btn-text');
                if (btnText) {
                    btnText.textContent = esMesa
                        ? 'Confirmar mi Reserva de Mesa'
                        : 'Registrar y Continuar al Pago Seguro';
                }
            }
        };

        if (modalidadCardMesa) {
            modalidadCardMesa.addEventListener('click', () => actualizarModalidad('Mesa'));
        }
        if (modalidadCardLlevar) {
            modalidadCardLlevar.addEventListener('click', () => actualizarModalidad('Para llevar'));
        }

        const tipoReservaSelect = document.getElementById('tipo_reserva');
        if (tipoReservaSelect) {
            tipoReservaSelect.addEventListener('change', () => actualizarModalidad(tipoReservaSelect.value));
        }

        // Guests Pills
        document.querySelectorAll('.guest-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                document.querySelectorAll('.guest-pill').forEach(p => p.classList.remove('is-active'));
                pill.classList.add('is-active');
                if (numeroPersonasInput) {
                    numeroPersonasInput.value = pill.dataset.guests;
                }
            });
        });

        const actualizarHorarioSeleccionado = () => {
            reservationTimeInputs.forEach(input => {
                input.closest('.reservation-time-option')?.classList.toggle('is-selected', input.checked);
            });
        };
        reservationTimeInputs.forEach(input => {
            input.addEventListener('change', actualizarHorarioSeleccionado);
        });

        // Chips para indicaciones
        document.querySelectorAll('.reserva-chip-btn').forEach(chip => {
            chip.addEventListener('click', () => {
                const detallesTextarea = document.getElementById('detalles');
                if (!detallesTextarea) return;
                const texto = chip.dataset.text;
                const previo = detallesTextarea.value.trim();
                detallesTextarea.value = (previo ? previo + '\n• ' : '• ') + texto;
                detallesTextarea.focus();
            });
        });

        // Restablecer borrador si el usuario inició sesión recientemente
        const borradorJSON = sessionStorage.getItem('reserva_draft');
        if (borradorJSON) {
            try {
                const borrador = JSON.parse(borradorJSON);
                if (borrador.nombre && document.getElementById('nombre')) document.getElementById('nombre').value = borrador.nombre;
                if (borrador.telefono && document.getElementById('telefono')) document.getElementById('telefono').value = borrador.telefono;
                if (borrador.fecha && document.getElementById('fecha')) document.getElementById('fecha').value = borrador.fecha;
                if (borrador.hora) {
                    const horaBorrador = reservationTimeInputs.find(input => input.value === borrador.hora);
                    if (horaBorrador) {
                        horaBorrador.checked = true;
                        actualizarHorarioSeleccionado();
                    }
                }
                if (borrador.detalles && document.getElementById('detalles')) document.getElementById('detalles').value = borrador.detalles;
                if (borrador.tipo_reserva) actualizarModalidad(borrador.tipo_reserva);
                sessionStorage.removeItem('reserva_draft');
            } catch (err) {}
        }

        // Date input min = hoy
        const fechaReserva = document.getElementById('fecha');
        if (fechaReserva) fechaReserva.min = hoyISO();

        // Control del Modal de Pago
        const abrirModalPago = (reservaId, totalTexto) => {
            if (!paymentModalOverlay) return;
            document.getElementById('payModalReservaId').textContent = `Reserva #${reservaId}`;
            document.getElementById('payModalTotal').textContent = totalTexto;
            document.getElementById('payActionReservaId').value = reservaId;
            paymentModalOverlay.hidden = false;
        };

        const cerrarModalPago = () => {
            if (paymentModalOverlay) paymentModalOverlay.hidden = true;
        };

        const btnClosePaymentModal = document.getElementById('btnClosePaymentModal');
        if (btnClosePaymentModal) btnClosePaymentModal.addEventListener('click', cerrarModalPago);

        // Pestañas de Métodos de Pago
        document.querySelectorAll('.payment-method-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.payment-method-tab').forEach(t => t.classList.remove('is-active'));
                tab.classList.add('is-active');
                const metodo = tab.dataset.method;
                const hiddenMetodo = document.getElementById('selectedMetodoPago');
                if (hiddenMetodo) hiddenMetodo.value = metodo;

                document.querySelectorAll('.payment-method-details').forEach(det => det.hidden = true);
                const activeDetails = document.getElementById(`method${metodo}Details`);
                if (activeDetails) activeDetails.hidden = false;
            });
        });

        // Envío del Formulario de Pago desde el Modal
        const paymentExecutionForm = document.getElementById('paymentExecutionForm');
        if (paymentExecutionForm) {
            paymentExecutionForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const reservaId = document.getElementById('payActionReservaId')?.value;
                if (!reservaId) return;

                const btnSubmitPayment = document.getElementById('btnSubmitPayment');
                if (btnSubmitPayment) {
                    btnSubmitPayment.disabled = true;
                    btnSubmitPayment.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verificando pago seguro...';
                }

                try {
                    const formData = new FormData(paymentExecutionForm);
                    const respuesta = await fetch(`/reserva/pagar/${reservaId}/`, {
                        method: 'POST',
                        body: formData,
                        headers: { 'Accept': 'application/json' },
                        credentials: 'same-origin',
                    });
                    const resultado = await respuesta.json();
                    if (!respuesta.ok || !resultado.ok) {
                        throw new Error(resultado.error || 'No se pudo procesar el pago.');
                    }

                    cerrarModalPago();
                    lanzarConfetti(3500);

                    // Mensaje lindo y animado tras completar el pago
                    if (window.Swal) {
                        await Swal.fire({
                            customClass: {
                                popup: 'sweet-celebration-dialog',
                                confirmButton: 'luxury-btn-gold'
                            },
                            icon: 'success',
                            title: resultado.title || '¡Pago Recibido con Éxito! 🎉🍰',
                            html: `
                                <div class="sweet-payment-celebration">
                                    <div class="cake-pulse-icon">🍰💖</div>
                                    <p class="sweet-message-text">${escapeHTML(resultado.message)}</p>
                                    <div class="sweet-receipt-pill">
                                        <strong>Reserva #${escapeHTML(resultado.reservation_id)}</strong> · Total Pagado: <strong>${escapeHTML(resultado.total)} COP</strong>
                                    </div>
                                    <p class="sweet-pickup-info"><i class="fas fa-calendar-check"></i> Fecha de entrega: <strong>${escapeHTML(resultado.fecha_recogida)}</strong> a las <strong>${escapeHTML(resultado.hora_recogida)}</strong></p>
                                </div>
                            `,
                            showCancelButton: true,
                            confirmButtonText: '<i class="fas fa-receipt"></i> Ver Comprobante y Pedido',
                            cancelButtonText: '<i class="fab fa-whatsapp"></i> Hablar por WhatsApp',
                            buttonsStyling: false
                        }).then(result => {
                            if (result.isConfirmed && resultado.next_url) {
                                window.location.assign(resultado.next_url);
                            } else {
                                window.open(`https://wa.me/${window.PRISMA?.whatsapp || '573118689862'}?text=${encodeURIComponent('Hola Prisma 👋 Ya completé el pago de mi pedido #' + resultado.reservation_id)}`, '_blank');
                                if (resultado.next_url) window.location.assign(resultado.next_url);
                            }
                        });
                    }
                } catch (err) {
                    if (window.Swal) {
                        Swal.fire({
                            icon: 'error',
                            title: 'Error en el pago',
                            text: err.message || 'No se pudo completar el pago.',
                            confirmButtonColor: '#df9f28'
                        });
                    }
                } finally {
                    if (btnSubmitPayment) {
                        btnSubmitPayment.disabled = false;
                        btnSubmitPayment.innerHTML = '<i class="fas fa-check-circle"></i> Completar Pago Ahora';
                    }
                }
            });
        }

        // Envío AJAX del formulario de reserva principal
        if (reservaForm.dataset.reservaAjax === 'true') {
            reservaForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                if (reservaForm.dataset.submitted === 'true') return;

                const modalidadElegida = document.querySelector('input[name="tipo_reserva"]:checked')?.value || document.getElementById('tipo_reserva')?.value || 'Mesa';
                const usuarioLogueado = reservaForm.dataset.userLoggedIn === 'true';

                // REGLA CLAVE: Solo si quiere reservar postre para llevar debe iniciar sesión
                if (modalidadElegida === 'Para llevar' && !usuarioLogueado) {
                    // Guardar borrador en sessionStorage para que no pierda lo seleccionado
                    const draft = {
                        nombre: document.getElementById('nombre')?.value || '',
                        telefono: document.getElementById('telefono')?.value || '',
                        fecha: document.getElementById('fecha')?.value || '',
                        hora: reservaForm.querySelector('input[name="hora"]:checked')?.value || '',
                        detalles: document.getElementById('detalles')?.value || '',
                        tipo_reserva: 'Para llevar'
                    };
                    sessionStorage.setItem('reserva_draft', JSON.stringify(draft));

                    if (window.Swal) {
                        Swal.fire({
                            icon: 'info',
                            title: '¡Casi Listo para tu Pedido! 🍰🔒',
                            html: `
                                <p style="font-size:1.05rem; color:#4a3435; line-height:1.5;">
                                    Para reservar tu postre <strong>para llevar</strong> es necesario <strong>iniciar sesión</strong> o registrarte para completar tu pago seguro.
                                </p>
                                <p class="text-muted small">
                                    ¡Tus datos y postres seleccionados han sido guardados para que continúes sin interrupción!
                                </p>
                            `,
                            showDenyButton: true,
                            showCancelButton: true,
                            confirmButtonText: '<i class="fas fa-sign-in-alt"></i> Iniciar Sesión',
                            denyButtonText: '<i class="fas fa-user-plus"></i> Crear Cuenta',
                            cancelButtonText: 'Seguir editando',
                            confirmButtonColor: '#df9f28',
                            denyButtonColor: '#c45d6e',
                            cancelButtonColor: '#8a8a8a',
                        }).then(r => {
                            if (r.isConfirmed) {
                                window.location.assign(window.PRISMA?.urls?.login ? `${window.PRISMA.urls.login}?next=${encodeURIComponent(window.location.pathname)}` : '/usuarios/login/');
                            } else if (r.isDenied) {
                                window.location.assign(window.PRISMA?.urls?.registro ? `${window.PRISMA.urls.registro}?next=${encodeURIComponent(window.location.pathname)}` : '/usuarios/registro/');
                            }
                        });
                    }
                    return;
                }

                if (!reservaForm.reportValidity()) return;

                const submitButton = reservaForm.querySelector('[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando reserva...';
                }

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

                    reservaForm.dataset.submitted = 'true';

                    // Si es PARA LLEVAR: Abrir modal de pago interactivo
                    if (resultado.reservation_type === 'Para llevar') {
                        abrirModalPago(resultado.reservation_id, resultado.total);
                    } else {
                        // Si es MESA: Mostrar alerta animada festiva
                        lanzarConfetti(2800);
                        if (window.Swal) {
                            await Swal.fire({
                                customClass: {
                                    popup: 'sweet-celebration-dialog',
                                    confirmButton: 'luxury-btn-gold'
                                },
                                icon: 'success',
                                title: resultado.title || '¡Solicitud de Mesa Recibida! 🥂✨',
                                html: `
                                    <div class="sweet-payment-celebration">
                                        <p class="sweet-message-text">${escapeHTML(resultado.message)}</p>
                                        <div class="sweet-receipt-pill">
                                            <strong>Reserva #${escapeHTML(resultado.reservation_id)}</strong> · Total estimado: <strong>${escapeHTML(resultado.total)} COP</strong>
                                        </div>
                                        <p class="sweet-pickup-info">📅 Fecha: <strong>${escapeHTML(resultado.fecha_formateada)}</strong> a las <strong>${escapeHTML(resultado.hora_formateada)}</strong></p>
                                    </div>
                                `,
                                showCancelButton: true,
                                confirmButtonText: '<i class="fas fa-eye"></i> Ver mi Reserva',
                                cancelButtonText: '<i class="fab fa-whatsapp"></i> Confirmar por WhatsApp',
                                buttonsStyling: false
                            }).then(choice => {
                                if (choice.isConfirmed && resultado.next_url) {
                                    window.location.assign(resultado.next_url);
                                } else if (resultado.whatsapp_url) {
                                    window.open(resultado.whatsapp_url, '_blank');
                                    if (resultado.next_url) window.location.assign(resultado.next_url);
                                }
                            });
                        }
                    }
                } catch (error) {
                    if (window.Swal) {
                        Swal.fire({
                            icon: 'error',
                            title: 'No se pudo registrar',
                            text: error.message || 'Ocurrió un error al enviar la reserva.',
                            confirmButtonColor: '#df9f28'
                        });
                    } else {
                        mostrarNotificacion(error.message || 'Ocurrió un error al enviar la reserva.');
                    }
                } finally {
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.innerHTML = '<span class="btn-text">Confirmar mi Reserva</span> <i class="fas fa-arrow-right"></i>';
                    }
                }
            });
        }
    }

    // Manejo interactivo en la vista de detalle del cliente (detalle.html)
    const btnOpenPayFromDetail = document.getElementById('btnOpenPayFromDetail');
    if (btnOpenPayFromDetail) {
        btnOpenPayFromDetail.addEventListener('click', () => {
            const payBox = document.getElementById('payBoxSection');
            if (payBox) payBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    }

    const inlinePayForm = document.getElementById('inlinePayForm');
    if (inlinePayForm) {
        inlinePayForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = inlinePayForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verificando pago...';
            }
            try {
                const resp = await fetch(inlinePayForm.action, {
                    method: 'POST',
                    body: new FormData(inlinePayForm),
                    headers: { 'Accept': 'application/json' },
                    credentials: 'same-origin',
                });
                const res = await resp.json();
                if (!resp.ok || !res.ok) throw new Error(res.error || 'No se pudo completar el pago.');

                lanzarConfetti(3000);
                if (window.Swal) {
                    await Swal.fire({
                        customClass: { popup: 'sweet-celebration-dialog', confirmButton: 'luxury-btn-gold' },
                        icon: 'success',
                        title: res.title || '¡Pago Recibido con Éxito! 🎉🍰',
                        html: `
                            <div class="sweet-payment-celebration">
                                <div class="cake-pulse-icon">🍰💖</div>
                                <p class="sweet-message-text">${escapeHTML(res.message)}</p>
                                <div class="sweet-receipt-pill">
                                    <strong>Reserva #${escapeHTML(res.reservation_id)}</strong> · Total: <strong>${escapeHTML(res.total)} COP</strong>
                                </div>
                            </div>
                        `,
                        confirmButtonText: 'Continuar',
                        buttonsStyling: false
                    });
                }
                window.location.reload();
            } catch (err) {
                if (window.Swal) {
                    Swal.fire({ icon: 'error', title: 'Error en el pago', text: err.message, confirmButtonColor: '#df9f28' });
                }
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });
    }

    const formCancelarCliente = document.getElementById('formCancelarCliente');
    if (formCancelarCliente) {
        formCancelarCliente.addEventListener('submit', (e) => {
            e.preventDefault();
            if (window.Swal) {
                Swal.fire({
                    icon: 'warning',
                    title: '¿Confirmas cancelar tu reserva?',
                    text: 'Tus postres reservados serán liberados. Si ya pagaste, gestionaremos la devolución de tu dinero.',
                    showCancelButton: true,
                    confirmButtonText: 'Sí, cancelar reserva',
                    cancelButtonText: 'Mantener mi reserva',
                    confirmButtonColor: '#c45d6e',
                    cancelButtonColor: '#8a8a8a',
                }).then(result => {
                    if (result.isConfirmed) {
                        formCancelarCliente.submit();
                    }
                });
            } else if (confirm('¿Confirmas que deseas cancelar esta reserva?')) {
                formCancelarCliente.submit();
            }
        });
    }

    construirMenuMovil();
    const botonPago = document.getElementById('proceedToPayment');
    if (botonPago) botonPago.addEventListener('click', checkout);
    window.toggleMobileMenu = () => {
        const nav = document.getElementById('navMenu');
        if (nav) setMenuMovil(!nav.classList.contains('mobile-open'));
    };

    const activarTransicionesDePagina = () => {
        const progress = document.getElementById('page-progress');
        const prefetchedUrls = new Set();

        const prefetch = (urlStr) => {
            if (prefetchedUrls.has(urlStr)) return;
            prefetchedUrls.add(urlStr);
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = urlStr;
            link.as = 'document';
            document.head.appendChild(link);
        };

        const links = document.querySelectorAll('a[href]');
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (!href || href.startsWith('#') || href.startsWith('javascript:') ||
                link.target === '_blank' || link.protocol === 'mailto:' || link.protocol === 'tel:') return;

            link.addEventListener('pointerenter', () => {
                try {
                    const url = new URL(link.href, window.location.href);
                    if (url.origin === window.location.origin) prefetch(url.href);
                } catch (e) {}
            }, { passive: true });

            link.addEventListener('touchstart', () => {
                try {
                    const url = new URL(link.href, window.location.href);
                    if (url.origin === window.location.origin) prefetch(url.href);
                } catch (e) {}
            }, { passive: true });

            link.addEventListener('click', (event) => {
                if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey) return;
                try {
                    const url = new URL(link.href, window.location.href);
                    if (url.origin !== window.location.origin) return;
                    if (window.location.pathname === url.pathname && window.location.search === url.search) return;

                    if (progress) {
                        progress.classList.remove('done');
                        progress.classList.add('active');
                    }
                    document.body.classList.add('page-navigating');
                } catch (e) {}
            });
        });

        window.addEventListener('pageshow', () => {
            if (progress) {
                progress.classList.remove('active');
                progress.classList.add('done');
                setTimeout(() => progress.classList.remove('done'), 300);
            }
            document.body.classList.remove('page-navigating');
        });
    };
    activarTransicionesDePagina();

    // Exponer al ámbito global lo que necesitan los onclick del HTML
    window.agregarAlCarrito = agregarAlCarrito;
    window.agregarDesdeModal = agregarDesdeModal;
    window.cambiarCantidad = cambiarCantidad;
    window.eliminarItem = eliminarItem;
    window.vaciarCarrito = vaciarCarrito;
    window.checkout = checkout;
    window.abrirModal = abrirModal;
    window.cerrarModal = cerrarModal;
    window.navegarGaleria = navegarGaleria;
    window.filtrarProductos = filtrarProductos;
});
