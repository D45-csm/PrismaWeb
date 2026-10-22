from django.urls import path
from . import views

urlpatterns = [
    path('', views.carrito_view, name='carrito'),
]