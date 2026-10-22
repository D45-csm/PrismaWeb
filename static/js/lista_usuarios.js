(() => {
    document.querySelectorAll('[data-user-role-select]').forEach((select) => {
        const form = select.closest('.user-role-form');
        const saveButton = form?.querySelector('[data-user-role-save]');
        if (!saveButton || select.disabled) return;

        const initialRole = select.value;
        select.addEventListener('change', () => {
            saveButton.hidden = select.value === initialRole;
        });
    });
})();
