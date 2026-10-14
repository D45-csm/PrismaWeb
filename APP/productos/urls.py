from django.urls import path
from . import views

urlpatterns = [
    path('', views.productos_view, name='productos'),
    path('temporada/', views.temporada_view, name='temporada'),
]