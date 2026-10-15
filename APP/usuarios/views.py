from smtplib import SMTPException

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.db import transaction
from django.http import Http404
from django.db.models import F, Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import AdminLoginForm, LoginForm, RegistroForm
from .models import Usuario
from .tokens import email_verification_token
from APP.compra_insumos.models import DetalleCompraInsumo
from APP.insumos.models import Insumo
from APP.productos.models import Producto
from APP.reserva.models import Reserva
from APP.ventas.models import DetalleVenta


def es_administrador(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def redireccion_post_login(user):
    return 'perfil' if es_administrador(user) else 'base_cliente'


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
def lista_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'usuarios/lista_usuarios.html', {'usuarios': usuarios})


def registro_view(request):
    if request.user.is_authenticated:
        return redirect(redireccion_post_login(request.user))

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    usuario = form.save()
                    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
                    token = email_verification_token.make_token(usuario)
                    current_site = get_current_site(request)
                    verification_url = (
                        f'{"https" if request.is_secure() else "http"}://'
                        f'{current_site.domain}'
                        f'{reverse("verificar_correo", kwargs={"uidb64": uid, "token": token})}'
                    )
                    send_mail(
                        'Confirma tu correo de Prisma',
                        (
                            f'Hola {usuario.username},\n\n'
                            'Confirma que este correo te pertenece abriendo este enlace:\n'
                            f'{verification_url}\n\n'
                            f'Si no creaste una cuenta en {current_site.name}, ignora este mensaje.'
                        ),
                        None,
                        [usuario.email],
                        fail_silently=False,
                    )
            except (OSError, SMTPException, ImproperlyConfigured, ValueError):
                form.add_error(
                    None,
                    'No pudimos enviar el correo de verificación. Revisa la configuración del correo e inténtalo otra vez.',
                )
            else:
                messages.success(
                    request,
                    'Te enviamos un enlace de verificación. Confirma tu correo antes de iniciar sesión.',
                )
                return redirect('registro')
    else:
        form = RegistroForm()
    return render(request, 'usuarios/registro.html', {'form': form})


def verificar_correo_view(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        raise Http404('El enlace de verificación no es válido.')

    if usuario.is_active:
        messages.info(request, 'Este correo ya fue verificado. Inicia sesión para continuar.')
        return redirect('login')
    if not email_verification_token.check_token(usuario, token):
        messages.error(request, 'El enlace de verificación venció o no es válido.')
        return redirect('registro')

    usuario.is_active = True
    usuario.save(update_fields=['is_active'])
    login(request, usuario)
    messages.success(request, 'Correo verificado. Tu cuenta de cliente está lista.')
    return redirect('base_cliente')


def login_view(request):
    if request.user.is_authenticated:
        return redirect(redireccion_post_login(request.user))

    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if request.POST.get('remember_me') == 'on':
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                request.session.set_expiry(0)
            messages.success(request, 'Inicio de sesión exitoso.')
            return redirect('base_cliente')
    else:
        form = LoginForm()
    return render(request, 'usuarios/login.html', {'form': form})


def admin_login_view(request):
    if es_administrador(request.user):
        return redirect('perfil')

    if request.method == 'POST':
        form = AdminLoginForm(request=request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, 'Acceso administrativo concedido.')
            return redirect('perfil')
    else:
        form = AdminLoginForm()
    return render(
        request,
        'usuarios/login.html',
        {'form': form, 'admin_login': True},
    )


def recuperar_view(request):
    return render(request, 'usuarios/recuperar.html')


class ClientePasswordResetView(auth_views.PasswordResetView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email_console'] = (
            settings.EMAIL_BACKEND
            == 'django.core.mail.backends.console.EmailBackend'
        )
        return context


class ClientePasswordResetDoneView(auth_views.PasswordResetDoneView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email_console'] = (
            settings.EMAIL_BACKEND
            == 'django.core.mail.backends.console.EmailBackend'
        )
        return context


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('base_cliente')


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
def profile_view(request):
    hoy = timezone.localdate()
    ventas_hoy = DetalleVenta.objects.filter(
        venta__fecha=hoy,
    ).aggregate(total=Sum(F('cantidad') * F('costo_unitario_producto')))['total'] or 0
    context = {
        'total_reservas_hoy': Reserva.objects.filter(fecha_reserva=hoy).count(),
        'ventas_hoy': ventas_hoy,
        'total_productos': Producto.objects.count(),
        'total_insumos': Insumo.objects.filter(activo=True).count(),
        'reservas_recientes': Reserva.objects.order_by('-fecha_realizacion')[:5],
        'insumos_recientes': Insumo.objects.filter(activo=True).select_related(
            'categoria',
        ).order_by('nombre')[:10],
        'compras_recientes': DetalleCompraInsumo.objects.select_related(
            'compra__proveedor',
            'insumo',
        ).order_by('-compra__fecha')[:5],
        'productos_recientes': Producto.objects.select_related(
            'categoria',
        ).order_by('-id')[:10],
    }
    return render(request, 'usuarios/perfil.html', context)
