from django.contrib import admin
from .models import Producto, CategoriaProducto


admin.site.register(Producto)
admin.site.register(CategoriaProducto)