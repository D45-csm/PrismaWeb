from django.urls import path

from . import views

urlpatterns = [
    path('', views.gestion_recetas, name='lista_recetas'),
    path('operaciones/', views.operaciones_recetas, name='operaciones_recetas'),
    path(
        'operaciones/<int:pk>/realizar/',
        views.realizar_operacion_receta,
        name='realizar_operacion_receta',
    ),
]