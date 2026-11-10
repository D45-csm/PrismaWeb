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
    const productEditorDialog = document.querySelector('#productEditorDialog');
    const resetCreateForm = () => {
        createForm.reset();
        createForm.querySelectorAll('input:not([type="hidden"]), textarea')
            .forEach((field) => { field.value = ''; });
        createForm.querySelectorAll('.insumo-field-error, .admin-form-errors')
            .forEach((error) => error.remove());
    };
    const closeCategoryDialog = () => {
        categoryDialog.close();
        resetCreateForm();
    };
    const openCategoryDialog = (mode, reset = false) => {
        document.querySelectorAll('.admin-crud-editor-dialog[open]').forEach((dialog) => {
            if (dialog !== categoryDialog) dialog.close();
        });
        if (reset && mode === 'crear') resetCreateForm();
        if (!categoryDialog.open) categoryDialog.showModal();
        createForm.hidden = mode !== 'crear';
        if (editForm) editForm.hidden = mode !== 'editar';
    };

    document.querySelectorAll('[data-open-category-dialog="crear"]').forEach((button) => {
        button.addEventListener('click', () => openCategoryDialog('crear', true));
    });
    document.querySelectorAll('[data-open-category-dialog="editar"]').forEach((button) => {
        button.addEventListener('click', () => {
            const url = new URL(button.dataset.categoryEditUrl, window.location.origin);
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.forEach((value, key) => {
                url.searchParams.set(key, value);
            });
            url.searchParams.set('editar_categoria', button.dataset.categoryId);
            window.location.assign(url);
        });
    });
    categoryDialog.querySelectorAll('.insumo-dialog-close, [data-close-category-dialog]')
        .forEach((button) => button.addEventListener('click', closeCategoryDialog));
    if (categoryDialog.dataset.open) {
        openCategoryDialog(categoryDialog.dataset.open);
    }
})();
