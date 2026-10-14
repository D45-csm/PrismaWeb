from django.urls import path, reverse_lazy

from . import views
from django.contrib.auth import views as auth_views
from .forms import ClientePasswordResetForm

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path(
        'verificar/<uidb64>/<token>/',
        views.verificar_correo_view,
        name='verificar_correo',
    ),
    path(
        'recuperar/',
        views.ClientePasswordResetView.as_view(
            form_class=ClientePasswordResetForm,
            template_name='usuarios/recuperar.html',
            email_template_name='usuarios/password_reset_email.txt',
            subject_template_name='usuarios/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='recuperar',
    ),
    path(
        'recuperar/enviado/',
        views.ClientePasswordResetDoneView.as_view(
            template_name='usuarios/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'recuperar/confirmar/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='usuarios/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'recuperar/completado/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='usuarios/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
    path('perfil/', views.profile_view, name='perfil'),
    path('Lista_usuarios/', views.lista_usuarios, name='Lista de usuarios'),
]