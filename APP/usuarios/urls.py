from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path(
        'codigo-recuperacion/',
        views.codigo_recuperacion_cuenta_view,
        name='codigo_recuperacion_cuenta',
    ),
    path('recuperar/', views.recuperar_view, name='recuperar'),
    path(
        'recuperar/codigo/',
        views.recuperar_codigo_view,
        name='recuperar_codigo',
    ),
    path(
        'recuperar/nueva-contrasena/',
        views.recuperar_nueva_contrasena_view,
        name='recuperar_nueva_contrasena',
    ),
    path('perfil/', views.profile_view, name='perfil'),
    path('Lista_usuarios/', views.lista_usuarios, name='Lista de usuarios'),
    path('roles/', views.gestion_roles, name='gestion_roles'),
]