import secrets
import logging
import smtplib
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.http import Http404, JsonResponse
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods

from .forms import (
    CodigoRecuperacionForm,
    LoginForm,
    NuevaContrasenaForm,
    PerfilForm,
    RecuperarPasswordForm,
    RegistroForm,
    RolForm,
    UsuarioAdminForm,
)
from .models import Usuario
from APP.compra_insumos.models import DetalleCompraInsumo
from APP.insumos.models import Insumo
from APP.productos.models import Producto
from APP.reserva.models import Reserva
from APP.ventas.models import DetalleVenta
from .permissions import (
    ROL_CLIENTE,
    exigir_permiso,
    usuario_puede_acceder,
    usuario_puede_entrar_panel,
)

RECOVERY_CODE_MAX_ATTEMPTS = 5
RECOVERY_CODE_LOCKOUT = timedelta(minutes=15)
RECOVERY_CODE_TTL = timedelta(minutes=10)
RECOVERY_GRANT_TTL = timedelta(minutes=10)
logger = logging.getLogger(__name__)


def es_administrador(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def redireccion_post_login(user):
    return 'perfil' if usuario_puede_entrar_panel(user) else 'base_cliente'


def _login_rate_limit_keys(request, identifier):
    ip_address = request.META.get('REMOTE_ADDR', 'unknown')
    ip_hash = salted_hmac('APP.usuarios.login.ip', ip_address).hexdigest()
    keys = [f'login:ip:{ip_hash}']
    if identifier:
        identifier_hash = salted_hmac(
            'APP.usuarios.login.identifier',
            f'{ip_address}:{identifier.casefold()}',
        ).hexdigest()
        keys.append(f'login:identity:{identifier_hash}')
    return keys


def _login_is_rate_limited(keys):
    return (
        cache.get(keys[0], 0) >= settings.LOGIN_RATE_LIMIT_IP_MAX_ATTEMPTS
        or (
            len(keys) > 1
            and cache.get(keys[1], 0) >= settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
        )
    )


def _record_login_failure(keys):
    for key in keys:
        if not cache.add(key, 1, timeout=settings.LOGIN_RATE_LIMIT_WINDOW):
            try:
                cache.incr(key)
            except ValueError:
                cache.add(key, 1, timeout=settings.LOGIN_RATE_LIMIT_WINDOW)


def _puede_cambiar_roles(request, usuario=None):
    return (
        (usuario is None or usuario.pk != request.user.pk)
        and usuario_puede_acceder(request.user, 'usuarios.change_usuario')
        and usuario_puede_acceder(request.user, 'auth.change_group')
    )


def _render_lista_usuarios(
    request,
    form=None,
    modal_open='',
    usuario_actual=None,
):
    puede_cambiar_roles = _puede_cambiar_roles(request, usuario_actual)
    query = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', 'activos')
    usuarios = Usuario.objects.prefetch_related('groups')
    if estado == 'activos':
        usuarios = usuarios.filter(is_active=True)
    elif estado == 'inactivos':
        usuarios = usuarios.filter(is_active=False)
    else:
        estado = 'todos'
    if query:
        usuarios = usuarios.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(telefono__icontains=query)
        )
    return render(request, 'usuarios/lista_usuarios.html', {
        'usuarios': usuarios.order_by('username'),
        'roles': Group.objects.order_by('name'),
        'usuario_actual_id': request.user.pk,
        'total_usuarios': Usuario.objects.count(),
        'usuarios_activos': Usuario.objects.filter(is_active=True).count(),
        'usuarios_inactivos': Usuario.objects.filter(is_active=False).count(),
        'puede_cambiar_roles': puede_cambiar_roles,
        'puede_agregar_usuarios': usuario_puede_acceder(
            request.user,
            'usuarios.add_usuario',
        ),
        'puede_cambiar_usuarios': usuario_puede_acceder(
            request.user,
            'usuarios.change_usuario',
        ),
        'puede_eliminar_usuarios': usuario_puede_acceder(
            request.user,
            'usuarios.delete_usuario',
        ),
        'query': query,
        'estado': estado,
        'form': form or UsuarioAdminForm(
            instance=usuario_actual,
            include_role=puede_cambiar_roles,
        ),
        'usuario_actual': usuario_actual,
        'modo_edicion': usuario_actual is not None,
        'modal_open': modal_open,
    })


