(() => {
    const dialog = document.querySelector('#insumoDialog');
    if (!dialog) return;

    const deleteDialog = document.querySelector('#insumoDeleteDialog');
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
        dialog.querySelector('.insumo-dialog-provider').textContent =
            `Proveedor: ${item.proveedor_referencia || 'Sin proveedor'}`;

        const status = dialog.querySelector('.insumo-dialog-status');
        status.textContent = item.activo ? 'Activo' : 'Desactivado';
        status.classList.toggle('inactive', !item.activo);

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

        const provider = document.createElement('select');
        item.proveedores.forEach((providerItem) => {
            const option = document.createElement('option');
            option.value = providerItem.id;
            option.textContent = providerItem.nombre;
            option.selected =
                String(providerItem.id) === String(item.proveedor_referencia_id);
            provider.append(option);
        });
        fields.append(makeField(
            'Proveedor de referencia',
            `${prefix}-proveedor_referencia`,
            provider,
        ));

        const availability = document.createElement('input');
        availability.type = 'checkbox';
        availability.checked = item.activo;
        availability.value = 'on';
        availability.classList.remove('insumo-input');
        const availabilityField = makeField(
            'Disponible en el inventario',
            `${prefix}-activo`,
            availability,
        );
        availabilityField.classList.add('insumo-field-checkbox');
        fields.append(availabilityField);

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

    dialog.querySelector('.insumo-dialog-delete').addEventListener('click', () => {
        deleteDialog.querySelector('.insumo-delete-name').textContent = currentItem.nombre;
        deleteDialog.showModal();
    });
    deleteDialog.querySelector('.insumo-delete-cancel').addEventListener('click', () => {
        deleteDialog.close();
    });
    deleteDialog.querySelector('.insumo-delete-confirm').addEventListener('click', async (event) => {
        const confirmButton = event.currentTarget;
        confirmButton.disabled = true;
        setMessage('Verificando historial y eliminando…');
        const data = new FormData();
        data.set('accion', 'eliminar_insumo');

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
            if (!response.ok) throw new Error(result.error || 'No se pudo eliminar el insumo.');

            deleteDialog.close();
            setMessage(result.message);
            window.setTimeout(() => window.location.reload(), 700);
        } catch (error) {
            deleteDialog.close();
            setMessage(error.message || 'No se pudo eliminar el insumo.', true);
        } finally {
            confirmButton.disabled = false;
        }
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
            const providerLabel = row.querySelector('.insumo-row-meta > span:nth-child(3)');
            const providerIcon = providerLabel.querySelector('i');
            providerLabel.replaceChildren(
                providerIcon,
                document.createTextNode(` ${item.proveedor_referencia || 'Sin proveedor'}`),
            );
            if (item.categoria_id) row.dataset.categoriaId = item.categoria_id;
        }
        if (typeof item.activo === 'boolean') {
            const wasActive = row.dataset.activo === 'true';
            row.dataset.activo = String(item.activo);
            row.classList.toggle('insumo-row-inactive', !item.activo);
            const badge = row.querySelector('.insumo-status');
            badge.textContent = item.activo ? 'Activo' : 'Desactivado';
            badge.classList.toggle('inactive', !item.activo);

            const summary = document.querySelector('.insumo-summary span:nth-child(2)');
            const count = document.querySelector('.insumo-dashboard');
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
        }

        const dashboard = document.querySelector('.insumo-dashboard');
        const filterState = dashboard.dataset.estado;
        const categoryFilter = dashboard.dataset.categoriaSeleccionada;
        const queryFilter = dashboard.dataset.query.trim().toLocaleLowerCase();
        const searchField = dashboard.dataset.campo;
        const filterText = {
            nombre: row.querySelector('.insumo-row-select')?.textContent || '',
            tipo: row.querySelector('.insumo-row-meta > span:first-child')?.textContent || '',
            tamano: row.querySelector('.insumo-row-meta > span:nth-child(2)')?.textContent || '',
        }[searchField];
        const rowText = filterText.toLocaleLowerCase();
        row.hidden =
            (filterState === 'activos' && row.dataset.activo !== 'true') ||
            (filterState === 'inactivos' && row.dataset.activo !== 'false') ||
            (categoryFilter && row.dataset.categoriaId !== categoryFilter) ||
            (queryFilter && !rowText.includes(queryFilter));
        const visibleRows = [...document.querySelectorAll('[data-insumo-row]')]
            .filter((candidate) => !candidate.hidden).length;
        const resultsLabel = document.querySelector('.insumo-results-label span');
        if (resultsLabel) {
            resultsLabel.textContent = `${visibleRows} resultado${visibleRows === 1 ? '' : 's'}`;
        }
    };
})();
