(() => {
    const detailDialog = document.querySelector('#crudDetailDialog');
    const deleteDialog = document.querySelector('#crudDeleteDialog');
    const editorDialog = document.querySelector('[data-open-crud-editor]')?.closest('.admin-crud-page')
        ?.querySelector('dialog[data-open]');
    const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;

    document.querySelectorAll('[data-close-crud-dialog]').forEach((button) => {
        button.addEventListener('click', () => button.closest('dialog')?.close());
    });

    const roleDeleteDialog = document.querySelector('#roleDeleteDialog');
    if (roleDeleteDialog) {
        const roleId = roleDeleteDialog.querySelector('[data-role-delete-id-field]');
        const roleName = roleDeleteDialog.querySelector('[data-role-delete-name]');

        document.querySelectorAll('[data-role-delete-id]').forEach((button) => {
            button.addEventListener('click', () => {
                roleId.value = button.dataset.roleDeleteId;
                roleName.textContent = button.dataset.roleDeleteName;
                roleDeleteDialog.showModal();
            });
        });

        roleDeleteDialog.querySelectorAll('[data-close-role-delete]').forEach((button) => {
            button.addEventListener('click', () => roleDeleteDialog.close());
        });
    }

    document.querySelectorAll('[data-open-crud-editor]').forEach((button) => {
        button.addEventListener('click', () => {
            if (!editorDialog) return;
            document.querySelectorAll('.admin-crud-editor-dialog[open]').forEach((dialog) => {
                if (dialog !== editorDialog) dialog.close();
            });
            const form = editorDialog.querySelector('form');
            if (form) {
                form.querySelectorAll('input, select, textarea').forEach((field) => {
                    if (field.name === 'csrfmiddlewaretoken') return;
                    if (field.type === 'hidden') {
                        if (field.name === 'accion') field.value = button.dataset.createAction;
                        else if (field.name.startsWith('eliminar_')) field.value = '0';
                        else if (field.name === 'proveedor_id') field.remove();
                        return;
                    }
                    if (field.type === 'checkbox') {
                        field.checked = field.name === 'activo';
                    } else if (field.type === 'file') {
                        field.value = '';
                    } else if (field.tagName === 'SELECT') {
                        field.selectedIndex = 0;
                    } else {
                        field.value = '';
                    }
                });
                form.querySelectorAll('.product-image-preview').forEach((preview) => {
                    if (preview.src.startsWith('blob:')) URL.revokeObjectURL(preview.src);
                    preview.removeAttribute('src');
                    preview.hidden = true;
                });
                form.querySelectorAll('.insumo-field-error, .admin-form-errors')
                    .forEach((error) => error.remove());
                const createUrl = button.dataset.createUrl;
                if (createUrl && form.enctype === 'multipart/form-data') form.action = createUrl;
            }
            editorDialog.showModal();
        });
    });
    if (editorDialog?.dataset.open) editorDialog.showModal();

    if (deleteDialog) {
        const deleteForm = deleteDialog.querySelector('#crudDeleteForm');
        const deleteName = deleteDialog.querySelector('[data-crud-delete-name]');
        document.querySelectorAll('[data-crud-delete-url]').forEach((button) => {
            button.addEventListener('click', () => {
                deleteForm.action = button.dataset.crudDeleteUrl;
                deleteName.textContent = button.dataset.crudDeleteName;
                deleteDialog.showModal();
            });
        });
    }

    document.querySelectorAll('.insumo-row-actions, .insumo-category-menu')
        .forEach((menu) => {
            let closeTimer;
            const submenu = menu.querySelector('.insumo-row-menu, .insumo-category-menu-items');
            const cancelClose = () => window.clearTimeout(closeTimer);
            const scheduleClose = (event) => {
                if (event.pointerType !== 'mouse') return;
                cancelClose();
                closeTimer = window.setTimeout(() => {
                    menu.open = false;
                }, 150);
            };

            menu.addEventListener('pointerenter', cancelClose);
            menu.addEventListener('pointerleave', scheduleClose);
            submenu?.addEventListener('pointerenter', cancelClose);
            submenu?.addEventListener('pointerleave', scheduleClose);
            menu.addEventListener('toggle', () => {
                if (!menu.open) cancelClose();
            });
        });

    if (!detailDialog) return;

    const message = detailDialog.querySelector('.insumo-dialog-message');
    const availability = detailDialog.querySelector('[data-crud-availability]');
    const editLink = detailDialog.querySelector('[data-crud-edit-link]');
    let statusUrl = '';
    let statusLabel = '';
    let currentRecordId = '';

    const setMessage = (text, isError = false) => {
        message.textContent = text;
        message.hidden = !text;
        message.classList.toggle('error', isError);
    };

    const renderItem = (item) => {
        currentRecordId = item.id;
        detailDialog.querySelector('#crudDetailTitle').textContent = item.nombre;
        detailDialog.querySelector('.insumo-dialog-description').textContent =
            item.descripcion || 'Aún no tiene descripción.';
        const meta = detailDialog.querySelector('.insumo-dialog-meta');
        meta.replaceChildren();
        (item.meta || []).forEach((label) => {
            const badge = document.createElement('span');
            badge.textContent = label;
            meta.append(badge);
        });
        const statusBadge = document.createElement('span');
        statusBadge.textContent = item.activo ? 'Activo' : 'Desactivado';
        statusBadge.classList.toggle('inactive', !item.activo);
        meta.append(statusBadge);

        const image = detailDialog.querySelector('.insumo-dialog-image img');
        const placeholder = detailDialog.querySelector('.insumo-dialog-image span');
        image.hidden = !item.imagen;
        placeholder.hidden = Boolean(item.imagen);
        image.src = item.imagen || '';
        image.alt = item.imagen ? `Imagen de ${item.nombre}` : '';
        editLink.href = item.edit_url;
        availability.checked = item.activo;
        availability.setAttribute('aria-label', `${item.activo ? 'Desactivar' : 'Activar'} ${item.nombre}`);
        statusUrl = item.status_url;
        statusLabel = item.nombre;
    };

    document.querySelectorAll('[data-crud-detail-url]').forEach((button) => {
        button.addEventListener('click', async () => {
            setMessage('Cargando información…');
            detailDialog.showModal();
            try {
                const response = await fetch(button.dataset.crudDetailUrl, {
                    headers: {'X-Requested-With': 'XMLHttpRequest'},
                });
                const item = await response.json();
                if (!response.ok) throw new Error(item.error || 'No se pudo cargar el registro.');
                renderItem(item);
                setMessage('');
            } catch (error) {
                setMessage(error.message || 'No se pudo cargar el registro.', true);
            }
        });
    });

    availability.addEventListener('change', async () => {
        const previousValue = !availability.checked;
        availability.disabled = true;
        setMessage(availability.checked ? 'Activando…' : 'Desactivando…');
        try {
            const data = new FormData();
            data.set('activo', String(availability.checked));
            const response = await fetch(statusUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: data,
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'No se pudo actualizar el estado.');
            availability.checked = result.activo;
            availability.setAttribute('aria-label', `${result.activo ? 'Desactivar' : 'Activar'} ${statusLabel}`);
            const dialogStatus = detailDialog.querySelector('.insumo-dialog-meta span:last-child');
            if (dialogStatus) {
                dialogStatus.textContent = result.activo ? 'Activo' : 'Desactivado';
                dialogStatus.classList.toggle('inactive', !result.activo);
            }
            const row = document.querySelector(`[data-crud-record-id="${currentRecordId}"]`);
            if (row) {
                const wasActive = row.dataset.activeBeforeUpdate === 'true';
                row.dataset.activeBeforeUpdate = String(result.activo);
                row.classList.toggle('insumo-row-inactive', !result.activo);
                row.querySelector('.insumo-status')?.classList.toggle('inactive', !result.activo);
                const badge = row.querySelector('.insumo-status');
                if (badge) badge.textContent = result.activo ? 'Activo' : 'Desactivado';

                const page = document.querySelector('.admin-crud-page');
                const activeCount = Number(page?.dataset.activeCount || 0);
                const nextCount = Math.max(0, activeCount + Number(result.activo) - Number(wasActive));
                if (page) page.dataset.activeCount = String(nextCount);
                const summary = page?.querySelector('.supplier-active-summary, .product-active-summary');
                if (summary) {
                    const icon = summary.querySelector('i');
                    summary.replaceChildren(
                        ...(icon ? [icon] : []),
                        document.createTextNode(` ${nextCount} ${page.dataset.activeLabel}`),
                    );
                }
                const state = page?.dataset.activeState;
                row.hidden = (state === 'activos' && !result.activo)
                    || (state === 'inactivos' && result.activo);
            }
            setMessage(result.message);
        } catch (error) {
            availability.checked = previousValue;
            setMessage(error.message || 'No se pudo actualizar el estado.', true);
        } finally {
            availability.disabled = false;
        }
    });
})();
