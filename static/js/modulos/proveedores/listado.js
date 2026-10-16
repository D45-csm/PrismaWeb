(() => {
    const table = document.querySelector('#proveedoresTable');
    if (!table) return;

    if (window.DataTable) {
        new window.DataTable(table, {
            language: {
                url: 'https://cdn.datatables.net/plug-ins/2.3.4/i18n/es-ES.json',
                emptyTable: 'Aún no hay proveedores registrados.',
            },
            pageLength: 10,
            order: [[0, 'asc']],
            columnDefs: [{ orderable: false, searchable: false, targets: 5 }],
        });
    }

    const deleteForm = document.querySelector('#proveedorDeleteForm');
    table.addEventListener('click', (event) => {
        const link = event.target.closest?.('a[data-delete-url]');
        if (!link || !deleteForm) return;

        event.preventDefault();
        deleteForm.action = link.dataset.deleteUrl;
        deleteForm.dataset.confirmText = link.dataset.confirmText;
        deleteForm.requestSubmit();
    });
})();
