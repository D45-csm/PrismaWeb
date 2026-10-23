import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.db import transaction
from django.db.models import Count, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
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
    RolForm,
)
from .models import Usuario
from APP.compra_insumos.models import DetalleCompraInsumo
from APP.insumos.models import Insumo
from APP.productos.models import Producto
from APP.reserva.models import Reserva
from APP.ventas.models import DetalleVenta
from .permissions import exigir_permiso, usuario_puede_acceder

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
    if request.method == 'POST':
        exigir_permiso(request, 'usuarios.change_usuario')
        exigir_permiso(request, 'auth.change_group')
        usuario_id = request.POST.get('usuario_id', '')
        if not usuario_id.isdecimal() or len(usuario_id) > 18:
            raise Http404
        usuario = Usuario.objects.filter(pk=int(usuario_id)).first()
        if usuario is None:
            raise Http404
        if usuario.pk == request.user.pk:
            raise PermissionDenied
        rol_id = request.POST.get('rol', '')
        if rol_id:
            if not rol_id.isdecimal() or len(rol_id) > 18:
                raise Http404
            rol = Group.objects.filter(pk=int(rol_id)).first()
            if rol is None:
                raise Http404
            usuario.groups.set([rol])
            messages.success(request, f'Rol de "{usuario.username}" actualizado a "{rol.name}".')
        else:
            usuario.groups.clear()
            messages.success(request, f'Se quitó el rol de "{usuario.username}".')
        return redirect('Lista de usuarios')

    exigir_permiso(request, 'usuarios.view_usuario')
    usuarios = Usuario.objects.prefetch_related('groups').order_by('username')
    return render(request, 'usuarios/lista_usuarios.html', {
        'usuarios': usuarios,
        'roles': Group.objects.order_by('name'),
        'usuario_actual_id': request.user.pk,
        'total_usuarios': Usuario.objects.count(),
        'usuarios_activos': Usuario.objects.filter(is_active=True).count(),
        'puede_cambiar_roles': usuario_puede_acceder(
            request.user,
            'auth.change_group',
        ),
    })


def _render_gestion_roles(request, form=None, rol_actual=None):
    roles = Group.objects.annotate(
        usuarios_asignados=Count('user'),
    ).order_by('name')
    return render(request, 'usuarios/gestion_roles.html', {
        'roles': roles,
        'total_roles': Group.objects.count(),
        'form': form or RolForm(instance=rol_actual),
        'rol_actual': rol_actual,
        'modo_edicion': rol_actual is not None,
    })


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
def gestion_roles(request):
    exigir_permiso(request, 'auth.view_group')
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion in ('crear_rol', 'editar_rol'):
            exigir_permiso(
                request,
                'auth.add_group' if accion == 'crear_rol' else 'auth.change_group',
            )
            rol_actual = None
            if accion == 'editar_rol':
                rol_id = request.POST.get('rol_id', '')
                if not rol_id.isdecimal() or len(rol_id) > 18:
                    raise Http404
                rol_actual = get_object_or_404(Group, pk=int(rol_id))
            form = RolForm(request.POST, instance=rol_actual)
            if form.is_valid():
                rol = form.save()
                messages.success(
                    request,
                    f'Rol "{rol.name}" '
                    f'{"actualizado" if rol_actual else "creado"} correctamente.',
                )
                return redirect('gestion_roles')
            return _render_gestion_roles(request, form=form, rol_actual=rol_actual)

        if accion == 'eliminar_rol':
            exigir_permiso(request, 'auth.delete_group')
            rol_id = request.POST.get('rol_id', '')
            if not rol_id.isdecimal() or len(rol_id) > 18:
                raise Http404
            rol = get_object_or_404(Group, pk=int(rol_id))
            nombre_rol = rol.name
            rol.delete()
            messages.success(
                request,
                f'El rol "{nombre_rol}" fue eliminado y se quitaron sus asignaciones.',
            )
            return redirect('gestion_roles')

        messages.error(request, 'No se reconoció la acción solicitada.')

    rol_actual = None
    edit_id = request.GET.get('editar_rol', '')
    if edit_id:
        if not edit_id.isdecimal() or len(edit_id) > 18:
            raise Http404
        rol_actual = get_object_or_404(Group, pk=int(edit_id))
    return _render_gestion_roles(request, rol_actual=rol_actual)


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
            request.session.pop('password_reset_user_id', None)
            request.session.pop('password_reset_nonce', None)
            request.session.pop('password_reset_expires_at', None)
            request.session['recovery_email'] = email
            messages.info(
                request,
                'Si la cuenta existe, ingresa el código personal que guardaste para continuar.',
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
    permisos = {
        'usuarios': usuario_puede_acceder(request.user, 'usuarios.view_usuario'),
        'roles': usuario_puede_acceder(request.user, 'auth.view_group'),
        'proveedores': usuario_puede_acceder(
            request.user,
            'proveedores.view_proveedor',
        ),
        'reservas': usuario_puede_acceder(request.user, 'reserva.view_reserva'),
        'inventario': usuario_puede_acceder(request.user, 'insumos.view_insumo'),
        'compras': usuario_puede_acceder(
            request.user,
            'compra_insumos.view_compra_insumo',
        ),
        'productos': usuario_puede_acceder(request.user, 'productos.view_producto'),
        'insumos': usuario_puede_acceder(request.user, 'insumos.view_insumo'),
        'ventas': usuario_puede_acceder(request.user, 'ventas.view_venta'),
    }
    ventas_hoy = 0
    if permisos['ventas']:
        ventas_hoy = DetalleVenta.objects.filter(
            venta__fecha=hoy,
        ).aggregate(total=Sum(F('cantidad') * F('costo_unitario_producto')))['total'] or 0
    context = {
        'permisos_modulos': permisos,
        'total_reservas_hoy': (
            Reserva.objects.filter(fecha_reserva=hoy).count()
            if permisos['reservas'] else 0
        ),
        'ventas_hoy': ventas_hoy,
        'total_productos': Producto.objects.count() if permisos['productos'] else 0,
        'total_insumos': (
            Insumo.objects.filter(activo=True).count() if permisos['insumos'] else 0
        ),
        'reservas_recientes': (
            Reserva.objects.order_by('-fecha_realizacion')[:5]
            if permisos['reservas'] else ()
        ),
        'insumos_recientes': (
            Insumo.objects.filter(activo=True).select_related(
                'categoria',
            ).order_by('nombre')[:10]
            if permisos['inventario'] else ()
        ),
        'compras_recientes': (
            DetalleCompraInsumo.objects.select_related(
                'compra__proveedor',
                'insumo',
            ).order_by('-compra__fecha')[:5]
            if permisos['compras'] else ()
        ),
        'productos_recientes': (
            Producto.objects.select_related('categoria').order_by('-id')[:10]
            if permisos['productos'] else ()
        ),
    }
    return render(request, 'usuarios/perfil.html', context)
