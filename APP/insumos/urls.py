from django.urls import path
from . import views

urlpatterns = [
    path('', views.gestion_categorias, name='gestion_insumos'),
    path('detalle/<int:pk>/', views.detalle_insumo, name='detalle_insumo'),
    path('categorias/', views.gestion_categorias, name='gestion_categorias_insumos'),
]