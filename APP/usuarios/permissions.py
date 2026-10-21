from django.core.exceptions import PermissionDenied


def usuario_puede_acceder(user, permission):
    if not user.is_authenticated or not (user.is_staff or user.is_superuser):
        return False
    groups = user.groups.all()
    if not groups.exists():
        return True
    if user.is_superuser:
        app_label, codename = permission.split('.', 1)
        return groups.filter(
            permissions__content_type__app_label=app_label,
            permissions__codename=codename,
        ).exists()
    return user.has_perm(permission)


def exigir_permiso(request, permission):
    if not usuario_puede_acceder(request.user, permission):
        raise PermissionDenied
