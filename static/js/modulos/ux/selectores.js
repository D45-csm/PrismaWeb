(() => {
    const initializeSelects = () => {
        if (!window.jQuery || !window.jQuery.fn.select2) {
            throw new Error('No se pudo cargar Select2 para los menús desplegables.');
        }

        window.jQuery('select.js-select2').each((_, select) => {
            const $select = window.jQuery(select);
            if ($select.hasClass('select2-hidden-accessible')) return;

            $select.select2({
                width: '100%',
                theme: 'bootstrap-5',
                language: {
                    noResults: () => 'No se encontraron resultados',
                    searching: () => 'Buscando…',
                    inputTooShort: () => 'Escribe para buscar',
                    removeAllItems: () => 'Quitar todos los elementos',
                    removeItem: () => 'Quitar elemento',
                    search: () => 'Buscar',
                },
            });
        });
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeSelects, { once: true });
    } else {
        initializeSelects();
    }
})();