@login_required(login_url='login')
@user_passes_test(usuario_puede_entrar_panel, login_url='login')
def lista_usuarios(request):
    exigir_permiso(request, 'usuarios.view_usuario')
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'crear_usuario':
            exigir_permiso(request, 'usuarios.add_usuario')
            puede_asignar_rol = _puede_cambiar_roles(request)
            form = UsuarioAdminForm(
                request.POST,
                include_role=puede_asignar_rol,
            )
            if form.is_valid():
                usuario = form.save()
                if puede_asignar_rol:
                    rol = form.cleaned_data['rol']
                    usuario.groups.set([rol] if rol else [])
                messages.success(
                    request,
                    f'Usuario "{usuario.username}" creado correctamente.',
                )
                return redirect(request.path)
            return _render_lista_usuarios(request, form=form, modal_open='crear')

        if accion == 'editar_usuario':
            exigir_permiso(request, 'usuarios.change_usuario')
            usuario_id = request.POST.get('usuario_id', '')
            if not usuario_id.isdecimal() or len(usuario_id) > 18:
                raise Http404
            usuario = get_object_or_404(Usuario, pk=int(usuario_id))
            puede_asignar_rol = _puede_cambiar_roles(request, usuario)
            form = UsuarioAdminForm(
                request.POST,
                instance=usuario,
                include_role=puede_asignar_rol,
            )
            if form.is_valid():
                usuario = form.save()
                if puede_asignar_rol:
                    rol = form.cleaned_data['rol']
                    usuario.groups.set([rol] if rol else [])
                messages.success(
                    request,
                    f'Usuario "{usuario.username}" actualizado correctamente.',
                )
                return redirect(request.path)
            return _render_lista_usuarios(
                request,
                form=form,
                modal_open='editar',
                usuario_actual=usuario,
            )

        if accion:
            messages.error(request, 'No se reconoció la acción solicitada.')
            return redirect(request.path)

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
            rol = Group.objects.filter(
                pk=int(rol_id),
                estado_rol__is_active=True,
            ).first()
            if rol is None:
                raise Http404
            usuario.groups.set([rol])
            messages.success(request, f'Rol de "{usuario.username}" actualizado a "{rol.name}".')
        else:
            usuario.groups.clear()
            messages.success(request, f'Se quitó el rol de "{usuario.username}".')
        return redirect('Lista de usuarios')

    usuario_actual = None
    edit_id = request.GET.get('editar_usuario', '')
    if edit_id:
        if not edit_id.isdecimal() or len(edit_id) > 18:
            raise Http404
        usuario_actual = get_object_or_404(Usuario, pk=int(edit_id))
    return _render_lista_usuarios(
        request,
        modal_open='editar' if usuario_actual else request.GET.get('modal', ''),
        usuario_actual=usuario_actual,
    )


@login_required(login_url='login')
@user_passes_test(usuario_puede_entrar_panel, login_url='login')
def detalle_usuario(request, pk):
    exigir_permiso(request, 'usuarios.view_usuario')
    usuario = get_object_or_404(Usuario.objects.prefetch_related('groups'), pk=pk)
    roles = ', '.join(usuario.groups.values_list('name', flat=True))
    puede_cambiar = usuario.pk != request.user.pk and usuario_puede_acceder(
        request.user,
        'usuarios.change_usuario',
    )
    return JsonResponse({
        'id': usuario.pk,
        'nombre': usuario.username,
        'descripcion': 'Cuenta de usuario',
        'meta': [
            f'Correo: {usuario.email}' if usuario.email else 'Sin correo registrado',
            f'Teléfono: {usuario.telefono}' if usuario.telefono else 'Sin teléfono',
            f'Rol: {roles}' if roles else 'Sin rol asignado',
        ],
        'imagen': '',
        'activo': usuario.is_active,
        'puede_editar': usuario_puede_acceder(
            request.user,
            'usuarios.change_usuario',
        ),
        'puede_cambiar_estado': puede_cambiar,
        'edit_url': f'{reverse("Lista de usuarios")}?editar_usuario={usuario.pk}',
        'status_url': reverse('cambiar_estado_usuario', args=[usuario.pk]),
    })


