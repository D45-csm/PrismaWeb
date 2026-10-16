(() => {
    const table = document.querySelector('#proveedoresTable');
    if (!table || !window.DataTable) return;

    new window.DataTable(table, {
        language: {
            url: 'https://cdn.datatables.net/plug-ins/2.3.4/i18n/es-ES.json',
            emptyTable: 'Aún no hay proveedores registrados.',
        },
        pageLength: 10,
        order: [[0, 'asc']],
        columnDefs: [{ orderable: false, searchable: false, targets: 5 }],
    });
})();
