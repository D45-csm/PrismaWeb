import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods

from .forms import (
    AdminLoginForm,
    CodigoRecuperacionForm,
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

RECOVERY_CODE_MAX_ATTEMPTS = 5
RECOVERY_CODE_LOCKOUT = timedelta(minutes=15)
RECOVERY_GRANT_TTL = timedelta(minutes=10)


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
            codigo_recuperacion = f'{secrets.randbelow(100_000_000):08d}'
            usuario.recovery_code_hash = make_password(codigo_recuperacion)
            usuario.save(update_fields=['recovery_code_hash'])
            login(
                request,
                usuario,
                backend='django.contrib.auth.backends.ModelBackend',
            )
            request.session['codigo_recuperacion_mostrar'] = codigo_recuperacion
            messages.success(request, 'Tu cuenta Prisma está lista. ¡Bienvenido!')
            return redirect('codigo_recuperacion_cuenta')
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
        'next_is_recovery_code': (
            next_url.split('?', 1)[0] == reverse('codigo_recuperacion_cuenta')
        ),
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
        {
            'form': form,
            'admin_login': True,
        },
    )


@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
@never_cache
def codigo_recuperacion_cuenta_view(request):
    """Create or display once the customer's offline recovery code."""
    if es_administrador(request.user):
        return redirect('perfil')

    if request.method == 'POST':
        codigo = f'{secrets.randbelow(100_000_000):08d}'
        request.user.recovery_code_hash = make_password(codigo)
        request.user.recovery_code_attempts = 0
        request.user.recovery_code_locked_until = None
        request.user.recovery_reset_grant_hash = ''
        request.user.recovery_reset_grant_expires_at = None
        request.user.save(update_fields=[
            'recovery_code_hash',
            'recovery_code_attempts',
            'recovery_code_locked_until',
            'recovery_reset_grant_hash',
            'recovery_reset_grant_expires_at',
        ])
        request.session['codigo_recuperacion_mostrar'] = codigo
        return redirect('codigo_recuperacion_cuenta')

    codigo = request.session.pop('codigo_recuperacion_mostrar', None)
    return render(request, 'usuarios/codigo_recuperacion_cuenta.html', {
        'codigo': codigo,
        'tiene_codigo': bool(request.user.recovery_code_hash),
    })


@require_http_methods(['GET', 'POST'])
def recuperar_view(request):
    """Paso 1: identificar la cuenta y mostrar o regenerar el código de recuperación."""
    if request.method == 'POST':
        form = RecuperarPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            usuario = Usuario.objects.filter(
                email__iexact=email,
                is_active=True,
                is_staff=False,
                is_superuser=False,
            ).order_by('pk').first()

            request.session.pop('password_reset_user_id', None)
            request.session.pop('password_reset_nonce', None)
            request.session.pop('password_reset_expires_at', None)
            request.session['recovery_email'] = email

            if usuario:
                codigo = f'{secrets.randbelow(100_000_000):08d}'
                usuario.recovery_code_hash = make_password(codigo)
                usuario.recovery_code_attempts = 0
                usuario.recovery_code_locked_until = None
                usuario.recovery_reset_grant_hash = ''
                usuario.recovery_reset_grant_expires_at = None
                usuario.save(update_fields=[
                    'recovery_code_hash',
                    'recovery_code_attempts',
                    'recovery_code_locked_until',
                    'recovery_reset_grant_hash',
                    'recovery_reset_grant_expires_at',
                ])
                request.session['codigo_recuperacion_mostrar'] = codigo
                messages.info(
                    request,
                    'Hemos generado un código nuevo para tu cuenta. Copia este código y úsalo para recuperar tu contraseña.',
                )
            else:
                request.session.pop('codigo_recuperacion_mostrar', None)
                messages.error(
                    request,
                    'No encontramos una cuenta activa con ese correo para recuperar la contraseña.',
                )

            return redirect('recuperar_codigo')
    else:
        form = RecuperarPasswordForm()

    return render(request, 'usuarios/recuperar.html', {'form': form})