@login_required(login_url='login')
@user_passes_test(usuario_puede_entrar_panel, login_url='login')
@require_POST
def cambiar_estado_usuario(request, pk):
    exigir_permiso(request, 'usuarios.change_usuario')
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario.pk == request.user.pk:
        raise PermissionDenied
    valor = request.POST.get('activo')
    if valor not in ('true', 'false'):
        return JsonResponse(
            {'error': 'Selecciona si el usuario está activo.'},
            status=400,
        )
    usuario.is_active = valor == 'true'
    usuario.save(update_fields=['is_active'])
    return JsonResponse({
        'id': usuario.pk,
        'activo': usuario.is_active,
        'message': (
            'Usuario activado correctamente.'
            if usuario.is_active else 'Usuario desactivado correctamente.'
        ),
    })


@login_required(login_url='login')
@user_passes_test(usuario_puede_entrar_panel, login_url='login')
@require_POST
def eliminar_usuario(request, pk):
    exigir_permiso(request, 'usuarios.delete_usuario')
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario.pk == request.user.pk:
        raise PermissionDenied
    nombre = usuario.username
    try:
        usuario.delete()
    except ProtectedError:
        messages.error(
            request,
            f'No se puede eliminar a "{nombre}" porque tiene registros asociados.',
        )
    else:
        messages.success(request, f'El usuario "{nombre}" ha sido eliminado.')
    return redirect('Lista de usuarios')


def _render_gestion_roles(request, form=None, rol_actual=None):
    roles = Group.objects.annotate(
        usuarios_asignados=Count('user'),
    ).select_related('estado_rol').order_by('name')
    return render(request, 'usuarios/gestion_roles.html', {
        'roles': roles,
        'total_roles': Group.objects.count(),
        'form': form or RolForm(instance=rol_actual),
        'rol_actual': rol_actual,
        'modo_edicion': rol_actual is not None,
    })


@login_required(login_url='login')
@user_passes_test(usuario_puede_entrar_panel, login_url='login')
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
                if rol_actual.name.casefold() == ROL_CLIENTE.casefold():
                    messages.error(request, f'El rol "{ROL_CLIENTE}" está protegido.')
                    return redirect('gestion_roles')
            form = RolForm(request.POST, instance=rol_actual)
            if form.is_valid():
                if (
                    rol_actual
                    and rol_actual.estado_rol.is_active
                    and not form.cleaned_data['is_active']
                    and (
                        not usuario_puede_entrar_panel(
                            request.user,
                            excluding_group_id=rol_actual.pk,
                        )
                        or not usuario_puede_acceder(
                            request.user,
                            'auth.change_group',
                            excluding_group_id=rol_actual.pk,
                        )
                    )
                ):
                    form.add_error(
                        'is_active',
                        'No puedes desactivar el rol porque perderías el acceso para administrarlo.',
                    )
                    return _render_gestion_roles(
                        request,
                        form=form,
                        rol_actual=rol_actual,
                    )
                with transaction.atomic():
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
            if rol.name.casefold() == ROL_CLIENTE.casefold():
                messages.error(request, f'El rol "{ROL_CLIENTE}" no se puede eliminar.')
                return redirect('gestion_roles')
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
        if rol_actual.name.casefold() == ROL_CLIENTE.casefold():
            messages.error(request, f'El rol "{ROL_CLIENTE}" está protegido.')
            return redirect('gestion_roles')
    return _render_gestion_roles(request, rol_actual=rol_actual)


