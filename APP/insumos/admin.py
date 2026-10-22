from django.contrib import admin

from .models import CategoriaInsumo, Insumo

admin.site.register((CategoriaInsumo, Insumo))
