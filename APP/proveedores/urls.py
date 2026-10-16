from django.urls import path

from .views import (
    ProveedorCreateView,
    ProveedorDeleteView,
    ProveedorListView,
    ProveedorUpdateView,
)

urlpatterns = [
    path('', ProveedorListView.as_view(), name='proveedores_lista'),
    path('crear/', ProveedorCreateView.as_view(), name='proveedores_crear'),
    path(
        '<int:pk>/editar/',
        ProveedorUpdateView.as_view(),
        name='proveedores_editar',
    ),
    path(
        '<int:pk>/eliminar/',
        ProveedorDeleteView.as_view(),
        name='proveedores_eliminar',
    ),
]