def registro_view(request):
    if request.user.is_authenticated:
        return redirect(redireccion_post_login(request.user))

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                usuario = form.save()
                rol_cliente, _ = Group.objects.get_or_create(name=ROL_CLIENTE)
                usuario.groups.add(rol_cliente)
            login(
                request,
                usuario,
                backend=settings.AUTHENTICATION_BACKENDS[0],
            )
            messages.success(request, 'Tu cuenta Prisma está lista. ¡Bienvenido!')
            return redirect('base_cliente')
    else:
        form = RegistroForm()
    return render(request, 'usuarios/registro.html', {'form': form})


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect(redireccion_post_login(request.user))

    next_url = request.POST.get('next') or request.GET.get('next', '')
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()[:254]
        rate_limit_keys = _login_rate_limit_keys(request, identifier)
        form = LoginForm(request=request, data=request.POST)
        if _login_is_rate_limited(rate_limit_keys):
            wait_minutes = max(1, (settings.LOGIN_RATE_LIMIT_WINDOW + 59) // 60)
            form.add_error(
                None,
                f'Demasiados intentos. Espera {wait_minutes} minutos e inténtalo de nuevo.',
            )
            return render(
                request,
                'usuarios/login.html',
                {
                    'form': form,
                    'next': next_url,
                    'next_is_recovery_code': (
                        next_url.split('?', 1)[0]
                        == reverse('codigo_recuperacion_cuenta')
                    ),
                },
                status=429,
            )
        if form.is_valid():
            usuario = form.get_user()
            cache.delete_many(rate_limit_keys)
            login(request, usuario)
            if (
                not usuario_puede_entrar_panel(usuario)
                and request.POST.get('remember_me') == 'on'
            ):
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                request.session.set_expiry(0)
            messages.success(
                request,
                'Acceso administrativo concedido.'
                if es_administrador(usuario)
                else (
                    'Acceso al panel concedido.'
                    if usuario_puede_entrar_panel(usuario)
                    else 'Inicio de sesión exitoso.'
                ),
            )
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect(redireccion_post_login(usuario))
        _record_login_failure(rate_limit_keys)
    else:
        form = LoginForm()
    return render(request, 'usuarios/login.html', {
        'form': form,
        'next': next_url,
        'next_is_recovery_code': (
            next_url.split('?', 1)[0] == reverse('codigo_recuperacion_cuenta')
        ),
    })


def legacy_admin_login_redirect(request):
    return redirect('login')


@require_http_methods(['GET', 'POST'])
@never_cache
def admin_recuperar_view(request):
    return _recuperar_view(request, admin_only=True)


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
        request.user.email_recovery_code_hash = ''
        request.user.email_recovery_code_expires_at = None
        request.user.recovery_code_attempts = 0
        request.user.recovery_code_locked_until = None
        request.user.recovery_reset_grant_hash = ''
        request.user.recovery_reset_grant_expires_at = None
        request.user.save(update_fields=[
            'recovery_code_hash',
            'email_recovery_code_hash',
            'email_recovery_code_expires_at',
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


@never_cache
def recuperar_view(request):
    return _recuperar_view(request, admin_only=False)


@never_cache
def _recuperar_view(request, admin_only):
    """Send a short-lived recovery code only to the matching account type."""
    email_session_key = 'admin_recovery_email' if admin_only else 'recovery_email'
    reset_prefix = 'admin_password_reset' if admin_only else 'password_reset'
    code_url = 'admin_recuperar_codigo' if admin_only else 'recuperar_codigo'
    form = RecuperarPasswordForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            request.session.pop(f'{reset_prefix}_user_id', None)
            request.session.pop(f'{reset_prefix}_nonce', None)
            request.session.pop(f'{reset_prefix}_expires_at', None)
            request.session[email_session_key] = email
            if not admin_only:
                request.session.pop('codigo_recuperacion_mostrar', None)

            usuario = _recovery_account_queryset(admin_only).filter(
                email__iexact=email,
            ).order_by('pk').first()
            if usuario:
                ahora = timezone.now()
                if (
                    admin_only
                    and usuario.admin_recovery_code_sent_at
                    and usuario.admin_recovery_code_sent_at
                    > ahora - RECOVERY_CODE_TTL
                ):
                    messages.info(
                        request,
                        'Si el correo corresponde a una cuenta administrativa activa, '
                        'recibirás instrucciones. Si no llegan, inténtalo más tarde.',
                    )
                    return redirect(code_url)

                if (
                    admin_only
                    and usuario.email_recovery_code_hash
                    and usuario.email_recovery_code_expires_at
                    and usuario.email_recovery_code_expires_at > ahora
                ):
                    messages.info(
                        request,
                        'Si el correo corresponde a una cuenta administrativa activa, '
                        'recibirás instrucciones. Si no llegan, inténtalo más tarde.',
                    )
                    return redirect(code_url)

                codigo = f'{secrets.randbelow(100_000_000):08d}'
                usuario.email_recovery_code_hash = make_password(codigo)
                usuario.email_recovery_code_expires_at = ahora + RECOVERY_CODE_TTL
                usuario.recovery_code_attempts = 0
                usuario.recovery_code_locked_until = None
                usuario.recovery_reset_grant_hash = ''
                usuario.recovery_reset_grant_expires_at = None
                update_fields = [
                    'email_recovery_code_hash',
                    'email_recovery_code_expires_at',
                    'recovery_code_attempts',
                    'recovery_code_locked_until',
                    'recovery_reset_grant_hash',
                    'recovery_reset_grant_expires_at',
                ]
                if admin_only:
                    usuario.admin_recovery_code_sent_at = ahora
                    update_fields.append('admin_recovery_code_sent_at')
                usuario.save(update_fields=update_fields)
                try:
                    if admin_only:
                        subject = 'Código seguro para tu acceso administrativo de Prisma'
                        text_template = 'usuarios/email/recuperar_contrasena_admin.txt'
                        html_template = 'usuarios/email/recuperar_contrasena_admin.html'
                        email_context = {
                            'usuario': usuario,
                            'codigo': codigo,
                            'logo_url': request.build_absolute_uri(
                                static('img/logo_prisma.png')
                            ),
                        }
                    else:
                        subject = 'Código para restablecer tu contraseña de Prisma'
                        text_template = 'usuarios/email/recuperar_contrasena.txt'
                        html_template = 'usuarios/email/recuperar_contrasena.html'
                        email_context = {
                            'usuario': usuario,
                            'codigo': codigo,
                            'logo_url': request.build_absolute_uri(
                                static('img/logo_prisma.png')
                            ),
                            'email_link_url': request.build_absolute_uri(
                                reverse('recuperar_codigo_email_link')
                            ) + '#' + urlencode({'email': usuario.email, 'code': codigo}),
                        }
                    email = EmailMultiAlternatives(
                        subject,
                        render_to_string(text_template, email_context),
                        settings.DEFAULT_FROM_EMAIL,
                        [usuario.email],
                    )
                    email.attach_alternative(
                        render_to_string(html_template, email_context),
                        'text/html',
                    )
                    email_enviado = email.send(fail_silently=False)
                except (OSError, smtplib.SMTPException):
                    logger.exception('No se pudo enviar el código de recuperación.')
                    email_enviado = 0

                if not email_enviado:
                    usuario.email_recovery_code_hash = ''
                    usuario.email_recovery_code_expires_at = None
                    update_fields = [
                        'email_recovery_code_hash',
                        'email_recovery_code_expires_at',
                    ]
                    if admin_only:
                        usuario.admin_recovery_code_sent_at = None
                        update_fields.append('admin_recovery_code_sent_at')
                    usuario.save(update_fields=update_fields)
                    if not admin_only:
                        messages.error(
                            request,
                            'No pudimos enviar el correo. Inténtalo de nuevo más tarde.',
                        )
                        return render(request, 'usuarios/recuperar.html', {'form': form})

            messages.info(
                request,
                (
                    'Si el correo corresponde a una cuenta administrativa activa, '
                    'recibirás instrucciones. Si no llegan, inténtalo más tarde.'
                    if admin_only
                    else
                    'Si existe una cuenta con ese correo, enviamos un código de verificación. '
                    'Revisa tu bandeja de entrada y la carpeta de spam.'
                ),
            )
            return redirect(code_url)

    return render(request, 'usuarios/recuperar.html', {
        'form': form,
        'admin_recovery': admin_only,
    })


@require_http_methods(['GET', 'POST'])
@never_cache
def recuperar_codigo_view(request):
    return _recuperar_codigo_view(request, admin_only=False)


@require_http_methods(['GET', 'POST'])
@never_cache
def admin_recuperar_codigo_view(request):
    return _recuperar_codigo_view(request, admin_only=True)


def _recovery_account_queryset(admin_only):
    usuarios = Usuario.objects.filter(is_active=True)
    if admin_only:
        return usuarios.filter(Q(is_staff=True) | Q(is_superuser=True))
    return usuarios.filter(is_staff=False, is_superuser=False)


def _recuperar_codigo_view(request, admin_only):
    """Verify and consume a short-lived code for the selected account type."""
    email_session_key = 'admin_recovery_email' if admin_only else 'recovery_email'
    reset_prefix = 'admin_password_reset' if admin_only else 'password_reset'
    recovery_url = 'admin_recuperar' if admin_only else 'recuperar'
    new_password_url = (
        'admin_recuperar_nueva_contrasena'
        if admin_only else 'recuperar_nueva_contrasena'
    )
    email = request.session.get(email_session_key)
    if not email and request.method == 'POST':
        email = request.POST.get('recovery_email', '').strip().lower()
        if email:
            request.session[email_session_key] = email
    if not email:
        return redirect(recovery_url)

    usuario = _recovery_account_queryset(admin_only).filter(
        email__iexact=email,
    ).order_by('pk').first()

    codigo_a_mostrar = (
        None
        if admin_only
        else request.session.pop('codigo_recuperacion_mostrar', None)
    )

    if request.method == 'POST':
        form = CodigoRecuperacionForm(request.POST)
        if form.is_valid() and usuario:
            with transaction.atomic():
                cuenta = _recovery_account_queryset(admin_only).select_for_update().filter(
                    pk=usuario.pk,
                ).first()
                ahora = timezone.now()
                if (
                    cuenta
                    and cuenta.recovery_code_locked_until
                    and cuenta.recovery_code_locked_until <= ahora
                ):
                    cuenta.recovery_code_attempts = 0
                    cuenta.recovery_code_locked_until = None
                codigo_email_vigente = (
                    cuenta is not None
                    and bool(cuenta.email_recovery_code_hash)
                    and cuenta.email_recovery_code_expires_at is not None
                    and cuenta.email_recovery_code_expires_at > ahora
                )
                codigo_respaldo_vigente = (
                    not admin_only
                    and cuenta is not None
                    and bool(cuenta.recovery_code_hash)
                )
                vigente = (
                    (codigo_email_vigente or codigo_respaldo_vigente)
                    and cuenta.recovery_code_attempts < RECOVERY_CODE_MAX_ATTEMPTS
                    and (
                        cuenta.recovery_code_locked_until is None
                        or cuenta.recovery_code_locked_until <= ahora
                    )
                )

                codigo_ingresado = form.cleaned_data['code']
                codigo_valido = (
                    codigo_email_vigente
                    and check_password(codigo_ingresado, cuenta.email_recovery_code_hash)
                ) or (
                    codigo_respaldo_vigente
                    and check_password(codigo_ingresado, cuenta.recovery_code_hash)
                )
                if vigente and codigo_valido:
                    nonce = secrets.token_urlsafe(32)
                    cuenta.recovery_code_hash = ''
                    cuenta.email_recovery_code_hash = ''
                    cuenta.email_recovery_code_expires_at = None
                    cuenta.recovery_code_attempts = 0
                    cuenta.recovery_code_locked_until = None
                    cuenta.recovery_reset_grant_hash = make_password(nonce)
                    cuenta.recovery_reset_grant_expires_at = (
                        timezone.now() + RECOVERY_GRANT_TTL
                    )
                    cuenta.save(update_fields=[
                        'recovery_code_hash',
                        'email_recovery_code_hash',
                        'email_recovery_code_expires_at',
                        'recovery_code_attempts',
                        'recovery_code_locked_until',
                        'recovery_reset_grant_hash',
                        'recovery_reset_grant_expires_at',
                    ])
                    request.session.cycle_key()
                    request.session.pop(email_session_key, None)
                    request.session[f'{reset_prefix}_user_id'] = cuenta.pk
                    request.session[f'{reset_prefix}_nonce'] = nonce
                    request.session[f'{reset_prefix}_expires_at'] = int(
                        cuenta.recovery_reset_grant_expires_at.timestamp()
                    )
                    request.session.set_expiry(int(RECOVERY_GRANT_TTL.total_seconds()))
                    return redirect(new_password_url)

                if cuenta and (
                    cuenta.recovery_code_hash or cuenta.email_recovery_code_hash
                ):
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
            'Solicita otro código desde "¿Olvidaste tu contraseña?".',
        )
    else:
        form = CodigoRecuperacionForm()

    return render(request, 'usuarios/codigo_recuperacion.html', {
        'form': form,
        'codigo': codigo_a_mostrar,
        'admin_recovery': admin_only,
    })


@require_http_methods(['GET'])
@never_cache
def recuperar_codigo_email_link_view(request):
    """Render a landing page that submits the email link's fragment securely."""
    return render(request, 'usuarios/codigo_recuperacion.html', {
        'form': CodigoRecuperacionForm(),
        'email_link': True,
    })


@require_http_methods(['GET', 'POST'])
@never_cache
def recuperar_nueva_contrasena_view(request):
    return _recuperar_nueva_contrasena_view(request, admin_only=False)


@require_http_methods(['GET', 'POST'])
@never_cache
def admin_recuperar_nueva_contrasena_view(request):
    return _recuperar_nueva_contrasena_view(request, admin_only=True)


def _recuperar_nueva_contrasena_view(request, admin_only):
    """Save a password using the short-lived grant for the selected account type."""
    reset_prefix = 'admin_password_reset' if admin_only else 'password_reset'
    recovery_url = 'admin_recuperar' if admin_only else 'recuperar'
    login_url = 'login'
    user_id = request.session.get(f'{reset_prefix}_user_id')
    nonce = request.session.get(f'{reset_prefix}_nonce')
    expires_at = request.session.get(f'{reset_prefix}_expires_at')
    try:
        sesion_vigente = bool(expires_at) and int(expires_at) > int(timezone.now().timestamp())
    except (TypeError, ValueError):
        sesion_vigente = False

    if not user_id or not nonce or not sesion_vigente:
        request.session.pop(f'{reset_prefix}_user_id', None)
        request.session.pop(f'{reset_prefix}_nonce', None)
        request.session.pop(f'{reset_prefix}_expires_at', None)
        messages.error(request, 'La verificación venció. Inicia sesión para generar un código nuevo.')
        return redirect(recovery_url)

    usuario = _recovery_account_queryset(admin_only).filter(pk=user_id).first()
    if not usuario:
        request.session.flush()
        messages.error(request, 'La verificación ya no es válida. Inténtalo de nuevo.')
        return redirect(recovery_url)

    grant_vigente = (
        bool(usuario.recovery_reset_grant_hash)
        and usuario.recovery_reset_grant_expires_at is not None
        and usuario.recovery_reset_grant_expires_at > timezone.now()
        and check_password(nonce, usuario.recovery_reset_grant_hash)
    )
    if not grant_vigente:
        request.session.flush()
        messages.error(request, 'La verificación venció. Inicia sesión para generar un código nuevo.')
        return redirect(recovery_url)

    if request.method == 'POST':
        form = NuevaContrasenaForm(usuario, request.POST)
        if form.is_valid():
            with transaction.atomic():
                cuenta = _recovery_account_queryset(admin_only).select_for_update().filter(
                    pk=usuario.pk,
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
                    return redirect(recovery_url)

                cuenta.set_password(form.cleaned_data['new_password1'])
                cuenta.recovery_reset_grant_hash = ''
                cuenta.recovery_reset_grant_expires_at = None
                cuenta.recovery_code_hash = ''
                cuenta.email_recovery_code_hash = ''
                cuenta.email_recovery_code_expires_at = None
                cuenta.recovery_code_attempts = 0
                cuenta.recovery_code_locked_until = None
                cuenta.save(update_fields=[
                    'password',
                    'recovery_reset_grant_hash',
                    'recovery_reset_grant_expires_at',
                    'recovery_code_hash',
                    'email_recovery_code_hash',
                    'email_recovery_code_expires_at',
                    'recovery_code_attempts',
                    'recovery_code_locked_until',
                ])
            request.session.flush()
            messages.success(
                request,
                'Tu contraseña fue actualizada correctamente. Ya puedes iniciar sesión.',
            )
            return redirect(login_url)
    else:
        form = NuevaContrasenaForm(usuario)

    return render(request, 'usuarios/recuperar_nueva_contrasena.html', {
        'form': form,
        'admin_recovery': admin_only,
    })


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('base_cliente')


@login_required(login_url='login')
@user_passes_test(usuario_puede_entrar_panel, login_url='login')
@require_http_methods(['GET', 'POST'])
def editar_perfil_view(request):
    if request.method == 'POST':
        perfil_form = PerfilForm(request.POST, instance=request.user)
        if request.POST.get('form_type') != 'profile':
            messages.error(request, 'No se pudo identificar el formulario enviado.')
        elif perfil_form.is_valid():
            perfil_form.save()
            messages.success(request, 'Tus datos de perfil se actualizaron correctamente.')
            return redirect('editar_perfil')
    else:
        perfil_form = PerfilForm(instance=request.user)

    return render(request, 'usuarios/editar_perfil.html', {
        'perfil_form': perfil_form,
    })


@login_required(login_url='login')
@user_passes_test(usuario_puede_entrar_panel, login_url='login')
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
