from django.core.exceptions import PermissionDenied


def usuario_puede_acceder(user, permission):
    if not user.is_authenticated or not (user.is_staff or user.is_superuser):
        return False
    if user.is_superuser or not user.groups.exists():
        return True
    return user.has_perm(permission)


def exigir_permiso(request, permission):
    if not usuario_puede_acceder(request.user, permission):
        raise PermissionDenied