@require_http_methods(['GET', 'POST'])
@never_cache
def recuperar_codigo_view(request):
    """Paso 2: verificar y consumir el código personal de recuperación."""
    email = request.session.get('recovery_email')
    if not email:
        return redirect('recuperar')

    usuario = Usuario.objects.filter(
        email__iexact=email,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    ).order_by('pk').first()

    codigo_a_mostrar = request.session.pop('codigo_recuperacion_mostrar', None)

    if request.method == 'POST':
        form = CodigoRecuperacionForm(request.POST)
        if form.is_valid() and usuario:
            with transaction.atomic():
                cuenta = Usuario.objects.select_for_update().filter(
                    pk=usuario.pk,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                ).first()
                ahora = timezone.now()
                if (
                    cuenta
                    and cuenta.recovery_code_locked_until
                    and cuenta.recovery_code_locked_until <= ahora
                ):
                    cuenta.recovery_code_attempts = 0
                    cuenta.recovery_code_locked_until = None
                vigente = (
                    cuenta is not None
                    and bool(cuenta.recovery_code_hash)
                    and cuenta.recovery_code_attempts < RECOVERY_CODE_MAX_ATTEMPTS
                    and (
                        cuenta.recovery_code_locked_until is None
                        or cuenta.recovery_code_locked_until <= ahora
                    )
                )

                if vigente and check_password(
                    form.cleaned_data['code'],
                    cuenta.recovery_code_hash,
                ):
                    nonce = secrets.token_urlsafe(32)
                    cuenta.recovery_code_hash = ''
                    cuenta.recovery_code_attempts = 0
                    cuenta.recovery_code_locked_until = None
                    cuenta.recovery_reset_grant_hash = make_password(nonce)
                    cuenta.recovery_reset_grant_expires_at = (
                        timezone.now() + RECOVERY_GRANT_TTL
                    )
                    cuenta.save(update_fields=[
                        'recovery_code_hash',
                        'recovery_code_attempts',
                        'recovery_code_locked_until',
                        'recovery_reset_grant_hash',
                        'recovery_reset_grant_expires_at',
                    ])
                    request.session.cycle_key()
                    request.session.pop('recovery_email', None)
                    request.session['password_reset_user_id'] = cuenta.pk
                    request.session['password_reset_nonce'] = nonce
                    request.session['password_reset_expires_at'] = int(
                        cuenta.recovery_reset_grant_expires_at.timestamp()
                    )
                    request.session.set_expiry(int(RECOVERY_GRANT_TTL.total_seconds()))
                    return redirect('recuperar_nueva_contrasena')

                if cuenta and cuenta.recovery_code_hash:
                    intentos = cuenta.recovery_code_attempts + 1
                    if intentos >= RECOVERY_CODE_MAX_ATTEMPTS:
                        cuenta.recovery_code_attempts = RECOVERY_CODE_MAX_ATTEMPTS
                        cuenta.recovery_code_locked_until = ahora + RECOVERY_CODE_LOCKOUT
                    else:
                        cuenta.recovery_code_attempts = intentos
                    cuenta.save(update_fields=[
                        'recovery_code_attempts',
                        'recovery_code_locked_until',
                    ])

        messages.error(
            request,
            'El código no es válido, ya se utilizó, está bloqueado temporalmente o no se ha generado para esta cuenta. '
            'Si no tienes uno, vuelve a "¿Olvidaste tu contraseña?" para generarlo otra vez.',
        )
    else:
        form = CodigoRecuperacionForm()

    return render(request, 'usuarios/codigo_recuperacion.html', {
        'form': form,
        'codigo': codigo_a_mostrar,
    })


@require_http_methods(['GET', 'POST'])
def recuperar_nueva_contrasena_view(request):
    """Step 3: save a password using the short-lived verification grant."""
    user_id = request.session.get('password_reset_user_id')
    nonce = request.session.get('password_reset_nonce')
    expires_at = request.session.get('password_reset_expires_at')
    try:
        sesion_vigente = bool(expires_at) and int(expires_at) > int(timezone.now().timestamp())
    except (TypeError, ValueError):
        sesion_vigente = False

    if not user_id or not nonce or not sesion_vigente:
        request.session.pop('password_reset_user_id', None)
        request.session.pop('password_reset_nonce', None)
        request.session.pop('password_reset_expires_at', None)
        messages.error(request, 'La verificación venció. Inicia sesión para generar un código nuevo.')
        return redirect('recuperar')

    usuario = Usuario.objects.filter(
        pk=user_id,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    ).first()
    if not usuario:
        request.session.flush()
        messages.error(request, 'La verificación ya no es válida. Inténtalo de nuevo.')
        return redirect('recuperar')

    grant_vigente = (
        bool(usuario.recovery_reset_grant_hash)
        and usuario.recovery_reset_grant_expires_at is not None
        and usuario.recovery_reset_grant_expires_at > timezone.now()
        and check_password(nonce, usuario.recovery_reset_grant_hash)
    )
    if not grant_vigente:
        request.session.flush()
        messages.error(request, 'La verificación venció. Inicia sesión para generar un código nuevo.')
        return redirect('recuperar')

    if request.method == 'POST':
        form = NuevaContrasenaForm(usuario, request.POST)
        if form.is_valid():
            with transaction.atomic():
                cuenta = Usuario.objects.select_for_update().filter(
                    pk=usuario.pk,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                    recovery_reset_grant_expires_at__gt=timezone.now(),
                ).first()
                if (
                    not cuenta
                    or not cuenta.recovery_reset_grant_hash
                    or not check_password(nonce, cuenta.recovery_reset_grant_hash)
                ):
                    request.session.flush()
                    messages.error(
                        request,
                        'La verificación ya se utilizó o venció. Inténtalo de nuevo.',
                    )
                    return redirect('recuperar')

                cuenta.set_password(form.cleaned_data['new_password1'])
                cuenta.recovery_reset_grant_hash = ''
                cuenta.recovery_reset_grant_expires_at = None
                cuenta.recovery_code_hash = ''
                cuenta.recovery_code_attempts = 0
                cuenta.recovery_code_locked_until = None
                cuenta.save(update_fields=[
                    'password',
                    'recovery_reset_grant_hash',
                    'recovery_reset_grant_expires_at',
                    'recovery_code_hash',
                    'recovery_code_attempts',
                    'recovery_code_locked_until',
                ])
            request.session.flush()
            messages.success(
                request,
                'Tu contraseña fue actualizada correctamente. Ya puedes iniciar sesión.',
            )
            return redirect('login')
    else:
        form = NuevaContrasenaForm(usuario)

    return render(request, 'usuarios/recuperar_nueva_contrasena.html', {
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
