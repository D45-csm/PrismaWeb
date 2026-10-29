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


def usuario_puede_acceder(user, permission):
    if not user.is_authenticated:
        return False

    groups = user.groups.all()
    if not groups.exists():
        if user.is_staff or user.is_superuser:
            return True
        return user.has_perm(permission)

    if user.is_superuser:
        app_label, codename = permission.split('.', 1)
        return groups.filter(
            permissions__content_type__app_label=app_label,
            permissions__codename=codename,
        ).exists()
    return user.has_perm(permission)


def usuario_puede_entrar_panel(user):
    if not user.is_authenticated:
        return False
    if not user.groups.exists() and (user.is_staff or user.is_superuser):
        return True
    return any(
        usuario_puede_acceder(user, permission)
        for permission in PERMISOS_DE_VISTA_DEL_PANEL
    )


def exigir_permiso(request, permission):
    if not usuario_puede_acceder(request.user, permission):
        raise PermissionDenied
