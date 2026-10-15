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
    if (categoryDialog) {
        const createForm = categoryDialog.querySelector('#categoryCreateForm');
        const editForm = categoryDialog.querySelector('[data-category-edit-form]');
        const openCategoryDialog = (mode) => {
            if (!categoryDialog.open) categoryDialog.showModal();
            if (createForm) createForm.hidden = mode !== 'crear';
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
    }

    const dialog = document.querySelector('#insumoDialog');
    if (!dialog) return;

    const details = dialog.querySelector('.insumo-dialog-details');
    const editForm = dialog.querySelector('.insumo-dialog-edit');
    const fields = dialog.querySelector('.insumo-dialog-fields');
    const message = dialog.querySelector('.insumo-dialog-message');
    const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
    let currentItem = null;
    let currentUrl = '';

    const setMessage = (text, isError = false) => {
        message.textContent = text;
        message.hidden = !text;
        message.classList.toggle('error', isError);
    };

    const makeField = (labelText, name, control) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'insumo-field';
        const label = document.createElement('label');
        label.htmlFor = control.id;
        label.textContent = labelText;
        control.name = name;
        control.id = `insumo-edit-${name}`;
        control.classList.add('insumo-input');
        wrapper.append(label, control);
        return wrapper;
    };

    const renderDetails = (item) => {
        currentItem = item;
        dialog.querySelector('#insumoDialogTitle').textContent = item.nombre;
        dialog.querySelector('.insumo-dialog-description').textContent =
            item.descripcion || 'Aún no tiene descripción.';
        dialog.querySelector('.insumo-dialog-category').textContent = `Categoría: ${item.categoria}`;
        dialog.querySelector('.insumo-dialog-unit').textContent = `Unidad: ${item.unidad_medida_display}`;

        const status = dialog.querySelector('.insumo-dialog-status');
        status.textContent = item.activo ? 'Activo' : 'Desactivado';
        status.classList.toggle('inactive', !item.activo);
        const availability = dialog.querySelector('.insumo-dialog-availability');
        availability.checked = item.activo;

        const image = dialog.querySelector('.insumo-dialog-image img');
        const placeholder = dialog.querySelector('.insumo-dialog-image span');
        image.hidden = !item.imagen;
        placeholder.hidden = Boolean(item.imagen);
        image.src = item.imagen || '';
        image.alt = item.imagen ? `Imagen de ${item.nombre}` : '';
    };

    const buildEditForm = (item) => {
        fields.replaceChildren();
        const prefix = `insumo-${item.id}`;

        const name = document.createElement('input');
        name.type = 'text';
        name.maxLength = 100;
        name.value = item.nombre;
        fields.append(makeField('Nombre', `${prefix}-nombre`, name));

        const description = document.createElement('textarea');
        description.rows = 3;
        description.value = item.descripcion;
        fields.append(makeField('Descripción', `${prefix}-descripcion`, description));

        const category = document.createElement('select');
        item.categorias.forEach((categoryItem) => {
            const option = document.createElement('option');
            option.value = categoryItem.id;
            option.textContent = categoryItem.nombre;
            option.selected = String(categoryItem.id) === String(item.categoria_id);
            category.append(option);
        });
        fields.append(makeField('Categoría', `${prefix}-categoria`, category));

        const unit = document.createElement('select');
        item.unidades.forEach((unitItem) => {
            const option = document.createElement('option');
            option.value = unitItem.id;
            option.textContent = unitItem.nombre;
            option.selected = unitItem.id === item.unidad_medida;
            unit.append(option);
        });
        fields.append(makeField('Unidad de medida', `${prefix}-unidad_medida`, unit));

        const image = document.createElement('input');
        image.type = 'file';
        image.accept = 'image/*';
        fields.append(makeField('Cambiar imagen', `${prefix}-imagen`, image));

        if (item.imagen) {
            const clearImage = document.createElement('input');
            clearImage.type = 'checkbox';
            clearImage.value = 'on';
            clearImage.classList.remove('insumo-input');
            const clearField = makeField(
                'Quitar imagen actual',
                `${prefix}-imagen-clear`,
                clearImage,
            );
            clearField.classList.add('insumo-field-checkbox');
            fields.append(clearField);
        }
    };

    document.querySelectorAll('[data-insumo-url]').forEach((button) => {
        button.addEventListener('click', async () => {
            currentUrl = button.dataset.insumoUrl;
            setMessage('Cargando información…');
            editForm.hidden = true;
            details.hidden = false;
            dialog.querySelector('.insumo-dialog-view-actions').hidden = true;
            dialog.showModal();

            try {
                const response = await fetch(currentUrl, {
                    headers: {'X-Requested-With': 'XMLHttpRequest'},
                });
                if (!response.ok) throw new Error('No se pudo cargar el insumo.');
                const item = await response.json();
                renderDetails(item);
                setMessage('');
                dialog.querySelector('.insumo-dialog-view-actions').hidden = false;
            } catch (error) {
                setMessage(error.message || 'No se pudo cargar el insumo.', true);
            }
        });
    });

    dialog.querySelector('.insumo-dialog-close').addEventListener('click', () => dialog.close());
    dialog.querySelector('.insumo-dialog-cancel').addEventListener('click', () => {
        editForm.hidden = true;
        details.hidden = false;
        dialog.querySelector('.insumo-dialog-view-actions').hidden = false;
        setMessage('');
    });

    dialog.querySelector('.insumo-dialog-update').addEventListener('click', () => {
        buildEditForm(currentItem);
        details.hidden = true;
        editForm.hidden = false;
        dialog.querySelector('.insumo-dialog-view-actions').hidden = true;
        setMessage('');
    });

    editForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(editForm);
        formData.set('accion', 'editar_insumo');
        editForm.querySelector('[type="submit"]').disabled = true;
        setMessage('Guardando cambios…');

        try {
            const response = await fetch(currentUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData,
            });
            const result = await response.json();
            if (!response.ok) {
                const errors = Object.values(result.errors || {})
                    .flat()
                    .map((error) => error.message)
                    .join(' ');
                throw new Error(errors || result.error || 'No se pudieron guardar los cambios.');
            }
            renderDetails({...currentItem, ...result});
            updateRow(result);
            editForm.hidden = true;
            details.hidden = false;
            dialog.querySelector('.insumo-dialog-view-actions').hidden = false;
            setMessage(result.message);
        } catch (error) {
            setMessage(error.message || 'No se pudieron guardar los cambios.', true);
        } finally {
            editForm.querySelector('[type="submit"]').disabled = false;
        }
    });

    dialog.querySelector('.insumo-dialog-availability').addEventListener('change', async (event) => {
        const availability = event.currentTarget;
        const previousValue = currentItem.activo;
        const data = new FormData();
        data.set('accion', 'cambiar_disponibilidad');
        data.set('activo', String(availability.checked));
        availability.disabled = true;
        setMessage(availability.checked ? 'Activando…' : 'Desactivando…');

        try {
            const response = await fetch(currentUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: data,
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'No se pudo completar la acción.');

            currentItem.activo = result.activo;
            renderDetails(currentItem);
            updateRow(result);
            setMessage(result.message);
        } catch (error) {
            availability.checked = previousValue;
            setMessage(error.message || 'No se pudo actualizar la disponibilidad.', true);
        } finally {
            availability.disabled = false;
        }
    });

    const updateRow = (item) => {
        const row = document.querySelector(`[data-insumo-row="${item.id}"]`);
        if (!row) return;
        if (item.nombre) {
            row.querySelector('.insumo-row-select').textContent = item.nombre;
            row.querySelector('.insumo-row-info > p').textContent =
                item.descripcion || 'Sin descripción';
            const categoryLabel = row.querySelector('.insumo-row-meta > span:first-child');
            const unitLabel = row.querySelector('.insumo-row-meta > span:nth-child(2)');
            const categoryIcon = categoryLabel.querySelector('i');
            const unitIcon = unitLabel.querySelector('i');
            categoryLabel.replaceChildren(categoryIcon, document.createTextNode(` ${item.categoria}`));
            unitLabel.replaceChildren(
                unitIcon,
                document.createTextNode(` ${item.unidad_medida_display}`),
            );
            if (item.categoria_id) row.dataset.categoriaId = item.categoria_id;
            row.dataset.categoria = item.categoria;
            row.dataset.unidad = item.unidad_medida_display;
        }
        if (typeof item.activo === 'boolean') {
            row.dataset.activo = String(item.activo);
            row.classList.toggle('insumo-row-inactive', !item.activo);
            const badge = row.querySelector('.insumo-status');
            badge.textContent = item.activo ? 'Activo' : 'Desactivado';
            badge.classList.toggle('inactive', !item.activo);

            const summary = document.querySelector('.insumo-summary span:nth-child(2)');
            const count = document.querySelector('.insumo-dashboard');
            const wasActive = row.dataset.activeBeforeUpdate === 'true';
            if (wasActive !== item.activo && count) {
                const total = Number(count.dataset.insumosCount) + (item.activo ? 1 : -1);
                count.dataset.insumosCount = String(Math.max(0, total));
                if (summary) {
                    const icon = summary.querySelector('i');
                    summary.replaceChildren(
                        icon,
                        document.createTextNode(` ${Math.max(0, total)} insumos activos`),
                    );
                }
            }
            row.dataset.activeBeforeUpdate = String(item.activo);
        }

        const dashboard = document.querySelector('.insumo-dashboard');
        const filterState = dashboard.dataset.estado;
        const queryFilter = dashboard.dataset.query.trim().toLocaleLowerCase();
        const searchField = dashboard.dataset.campo;
        const rowText = searchField === 'categoria'
            ? row.dataset.categoria || ''
            : searchField === 'tamano'
                ? row.dataset.unidad || ''
                : row.querySelector('.insumo-row-select')?.textContent || '';
        row.hidden =
            (filterState === 'activos' && row.dataset.activo !== 'true') ||
            (filterState === 'inactivos' && row.dataset.activo !== 'false') ||
            (queryFilter && !rowText.toLocaleLowerCase().includes(queryFilter));
        const visibleRows = [...document.querySelectorAll('[data-insumo-row]')]
            .filter((candidate) => !candidate.hidden).length;
        const resultsLabel = document.querySelector('.insumo-results-label span');
        if (resultsLabel) {
            resultsLabel.textContent = `${visibleRows} resultado${visibleRows === 1 ? '' : 's'}`;
        }
    };
})();
