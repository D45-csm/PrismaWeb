import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F, Sum
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import (
    url_has_allowed_host_and_scheme,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)
from django.views.decorators.http import require_POST, require_http_methods

from .forms import (
    AdminLoginForm,
    LoginForm,
    NuevaContrasenaForm,
    RecuperarPasswordForm,
    RegistroForm,
)
from .models import Usuario
from APP.compra_insumos.models import DetalleCompraInsumo
from APP.insumos.models import Insumo
from APP.productos.models import Producto
from APP.reserva.models import Reserva
from APP.ventas.models import DetalleVenta

logger = logging.getLogger(__name__)


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
            usuario = form.save()
            login(request, usuario)
            messages.success(request, 'Tu cuenta Prisma está lista. ¡Bienvenido!')
            return redirect('base_cliente')
    else:
        form = RegistroForm()
    return render(request, 'usuarios/registro.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(redireccion_post_login(request.user))

    next_url = request.POST.get('next') or request.GET.get('next', '')
    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if request.POST.get('remember_me') == 'on':
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                request.session.set_expiry(0)
            messages.success(request, 'Inicio de sesión exitoso.')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('base_cliente')
    else:
        form = LoginForm()
    return render(request, 'usuarios/login.html', {
        'form': form,
        'next': next_url,
    })


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


def _enviar_correo_recuperacion(request, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    enlace = request.build_absolute_uri(
        reverse('recuperar_confirmar', kwargs={'uidb64': uid, 'token': token})
    )
    asunto = 'Recupera tu contraseña - Prisma'
    mensaje = render_to_string('usuarios/email/recuperar_contrasena.txt', {
        'usuario': usuario,
        'enlace': enlace,
    })
    try:
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [usuario.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('No se pudo enviar el correo de recuperación de contraseña.')


@require_http_methods(['GET', 'POST'])
def recuperar_view(request):
    """Primer paso de la recuperación de contraseña: el cliente pide el enlace a su correo."""
    if request.method == 'POST':
        form = RecuperarPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            usuario = Usuario.objects.filter(
                email__iexact=email,
                is_active=True,
                is_staff=False,
                is_superuser=False,
            ).first()
            if usuario:
                _enviar_correo_recuperacion(request, usuario)

            # Mismo mensaje exista o no la cuenta: evita revelar qué correos están registrados.
            messages.success(
                request,
                'Si el correo está registrado, te enviamos un enlace para '
                'restablecer tu contraseña. Revisa tu bandeja de entrada y spam.',
            )
            return redirect('recuperar')
    else:
        form = RecuperarPasswordForm()

    return render(request, 'usuarios/recuperar.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def recuperar_confirmar_view(request, uidb64, token):
    """Segundo paso: el cliente define su nueva contraseña desde el enlace del correo."""
    usuario = None
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(
            pk=uid,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        usuario = None

    token_valido = usuario is not None and default_token_generator.check_token(usuario, token)

    if not token_valido:
        return render(request, 'usuarios/recuperar_confirmar.html', {
            'token_valido': False,
        })

    if request.method == 'POST':
        form = NuevaContrasenaForm(usuario, request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Tu contraseña fue actualizada correctamente. Ya puedes iniciar sesión.',
            )
            return redirect('login')
    else:
        form = NuevaContrasenaForm(usuario)

    return render(request, 'usuarios/recuperar_confirmar.html', {
        'token_valido': True,
        'form': form,
    })


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
