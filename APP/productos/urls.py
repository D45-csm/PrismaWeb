from django.urls import path
from . import views


urlpatterns = [

    path('lista_productos/', views.gestion_productos, name='lista_productos'),

    path('categorias/', views.gestionar_categoria_producto, name='gestionar_categoria_producto'),

    path('crear/', views.crear_producto, name='crear_producto'),

    path('editar/<int:id>/', views.editar_producto,name='editar_producto'),

    path('detalle/<int:id>/', views.detalle_producto, name='detalle_producto'),

    path('eliminar/<int:id>/', views.eliminar_producto,name='eliminar_producto'),

]