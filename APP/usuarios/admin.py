from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("telefono",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {"fields": ("telefono",)}),)
    list_display = ( 'username', 'email', 'telefono', 'is_staff')