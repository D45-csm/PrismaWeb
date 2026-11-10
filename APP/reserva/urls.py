from django.urls import path

from . import views

urlpatterns = [
    path('gestion/', views.gestion_reservas, name='gestion_reservas'),
    path(
        'gestion/notificacion/<int:pk>/',
        views.consultar_notificacion_reserva,
        name='consultar_notificacion_reserva',
    ),
    path('consultar/', views.consultar_reserva, name='consultar_reserva'),
    path('consultar/<int:pk>/', views.reserva_cliente, name='reserva_cliente'),
    path('', views.reservas_view, name='reservas'),
]