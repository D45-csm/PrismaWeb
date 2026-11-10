from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class BackendRolesActivos(ModelBackend):
    def _get_group_permissions(self, user_obj):
        return Permission.objects.filter(
            group__user=user_obj,
            group__estado_rol__is_active=True,
        )
