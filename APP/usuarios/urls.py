from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('admin-login/', views.legacy_admin_login_redirect, name='admin_login'),
    path(
        'admin-login/recuperar/',
        views.admin_recuperar_view,
        name='admin_recuperar',
    ),
    path(
        'admin-login/recuperar/codigo/',
        views.admin_recuperar_codigo_view,
        name='admin_recuperar_codigo',
    ),
    path(
        'admin-login/recuperar/nueva-contrasena/',
        views.admin_recuperar_nueva_contrasena_view,
        name='admin_recuperar_nueva_contrasena',
    ),
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
        'recuperar/codigo/continuar/',
        views.recuperar_codigo_email_link_view,
        name='recuperar_codigo_email_link',
    ),
    path(
        'recuperar/nueva-contrasena/',
        views.recuperar_nueva_contrasena_view,
        name='recuperar_nueva_contrasena',
    ),
    path('perfil/', views.profile_view, name='perfil'),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    path('Lista_usuarios/', views.lista_usuarios, name='Lista de usuarios'),
    path('Lista_usuarios/<int:pk>/detalle/', views.detalle_usuario, name='detalle_usuario'),
    path(
        'Lista_usuarios/<int:pk>/estado/',
        views.cambiar_estado_usuario,
        name='cambiar_estado_usuario',
    ),
    path(
        'Lista_usuarios/<int:pk>/eliminar/',
        views.eliminar_usuario,
        name='eliminar_usuario',
    ),
    path('roles/', views.gestion_roles, name='gestion_roles'),
]