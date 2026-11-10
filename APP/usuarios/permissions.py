from django.core.exceptions import PermissionDenied


ROL_CLIENTE = 'Cliente'

PERMISOS_DE_VISTA_DEL_PANEL = (
    'usuarios.view_usuario',
    'auth.view_group',
    'proveedores.view_proveedor',
    'reserva.view_reserva',
    'insumos.view_insumo',
    'compra_insumos.view_compra_insumo',
    'productos.view_producto',
    'ventas.view_venta',
)


def usuario_puede_acceder(user, permission, excluding_group_id=None):
    if not user.is_authenticated or not user.is_active:
        return False

    groups = user.groups.all()
    if not groups.exists():
        if user.is_staff or user.is_superuser:
            return True
        return user.has_perm(permission)

    active_groups = groups.filter(estado_rol__is_active=True)
    if excluding_group_id is not None:
        active_groups = active_groups.exclude(pk=excluding_group_id)

    app_label, codename = permission.split('.', 1)
    if user.is_superuser:
        return active_groups.filter(
            permissions__content_type__app_label=app_label,
            permissions__codename=codename,
        ).exists()

    if excluding_group_id is not None:
        return (
            active_groups.filter(
                permissions__content_type__app_label=app_label,
                permissions__codename=codename,
            ).exists()
            or user.user_permissions.filter(
                content_type__app_label=app_label,
                codename=codename,
            ).exists()
        )
    return user.has_perm(permission)


def usuario_puede_entrar_panel(user, excluding_group_id=None):
    if not user.is_authenticated:
        return False
    if not user.groups.exists() and (user.is_staff or user.is_superuser):
        return True
    return any(
        usuario_puede_acceder(
            user,
            permission,
            excluding_group_id=excluding_group_id,
        )
        for permission in PERMISOS_DE_VISTA_DEL_PANEL
    )


def exigir_permiso(request, permission):
    if not usuario_puede_acceder(request.user, permission):
        raise PermissionDenied
