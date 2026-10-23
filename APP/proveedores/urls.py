from django.urls import path
from . import views

urlpatterns = [
    # Ruta principal: Lista y Crea
    path('gestion_proveedores/', views.gestion_proveedores, name='gestion_proveedores'),
    path('detalle/<int:pk>/', views.detalle_proveedor, name='detalle_proveedor'),
    path('estado/<int:pk>/', views.cambiar_estado_proveedor, name='cambiar_estado_proveedor'),
    # Ruta para cargar los datos en el formulario y actualizar
    path('editar/<int:pk>/', views.editar_proveedor, name='editar_proveedor'),
    # Ruta para eliminar de forma segura
    path('eliminar/<int:pk>/', views.eliminar_proveedor, name='eliminar_proveedor'),
]