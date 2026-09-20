"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path , include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('usuarios/', include('APP.usuarios.urls')),
    path('respaldo/', include('APP.respaldo.urls')),
    path('reserva/', include('APP.reserva.urls')),
    path('recetas/', include('APP.recetas.urls')),
    path('proveedores/', include('APP.proveedores.urls')),
    path('productos/', include('APP.productos.urls')),
    path('inventario/', include('APP.inventario.urls')),
    path('comprobantes/', include('APP.comprobantes.urls')),
    path('compra_insumos/', include('APP.compra_insumos.urls')),
    path('carrito/', include('APP.carrito.urls')),
    path('insumos/', include('APP.insumos.urls')),
]
