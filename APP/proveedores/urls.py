from django.urls import path
from . import views

urlpatterns = [
    path('', views.gestion_proveedores, name='gestion_proveedores'),
    path('guardar/', views.guardar_proveedor, name='guardar_proveedor'),
    path(
        '<int:pk>/estado/',
        views.cambiar_estado_proveedor,
        name='cambiar_estado_proveedor',
    ),
]