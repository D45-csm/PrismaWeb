(() => {
    const deleteDialog = document.querySelector('#deleteCategoryDialog');
    if (deleteDialog) {
        const categoryId = deleteDialog.querySelector('#deleteCategoryId');
        const categoryName = deleteDialog.querySelector('#deleteCategoryName');
        document.querySelectorAll('[data-confirm-category-delete]').forEach((button) => {
            button.addEventListener('click', () => {
                categoryId.value = button.dataset.categoryId;
                categoryName.textContent = button.dataset.categoryName;
                deleteDialog.showModal();
            });
        });
        deleteDialog.querySelectorAll('[data-close-delete-dialog]').forEach((button) => {
            button.addEventListener('click', () => deleteDialog.close());
        });
    }

    const categoryDialog = document.querySelector('#categoryDialog');
    if (!categoryDialog) return;

    const createForm = categoryDialog.querySelector('#categoryCreateForm');
    const editForm = categoryDialog.querySelector('[data-category-edit-form]');
    const openCategoryDialog = (mode) => {
        if (!categoryDialog.open) categoryDialog.showModal();
        createForm.hidden = mode !== 'crear';
        if (editForm) editForm.hidden = mode !== 'editar';
    };

    document.querySelectorAll('[data-open-category-dialog="crear"]').forEach((button) => {
        button.addEventListener('click', () => openCategoryDialog('crear'));
    });
    document.querySelectorAll('[data-open-category-dialog="editar"]').forEach((button) => {
        button.addEventListener('click', () => {
            const url = new URL(window.location.href);
            url.searchParams.set('editar_categoria', button.dataset.categoryId);
            window.location.assign(url);
        });
    });
    categoryDialog.querySelectorAll('.insumo-dialog-close, [data-close-category-dialog]')
        .forEach((button) => button.addEventListener('click', () => categoryDialog.close()));
    if (categoryDialog.dataset.open) {
        openCategoryDialog(categoryDialog.dataset.open);
    }
})();
