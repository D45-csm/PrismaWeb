(() => {
    const dialog = document.querySelector('#recipeEditorDialog');
    const form = dialog?.querySelector('form');
    const rows = dialog?.querySelector('[data-recipe-ingredient-rows]');
    const template = dialog?.querySelector('[data-empty-recipe-ingredient]');
    const totalForms = dialog?.querySelector('[name="ingredients-TOTAL_FORMS"]');
    const unitMapElement = document.querySelector('#recipe-unit-map');
    const unitsByIngredient = unitMapElement
        ? JSON.parse(unitMapElement.textContent)
        : {};
    const unitOptionsBySelect = new WeakMap();
    const deleteId = document.querySelector('[data-recipe-delete-id-field]');
    const deleteDialog = document.querySelector('#crudDeleteDialog');
    const deleteName = deleteDialog?.querySelector('[data-crud-delete-name]');

    const refreshIngredientRow = (row, resetUnit = false) => {
        const ingredientSelect = row.querySelector('[data-recipe-insumo]');
        const unitSelect = row.querySelector('[data-recipe-unit]');
        const inventoryUnit = row.querySelector('[data-inventory-unit]');
        if (!ingredientSelect || !unitSelect) return;

        const ingredient = unitsByIngredient[ingredientSelect.value];
        const selectedUnit = resetUnit ? '' : unitSelect.value;
        const incompatibleUnit = resetUnit
            ? ''
            : unitSelect.dataset.incompatibleValue;
        const compatibleUnits = ingredient?.unidades || [];
        const initialOptions = unitOptionsBySelect.get(unitSelect)
            || [...unitSelect.options].map((option) => option.cloneNode(true));
        const placeholder = initialOptions.find((option) => option.value === '');
        unitSelect.replaceChildren();
        if (placeholder) unitSelect.append(placeholder.cloneNode(true));

        initialOptions
            .filter((option) => compatibleUnits.includes(option.value))
            .forEach((option) => unitSelect.append(option.cloneNode(true)));

        if (incompatibleUnit && !compatibleUnits.includes(incompatibleUnit)) {
            const invalidOption = document.createElement('option');
            invalidOption.value = incompatibleUnit;
            invalidOption.textContent = `${incompatibleUnit} (unidad incompatible; selecciona otra)`;
            invalidOption.disabled = true;
            invalidOption.selected = true;
            unitSelect.append(invalidOption);
        } else if (compatibleUnits.includes(selectedUnit)) {
            unitSelect.value = selectedUnit;
        } else if (ingredient) {
            unitSelect.value = ingredient.unidad_inventario;
        }

        if (inventoryUnit) {
            inventoryUnit.textContent = ingredient
                ? `Inventario: ${ingredient.unidad_inventario}.`
                : '';
        }
    };

    const initializeIngredientRow = (row) => {
        const ingredientSelect = row.querySelector('[data-recipe-insumo]');
        const unitSelect = row.querySelector('[data-recipe-unit]');
        if (!ingredientSelect || !unitSelect) return;

        unitOptionsBySelect.set(
            unitSelect,
            [...unitSelect.options].map((option) => option.cloneNode(true)),
        );
        refreshIngredientRow(row);
        if (row.hidden) {
            row.querySelectorAll('input, select, textarea').forEach((field) => {
                if (field.type !== 'hidden' && !field.name.endsWith('-DELETE')) {
                    field.disabled = true;
                }
            });
        }
        ingredientSelect.addEventListener('change', () => {
            unitSelect.dataset.incompatibleValue = '';
            refreshIngredientRow(row, true);
            unitSelect.removeAttribute('aria-invalid');
            ingredientSelect.removeAttribute('aria-invalid');
            ingredientSelect.closest('.insumo-field')
                ?.querySelectorAll('[data-field-error]')
                .forEach((error) => error.remove());
            row.querySelectorAll('[data-unit-error]')
                .forEach((error) => error.remove());
        });
        unitSelect.addEventListener('change', () => {
            unitSelect.dataset.incompatibleValue = '';
            unitSelect.removeAttribute('aria-invalid');
            row.querySelectorAll('[data-unit-error]').forEach((error) => error.remove());
        });
        row.querySelector('[name$="-cantidad_insumo"]')?.addEventListener('input', (event) => {
            event.currentTarget.removeAttribute('aria-invalid');
            event.currentTarget.closest('.insumo-field')
                ?.querySelectorAll('[data-field-error]')
                .forEach((error) => error.remove());
        });
    };

    rows?.querySelectorAll('[data-recipe-ingredient-row]')
        .forEach(initializeIngredientRow);

    document.querySelectorAll('[data-recipe-delete-id]').forEach((button) => {
        button.addEventListener('click', () => {
            if (deleteId) deleteId.value = button.dataset.recipeDeleteId;
        });
    });
    deleteDialog?.addEventListener('close', () => {
        if (deleteId) deleteId.value = '';
        if (deleteName) deleteName.textContent = '';
    });

    if (!dialog || !form || !rows || !template || !totalForms) return;

    const resetEditor = () => {
        form.reset();
        const initialFormCount = Number(rows.dataset.initialFormCount || 0);
        const ingredientRows = [...rows.querySelectorAll('[data-recipe-ingredient-row]')];
        ingredientRows.forEach((row, index) => {
            if (index >= initialFormCount) {
                row.remove();
                return;
            }
            row.querySelectorAll('input, select, textarea').forEach((field) => {
                field.disabled = false;
                if (field.name.endsWith('-DELETE')) {
                    field.checked = false;
                } else if (field.type === 'hidden') {
                    field.value = '';
                } else if (field.type === 'checkbox') {
                    field.checked = false;
                } else {
                    field.value = '';
                }
            });
            row.querySelector('[data-recipe-unit]')?.removeAttribute(
                'data-incompatible-value',
            );
            row.querySelectorAll('[data-field-error], [data-unit-error]')
                .forEach((error) => error.remove());
            row.hidden = false;
            refreshIngredientRow(row, true);
        });
        form.querySelectorAll('input, select, textarea').forEach((field) => {
            if (
                field.name === 'csrfmiddlewaretoken'
                || /^ingredients-(TOTAL_FORMS|INITIAL_FORMS|MIN_NUM_FORMS|MAX_NUM_FORMS)$/.test(field.name)
            ) {
                return;
            }
            if (field.type === 'checkbox' || field.type === 'radio') {
                field.checked = false;
            } else if (field.type === 'hidden' || field.type === 'file') {
                field.value = '';
            } else if (field.tagName === 'SELECT') {
                field.selectedIndex = 0;
            } else {
                field.value = '';
            }
            field.removeAttribute('aria-invalid');
        });
        form.querySelectorAll('.admin-form-errors, [data-field-error], [data-unit-error]')
            .forEach((error) => error.remove());
        totalForms.value = String(initialFormCount);
    };

    dialog.addEventListener('close', resetEditor);

    dialog.querySelector('[data-add-recipe-ingredient]')?.addEventListener('click', () => {
        const index = Number(totalForms.value);
        const markup = template.innerHTML.replaceAll('__prefix__', String(index));
        rows.insertAdjacentHTML('beforeend', markup);
        initializeIngredientRow(rows.lastElementChild);
        totalForms.value = String(index + 1);
    });

    dialog.addEventListener('click', (event) => {
        const removeButton = event.target.closest('[data-remove-recipe-ingredient]');
        if (!removeButton) return;
        const row = removeButton.closest('[data-recipe-ingredient-row]');
        const deleteField = row?.querySelector('input[name$="-DELETE"]');
        if (deleteField) deleteField.checked = true;
        if (row) {
            row.hidden = true;
            row.querySelectorAll('input, select, textarea').forEach((field) => {
                if (field.type !== 'hidden' && !field.name.endsWith('-DELETE')) {
                    field.disabled = true;
                }
            });
        }
    });
})();
