from django.urls import path

from . import views

urlpatterns = [
    path('', views.inventario_dashboard, name='inventario_dashboard'),
    path(
        'historial/',
        views.historial_movimientos,
        name='historial_movimientos',
    ),
    path(
        'movimientos/<int:pk>/anular/',
        views.anular_movimiento,
        name='anular_movimiento',
    ),
    path(
        'reporte.pdf',
        views.exportar_inventario_pdf,
        name='exportar_inventario_pdf',
    ),
]