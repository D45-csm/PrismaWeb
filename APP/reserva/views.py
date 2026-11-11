import logging
import re
import smtplib
from datetime import date, time
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import DetalleReserva, Reserva
from APP.productos.models import Producto
from APP.usuarios.permissions import (
    exigir_permiso,
    usuario_puede_acceder,
    usuario_puede_entrar_panel,
)


logger = logging.getLogger(__name__)

POSTRES = {
    'Manzana Verde Cheesecake': 15000,
    'Café Chocolate': 15000,
    'Fresa Chocolate': 15000,
    'Postre Personalizado': 15000,
}

SLOTS_PRODUCTOS = tuple(range(1, 6))
HORA_APERTURA_RESERVAS = time(14, 0)
HORA_CIERRE_RESERVAS = time(18, 30)


def _normalizar_telefono(telefono):
    return ''.join(digito for digito in telefono if digito.isdigit())


def _validar_disponibilidad_insumos(productos_lineas):
    """
    Valida disponibilidad y stock de insumos según recetas antes de guardar (SCRUM-1248, SCRUM-1266).
    productos_lineas es una lista de tuplas (producto, cantidad).
    """
    try:
        from APP.recetas.models import Receta, RecetaInsumo
        from APP.inventario.models import Movimiento
        from django.db.models import Sum
    except ImportError:
        return True

    for producto, cantidad in productos_lineas:
        if not producto.activo:
            raise ValueError(f"El producto '{producto.nombre}' no se encuentra disponible actualmente.")

        # Buscar recetas vinculadas por nombre de producto
        recetas = Receta.objects.filter(nombre__iexact=producto.nombre, activo=True)
        for receta in recetas:
            for ri in RecetaInsumo.objects.filter(receta=receta).select_related('insumo'):
                insumo = ri.insumo
                if not insumo.activo:
                    raise ValueError(f"El insumo '{insumo.nombre}' necesario para '{producto.nombre}' no está disponible.")

                # Si hay movimientos registrados en el inventario para este insumo, verificar stock
                if Movimiento.objects.filter(insumo=insumo).exists():
                    entradas = Movimiento.objects.filter(insumo=insumo, accion='ENTRADA').aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
                    salidas = Movimiento.objects.filter(insumo=insumo, accion='SALIDA').aggregate(total=Sum('cantidad'))['total'] or Decimal('0')
                    stock_disponible = Decimal(str(entradas)) - Decimal(str(salidas))
                    requerido = Decimal(str(ri.cantidad_insumo)) * Decimal(str(cantidad))
                    if stock_disponible < requerido:
                        raise ValueError(
                            f"Stock insuficiente del insumo '{insumo.nombre}' para preparar {cantidad}x '{producto.nombre}'. "
                            f"Disponible: {stock_disponible} {ri.medida_insumo}, Requerido: {requerido} {ri.medida_insumo}."
                        )
    return True


def _datos_reserva(post_data, reserva=None):
    nombre = post_data.get('nombre', '').strip()
    telefono = post_data.get('telefono', '').strip()
    fecha_texto = post_data.get('fecha', '').strip()
    hora_texto = post_data.get('hora', '').strip()
    modalidad = post_data.get('tipo_reserva', '').strip()
    canal = post_data.get('canal_origen', 'Web').strip() or 'Web'
    detalles = post_data.get('detalles', '').strip()

    if canal not in dict(Reserva.choices_canal):
        canal = 'Web'

    if not nombre or len(nombre) > 100:
        raise ValueError('Ingresa el nombre del cliente (máximo 100 caracteres).')
    if not re.fullmatch(r'\+?[\d\s().-]{7,30}', telefono):
        raise ValueError('Ingresa un número de teléfono válido.')
    if len(_normalizar_telefono(telefono)) < 7:
        raise ValueError('Ingresa un número de teléfono válido.')
    if modalidad not in dict(Reserva.choices_tipo_reserva):
        raise ValueError('Selecciona una modalidad válida.')
    try:
        fecha_reserva = date.fromisoformat(fecha_texto)
        hora_reserva = time.fromisoformat(hora_texto)
    except (TypeError, ValueError):
        raise ValueError('Ingresa una fecha y una hora válidas.') from None

    if not HORA_APERTURA_RESERVAS <= hora_reserva <= HORA_CIERRE_RESERVAS:
        raise ValueError('El horario de reservas es de 2:00 PM a 6:30 PM.')

    ahora = timezone.localtime()
    if fecha_reserva < timezone.localdate() or (
        fecha_reserva == timezone.localdate()
        and hora_reserva <= ahora.time().replace(second=0, microsecond=0)
    ):
        raise ValueError('La fecha y la hora de la reserva no pueden estar en el pasado.')
    if len(detalles) > 500:
        raise ValueError('Las indicaciones no pueden superar 500 caracteres.')

    personas_texto = post_data.get('numero_personas', '').strip()
    numero_personas = None
    if personas_texto:
        try:
            numero_personas = int(personas_texto)
        except ValueError:
            raise ValueError('Ingresa un número de personas válido.') from None
        if not 1 <= numero_personas <= 50:
            raise ValueError('El número de personas debe estar entre 1 y 50.')
    if modalidad == 'Mesa' and numero_personas is None:
        raise ValueError('Indica cuántas personas asistirán para reservar una mesa.')

    lineas = []
    ids_producto = []
    for slot in SLOTS_PRODUCTOS:
        producto_id = post_data.get(f'producto_id_{slot}', '').strip()
        cantidad_texto = post_data.get(f'cantidad_{slot}', '').strip()
        if not producto_id:
            if cantidad_texto not in ('', '1'):
                raise ValueError('Selecciona un producto para cada cantidad indicada.')
            continue
        if not producto_id.isdecimal() or len(producto_id) > 18:
            raise ValueError('Uno de los productos seleccionados no es válido.')
        try:
            cantidad = int(cantidad_texto)
        except ValueError:
            raise ValueError('Indica una cantidad válida para cada producto.') from None
        if not 1 <= cantidad <= 50:
            raise ValueError('La cantidad de cada producto debe estar entre 1 y 50.')
        ids_producto.append(int(producto_id))
        lineas.append((int(producto_id), cantidad))

    if not lineas:
        raise ValueError('Selecciona al menos un producto para la reserva.')
    if len(set(ids_producto)) != len(ids_producto):
        raise ValueError('Selecciona cada producto una sola vez.')

    ids_anteriores = (
        reserva.lineas.exclude(producto_id=None).values_list('producto_id', flat=True)
        if reserva else ()
    )
    productos = {
        producto.pk: producto
        for producto in Producto.objects.filter(pk__in=ids_producto).filter(
            Q(activo=True) | Q(pk__in=ids_anteriores)
        )
    }
    if len(productos) != len(ids_producto):
        raise ValueError('Uno de los productos ya no está disponible.')

    productos_tuplas = [(productos[pk], cantidad) for pk, cantidad in lineas]
    _validar_disponibilidad_insumos(productos_tuplas)

    return {
        'nombre_cliente': nombre,
        'telefono': telefono,
        'fecha_reserva': fecha_reserva,
        'hora': hora_reserva,
        'numero_personas': numero_personas,
        'tipo_reserva': modalidad,
        'canal_origen': canal,
        'detalles': detalles,
    }, productos_tuplas


def _guardar_reserva(request, reserva=None):
    datos, productos = _datos_reserva(request.POST, reserva=reserva)
    with transaction.atomic():
        if reserva is None:
            reserva = Reserva.objects.create(
                **datos,
                usuario=request.user if request.user.is_authenticated else None,
                estado=(
                    'Pendiente de pago'
                    if datos['tipo_reserva'] == 'Para llevar'
                    else 'Pendiente'
                ),
            )
        else:
            lineas_anteriores = sorted(
                (
                    linea.producto_id,
                    linea.nombre_producto,
                    linea.cantidad,
                    linea.precio_unitario,
                )
                for linea in reserva.lineas.all()
            )
            lineas_nuevas = sorted(
                (producto.pk, producto.nombre, cantidad, producto.precio)
                for producto, cantidad in productos
            )
            cambio_reserva = (
                lineas_anteriores != lineas_nuevas
                or any(
                    getattr(reserva, campo) != datos[campo]
                    for campo in (
                        'fecha_reserva',
                        'hora',
                        'numero_personas',
                        'tipo_reserva',
                    )
                )
            )
            for campo, valor in datos.items():
                setattr(reserva, campo, valor)
            fields = list(datos)
            if cambio_reserva:
                reserva.pago_confirmado = False
                reserva.fecha_pago_confirmado = None
                reserva.estado = (
                    'Pendiente de pago'
                    if datos['tipo_reserva'] == 'Para llevar'
                    else 'Pendiente'
                )
                fields.extend([
                    'pago_confirmado',
                    'fecha_pago_confirmado',
                    'estado',
                ])
            reserva.save(update_fields=fields)
            reserva.lineas.all().delete()
        DetalleReserva.objects.bulk_create([
            DetalleReserva(
                reserva=reserva,
                producto=producto,
                nombre_producto=producto.nombre,
                cantidad=cantidad,
                precio_unitario=producto.precio,
            )
            for producto, cantidad in productos
        ])
    return reserva


def _formatear_cop(valor):
    return f'${valor:,.0f}'.replace(',', '.')


def _url_whatsapp_reserva(reserva):
    lineas = list(reserva.lineas.all())
    productos_texto = [
        f'- {linea.cantidad} x {linea.nombre_producto}: '
        f'{_formatear_cop(linea.subtotal)}'
        for linea in lineas
    ]
    encabezado = 'SOLICITUD DE PEDIDO PARA LLEVAR · PRISMA' if (
        reserva.tipo_reserva == 'Para llevar'
    ) else 'SOLICITUD DE RESERVA DE MESA · PRISMA'
    mensaje = '\n'.join([
        encabezado,
        f'Reserva #{reserva.pk}',
        f'Cliente: {reserva.nombre_cliente}',
        f'Teléfono: {reserva.telefono}',
        (
            f'Fecha: {reserva.fecha_reserva:%d/%m/%Y}'
            + (f' · {reserva.hora:%H:%M}' if reserva.hora else '')
        ),
        (
            f'Personas: {reserva.numero_personas}'
            if reserva.tipo_reserva == 'Mesa'
            else 'Modalidad: Para llevar'
        ),
        'Productos:',
        *productos_texto,
        f'Total del pedido: {_formatear_cop(reserva.total)} COP',
        f'Indicaciones: {reserva.detalles or "Sin indicaciones especiales."}',
        (
            'Solicito los medios de pago para pagar el pedido anticipadamente. '
            'Enviaré el comprobante por este chat. Entiendo que el pedido se confirma '
            'cuando Prisma verifique el pago.'
            if reserva.tipo_reserva == 'Para llevar'
            else 'Solicito confirmar la disponibilidad de la mesa. Entiendo que la '
            'reserva queda confirmada cuando Prisma responda por este chat.'
        ),
    ])
    return (
        f'https://wa.me/{settings.RESERVAS_WHATSAPP_DESTINO}'
        f'?text={quote(mensaje)}'
    )


def _notificar_reserva(reserva, request, confirmada=False):
    lineas = list(reserva.lineas.all())
    cuerpo = '\n'.join([
        f'Reserva #{reserva.pk}',
        f'Cliente: {reserva.nombre_cliente}',
        f'Teléfono: {reserva.telefono}',
        f'Fecha: {reserva.fecha_reserva:%d/%m/%Y}',
        f'Hora: {reserva.hora:%H:%M}',
        f'Modalidad: {reserva.tipo_reserva}',
        f'Personas: {reserva.numero_personas or "No aplica"}',
        f'Estado: {reserva.estado}',
        f'Total: {_formatear_cop(reserva.total)} COP',
        f'Pago anticipado verificado: {"Sí" if reserva.pago_confirmado else "No"}',
        'Productos:',
        *[f'- {linea.cantidad} x {linea.nombre_producto}' for linea in lineas],
        f'Indicaciones: {reserva.detalles or "Sin indicaciones especiales."}',
        'Consultar y gestionar:',
        request.build_absolute_uri(reverse(
            'consultar_notificacion_reserva',
            args=[reserva.pk],
        )),
    ])
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.error('No se notificó la reserva #%s: faltan las credenciales SMTP.', reserva.pk)
        return False
    try:
        sent = send_mail(
            (
                f'Reserva Prisma #{reserva.pk} confirmada'
                if confirmada else f'Nueva reserva Prisma #{reserva.pk}'
            ),
            cuerpo,
            settings.DEFAULT_FROM_EMAIL,
            [settings.RESERVAS_EMAIL_DESTINO],
            fail_silently=False,
        ) == 1
    except (OSError, smtplib.SMTPException, ValueError):
        logger.exception('Falló la notificación de la reserva #%s.', reserva.pk)
        return False
    if not sent:
        logger.error('No se pudo notificar la reserva #%s.', reserva.pk)
    return sent


def _es_administrador(user):
    return usuario_puede_entrar_panel(user)


def _render_reserva_form(request, template='reservas/reservas.html', **context):
    status = context.pop('status', 200)
    productos = Producto.objects.filter(activo=True)
    reserva_actual = context.get('reserva') or context.get('reserva_editar')
    if reserva_actual:
        productos = Producto.objects.filter(
            Q(activo=True) | Q(pk__in=reserva_actual.lineas.values('producto_id'))
        )
        context.setdefault('reserva_total', _formatear_cop(reserva_actual.total))
        if template == 'reservas/detalle.html':
            context.setdefault('whatsapp_url', _url_whatsapp_reserva(reserva_actual))
    return render(request, template, {
        'productos': productos.order_by('nombre'),
        'slots_productos': SLOTS_PRODUCTOS,
        'estados_reserva': Reserva.choices_estado,
        'modalidades_reserva': Reserva.choices_tipo_reserva,
        'canales_reserva': Reserva.choices_canal,
        'opciones_asistencia': Reserva.choice_asistencia,
        'whatsapp_destino': settings.RESERVAS_WHATSAPP_DESTINO,
        **context,
    }, status=status)


def _slots_editables(reserva=None):
    lineas = list(reserva.lineas.all()) if reserva else []
    return [
        {
            'producto_id': lineas[index].producto_id if index < len(lineas) else '',
            'cantidad': lineas[index].cantidad if index < len(lineas) else 1,
        }
        for index in range(len(SLOTS_PRODUCTOS))
    ]


def _error_reserva(request, message, status=400):
    if 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'ok': False, 'error': message}, status=status)
    messages.error(request, message)
    return _render_reserva_form(request, status=status)


@require_http_methods(['GET', 'POST'])
def reservas_view(request):
    if request.method == 'GET':
        return _render_reserva_form(request)

    modalidad = request.POST.get('tipo_reserva', 'Para llevar' if 'postre' in request.POST else '').strip()
    if modalidad == 'Para llevar' and not request.user.is_authenticated:
        login_url = f"{reverse('login')}?next={reverse('reservas')}"
        error_msg = 'Para reservar tu postre para llevar debes iniciar sesión y después completar tu pago.'
        if 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'ok': False,
                'require_login': True,
                'error': error_msg,
                'login_url': login_url,
            }, status=401)
        messages.warning(request, error_msg)
        return redirect(login_url)

    if 'producto_id_1' in request.POST:
        try:
            reserva = _guardar_reserva(request)
        except ValueError as error:
            return _error_reserva(request, str(error))
        email_sent = _notificar_reserva(reserva, request)
        request.session[f'reserva_{reserva.pk}_access'] = True
        es_para_llevar = reserva.tipo_reserva == 'Para llevar'
        return JsonResponse({
            'ok': True,
            'title': (
                '¡Pedido para llevar registrado!'
                if es_para_llevar else '¡Recibimos tu solicitud de mesa!'
            ),
            'message': (
                'Tu pedido quedó guardado exitosamente. Ahora completa tu pago para asegurar la preparación de tus postres.'
                if es_para_llevar else
                'Recibimos tu solicitud de mesa. Te contactaremos por WhatsApp para darte la bienvenida y confirmar detalles.'
            ),
            'email_sent': email_sent,
            'total': _formatear_cop(reserva.total),
            'reservation_type': reserva.tipo_reserva,
            'reservation_id': reserva.pk,
            'pago_confirmado': reserva.pago_confirmado,
            'require_payment': es_para_llevar and not reserva.pago_confirmado,
            'next_url': reverse('reserva_cliente', args=[reserva.pk]),
            'whatsapp_url': _url_whatsapp_reserva(reserva),
            'fecha_formateada': reserva.fecha_reserva.strftime('%d/%m/%Y'),
            'hora_formateada': reserva.hora.strftime('%H:%M') if reserva.hora else '',
        }, status=201)

    nombre = request.POST.get('nombre', '').strip()
    telefono = request.POST.get('telefono', '').strip()
    fecha_texto = request.POST.get('fecha', '').strip()
    postre = request.POST.get('postre', '').strip()
    detalles = request.POST.get('detalles', '').strip()

    try:
        cantidad = int(request.POST.get('cantidad', ''))
        fecha_reserva = date.fromisoformat(fecha_texto)
    except (TypeError, ValueError):
        return JsonResponse(
            {'ok': False, 'error': 'Revisa la fecha y la cantidad de postres.'},
            status=400,
        )

    if not nombre or len(nombre) > 100:
        return JsonResponse(
            {'ok': False, 'error': 'Ingresa tu nombre (máximo 100 caracteres).'},
            status=400,
        )
    if not re.fullmatch(r'\+?[\d\s().-]{7,30}', telefono):
        return JsonResponse(
            {'ok': False, 'error': 'Ingresa un número de teléfono válido.'},
            status=400,
        )
    if fecha_reserva < timezone.localdate():
        return JsonResponse(
            {'ok': False, 'error': 'La fecha de entrega no puede estar en el pasado.'},
            status=400,
        )
    if postre not in POSTRES:
        return JsonResponse(
            {'ok': False, 'error': 'Selecciona uno de los postres disponibles.'},
            status=400,
        )
    if not 1 <= cantidad <= 50:
        return JsonResponse(
            {'ok': False, 'error': 'La cantidad debe estar entre 1 y 50 postres.'},
            status=400,
        )
    if len(detalles) > 500:
        return JsonResponse(
            {'ok': False, 'error': 'Las indicaciones no pueden superar 500 caracteres.'},
            status=400,
        )

    precio_unitario = POSTRES[postre]
    with transaction.atomic():
        reserva = Reserva.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            nombre_cliente=nombre,
            telefono=telefono,
            fecha_reserva=fecha_reserva,
            hora=None,
            detalles=detalles,
            tipo_reserva='Para llevar',
            estado='Pendiente de pago',
        )
        DetalleReserva.objects.create(
            reserva=reserva,
            producto=Producto.objects.filter(nombre__iexact=postre).first(),
            nombre_producto=postre,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
        )

    total = precio_unitario * cantidad
    precio_texto = f'${total:,}'.replace(',', '.') if precio_unitario else 'A cotizar'
    fecha_formateada = fecha_reserva.strftime('%d/%m/%Y')
    whatsapp_url = _url_whatsapp_reserva(reserva)
    request.session[f'reserva_{reserva.pk}_access'] = True

    email_sent = False
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.error('No se envió la reserva #%s: faltan las credenciales SMTP.', reserva.pk)
    else:
        asunto = f'Nueva reserva Prisma #{reserva.pk}'
        cuerpo = '\n'.join([
            f'Reserva #{reserva.pk}',
            f'Cliente: {nombre}',
            f'Teléfono: {telefono}',
            f'Fecha de entrega: {fecha_formateada}',
            f'Postre: {postre}',
            f'Cantidad: {cantidad}',
            f'Precio estimado: {precio_texto}',
            f'Indicaciones: {detalles or "Sin indicaciones especiales."}',
        ])
        try:
            email_sent = send_mail(
                asunto,
                cuerpo,
                settings.DEFAULT_FROM_EMAIL,
                [settings.RESERVAS_EMAIL_DESTINO],
                fail_silently=False,
            ) == 1
            if not email_sent:
                logger.error('No se pudo enviar el correo de la reserva #%s.', reserva.pk)
        except (OSError, smtplib.SMTPException, ValueError):
            logger.exception('Falló el envío de correo de la reserva #%s.', reserva.pk)

    mensaje = (
        'Tu pedido quedó registrado y se notificó al equipo. Completa tu pago seguro para confirmar.'
        if email_sent else
        'Tu pedido quedó registrado. Completa tu pago seguro para confirmar.'
    )

    return JsonResponse({
        'ok': True,
        'email_sent': email_sent,
        'message': mensaje,
        'title': '¡Pedido para llevar registrado!',
        'total': _formatear_cop(reserva.total),
        'reservation_type': reserva.tipo_reserva,
        'reservation_id': reserva.pk,
        'pago_confirmado': reserva.pago_confirmado,
        'require_payment': not reserva.pago_confirmado,
        'next_url': reverse('reserva_cliente', args=[reserva.pk]),
        'whatsapp_url': whatsapp_url,
    }, status=201)


@require_http_methods(['GET', 'POST'])
def consultar_reserva(request):
    if request.method == 'POST':
        reserva_id = request.POST.get('reserva_id', '').strip()
        telefono = _normalizar_telefono(request.POST.get('telefono', '').strip())
        if not reserva_id.isdecimal() or len(reserva_id) > 18:
            messages.error(request, 'Ingresa un número de reserva válido.')
        else:
            reserva = Reserva.objects.filter(pk=int(reserva_id)).first()
            if (
                reserva
                and telefono
                and telefono == _normalizar_telefono(reserva.telefono)
            ):
                request.session[f'reserva_{reserva.pk}_access'] = True
                return redirect('reserva_cliente', pk=reserva.pk)
            messages.error(request, 'El número de reserva o el teléfono no coinciden.')
    return render(request, 'reservas/consultar.html')


@login_required(login_url='login')
@require_http_methods(['GET'])
def mis_reservas(request):
    reservas = (
        Reserva.objects.filter(usuario=request.user)
        .prefetch_related('lineas')
        .order_by('-fecha_realizacion', '-pk')
    )
    return render(request, 'reservas/mis_reservas.html', {'reservas': reservas})


@require_http_methods(['POST'])
def pagar_reserva_cliente(request, pk):
    reserva = get_object_or_404(Reserva.objects.prefetch_related('lineas'), pk=pk)
    tiene_acceso = (
        request.session.get(f'reserva_{pk}_access')
        or (request.user.is_authenticated and reserva.usuario_id == request.user.pk)
        or usuario_puede_entrar_panel(request.user)
    )
    if not tiene_acceso:
        return JsonResponse({'ok': False, 'error': 'No tienes permiso para pagar esta reserva.'}, status=403)

    if reserva.tipo_reserva != 'Para llevar':
        return JsonResponse({'ok': False, 'error': 'Las reservas de mesa no requieren pago anticipado.'}, status=400)

    if reserva.estado in ('Cancelada', 'Realizada', 'No asistió'):
        return JsonResponse({'ok': False, 'error': 'Esta reserva ya no admite pagos.'}, status=400)

    if reserva.pago_confirmado:
        return JsonResponse({'ok': True, 'message': 'El pago de este pedido ya estaba verificado previamente.', 'pago_confirmado': True})

    metodo = request.POST.get('metodo_pago', 'Nequi').strip() or 'Nequi'

    with transaction.atomic():
        reserva.pago_confirmado = True
        reserva.fecha_pago_confirmado = timezone.now()
        reserva.estado = 'Confirmada'
        reserva.metodo_pago = metodo
        reserva.notificacion_consultada = False
        reserva.save(update_fields=[
            'pago_confirmado',
            'fecha_pago_confirmado',
            'estado',
            'metodo_pago',
            'notificacion_consultada',
        ])
        try:
            from APP.ventas.models import Comprobante
            Comprobante.objects.create(
                reserva=reserva,
                estado='Confirmado',
                direccion_comprobante=f'comprobantes/{metodo.lower()}_{reserva.pk}.pdf',
            )
        except Exception:
            pass

    _notificar_reserva(reserva, request, confirmada=True)

    mensaje_lindo = (
        '¡Pago recibido con éxito! 🎉🍰✨ '
        'Tu pedido está 100% confirmado. En Prisma estamos seleccionando los mejores '
        'ingredientes artesanales para que tu postre esté fresco, delicioso y listo para recoger '
        f'el {reserva.fecha_reserva.strftime("%d/%m/%Y")}'
        + (f' a las {reserva.hora.strftime("%H:%M")}' if reserva.hora else '')
        + '. ¡Muchísimas gracias por confiar en nosotros para endulzar tus momentos especiales!'
    )

    if 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'ok': True,
            'title': '¡Pago Recibido con Éxito! 🎉🍰',
            'message': mensaje_lindo,
            'reservation_id': reserva.pk,
            'total': _formatear_cop(reserva.total),
            'metodo_pago': metodo,
            'estado': reserva.estado,
            'pago_confirmado': True,
            'fecha_recogida': reserva.fecha_reserva.strftime('%d/%m/%Y'),
            'hora_recogida': reserva.hora.strftime('%H:%M') if reserva.hora else '',
            'next_url': reverse('reserva_cliente', args=[reserva.pk]),
        })
    messages.success(request, mensaje_lindo)
    return redirect('reserva_cliente', pk=pk)


@require_http_methods(['GET', 'POST'])
def reserva_cliente(request, pk):
    reserva = get_object_or_404(Reserva.objects.prefetch_related('lineas'), pk=pk)
    tiene_acceso = (
        request.session.get(f'reserva_{pk}_access')
        or (request.user.is_authenticated and reserva.usuario_id == request.user.pk)
        or usuario_puede_entrar_panel(request.user)
    )
    if not tiene_acceso:
        return redirect('consultar_reserva')

    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        if accion == 'pagar':
            return pagar_reserva_cliente(request, pk)

        if accion == 'cancelar':
            if reserva.estado in ('Cancelada', 'Realizada', 'No asistió'):
                msg = 'Esta reserva ya no se puede cancelar.'
                if 'application/json' in request.headers.get('Accept', ''):
                    return JsonResponse({'ok': False, 'error': msg}, status=400)
                messages.error(request, msg)
            else:
                reserva.estado = 'Cancelada'
                reserva.save(update_fields=['estado'])
                if reserva.pago_confirmado:
                    msg = 'La reserva fue cancelada correctamente. Nuestro equipo se comunicará contigo para gestionar la devolución correspondiente.'
                else:
                    msg = 'La reserva fue cancelada correctamente y los cupos e insumos fueron liberados.'
                if 'application/json' in request.headers.get('Accept', ''):
                    return JsonResponse({'ok': True, 'message': msg, 'estado': 'Cancelada'})
                messages.success(request, msg)
            return redirect('reserva_cliente', pk=pk)
        if accion == 'editar':
            if reserva.estado not in (
                'Pendiente',
                'Pendiente de pago',
                'Confirmada',
            ):
                messages.error(request, 'Esta reserva ya no se puede modificar.')
                return redirect('reserva_cliente', pk=pk)
            try:
                _guardar_reserva(request, reserva=reserva)
            except ValueError as error:
                messages.error(request, str(error))
                return _render_reserva_form(
                    request,
                    'reservas/detalle.html',
                    reserva=reserva,
                    slots_editables=_slots_editables(reserva),
                    whatsapp_url=_url_whatsapp_reserva(reserva),
                )
            messages.success(
                request,
                (
                    'Los cambios se guardaron. Debes volver a pagar el pedido para '
                    'que Prisma lo confirme.'
                    if reserva.tipo_reserva == 'Para llevar'
                    and reserva.estado == 'Pendiente de pago'
                    else 'Los cambios se guardaron. Prisma debe confirmar nuevamente la mesa.'
                    if reserva.tipo_reserva == 'Mesa'
                    and reserva.estado == 'Pendiente'
                    else 'La reserva fue actualizada correctamente.'
                ),
            )
            return redirect('reserva_cliente', pk=pk)
        return _error_reserva(request, 'No se reconoció la acción solicitada.')

    return _render_reserva_form(
        request,
        'reservas/detalle.html',
        reserva=reserva,
        slots_editables=_slots_editables(reserva),
    )


@login_required(login_url='login')
@user_passes_test(_es_administrador, login_url='login')
@require_http_methods(['GET', 'POST'])
def gestion_reservas(request):
    exigir_permiso(request, 'reserva.view_reserva')
    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        if accion == 'crear':
            exigir_permiso(request, 'reserva.add_reserva')
            try:
                reserva = _guardar_reserva(request)
            except ValueError as error:
                messages.error(request, str(error))
                return _render_gestion_reservas(request)
            if _notificar_reserva(reserva, request):
                messages.success(request, f'Reserva #{reserva.pk} registrada y notificada.')
            else:
                messages.warning(
                    request,
                    f'Reserva #{reserva.pk} registrada, pero no se pudo enviar la notificación.',
                )
            return redirect('gestion_reservas')
        if accion == 'confirmar_pago':
            exigir_permiso(request, 'reserva.change_reserva')
            reserva = _reserva_posteada(request)
            if reserva.tipo_reserva != 'Para llevar':
                messages.error(request, 'La reserva de mesa no requiere pago anticipado.')
            elif reserva.estado in ('Cancelada', 'Realizada', 'No asistió'):
                messages.error(request, 'Esta reserva ya no admite pagos.')
            elif reserva.pago_confirmado:
                messages.info(request, 'El pago de este pedido ya estaba confirmado.')
            else:
                reserva.pago_confirmado = True
                reserva.fecha_pago_confirmado = timezone.now()
                reserva.estado = 'Confirmada'
                reserva.notificacion_consultada = False
                reserva.save(update_fields=[
                    'pago_confirmado',
                    'fecha_pago_confirmado',
                    'estado',
                    'notificacion_consultada',
                ])
                if _notificar_reserva(reserva, request, confirmada=True):
                    messages.success(
                        request,
                        f'Pago verificado y pedido #{reserva.pk} confirmado.',
                    )
                else:
                    messages.warning(
                        request,
                        f'Pago verificado y pedido #{reserva.pk} confirmado; no se pudo enviar el correo.',
                    )
            return redirect('gestion_reservas')
        if accion == 'editar':
            exigir_permiso(request, 'reserva.change_reserva')
            reserva_id = request.POST.get('reserva_id', '')
            if not reserva_id.isdecimal() or len(reserva_id) > 18:
                raise Http404
            reserva = get_object_or_404(Reserva, pk=int(reserva_id))
            try:
                _guardar_reserva(request, reserva=reserva)
            except ValueError as error:
                messages.error(request, str(error))
                return _render_gestion_reservas(request, reserva_editar=reserva)
            messages.success(request, f'Reserva #{reserva.pk} actualizada correctamente.')
            return redirect('gestion_reservas')
        if accion == 'estado':
            exigir_permiso(request, 'reserva.change_reserva')
            reserva = _reserva_posteada(request)
            estado = request.POST.get('estado', '')
            if (
                estado == 'Confirmada'
                and reserva.tipo_reserva == 'Para llevar'
                and not reserva.pago_confirmado
            ):
                messages.error(
                    request,
                    'Verifica primero el pago anticipado antes de confirmar este pedido.',
                )
            elif (
                estado == 'Pendiente de pago'
                and reserva.tipo_reserva != 'Para llevar'
            ):
                messages.error(request, 'Las reservas de mesa no requieren pago anticipado.')
            elif (
                estado == 'Pendiente de pago'
                and reserva.pago_confirmado
            ):
                messages.error(
                    request,
                    'El pago ya está verificado. Mantén el pedido confirmado o cancélalo.',
                )
            elif (
                estado == 'Pendiente'
                and reserva.tipo_reserva == 'Para llevar'
            ):
                messages.error(
                    request,
                    'Los pedidos para llevar deben permanecer pendientes de pago hasta su verificación.',
                )
            elif estado in ('Realizada', 'No asistió'):
                messages.error(request, 'Registra el resultado desde la acción de asistencia.')
            elif estado not in dict(Reserva.choices_estado):
                messages.error(request, 'Selecciona un estado válido.')
            else:
                estado_anterior = reserva.estado
                reserva.estado = estado
                if estado in ('Cancelada', 'Pendiente', 'Confirmada'):
                    reserva.asistencia = None
                    reserva.fecha_asistencia = None
                fields = ['estado', 'asistencia', 'fecha_asistencia']
                if estado == 'Confirmada' and estado_anterior != 'Confirmada':
                    reserva.notificacion_consultada = False
                    fields.append('notificacion_consultada')
                reserva.save(update_fields=fields)
                if estado == 'Confirmada' and estado_anterior != 'Confirmada':
                    if _notificar_reserva(reserva, request, confirmada=True):
                        messages.success(
                            request,
                            f'Reserva #{reserva.pk} confirmada y notificada.',
                        )
                    else:
                        messages.warning(
                            request,
                            f'Reserva #{reserva.pk} confirmada, pero no se pudo enviar la notificación.',
                        )
                else:
                    messages.success(request, f'Estado de la reserva #{reserva.pk} actualizado.')
            return redirect('gestion_reservas')
        if accion == 'cancelar':
            exigir_permiso(request, 'reserva.change_reserva')
            reserva = _reserva_posteada(request)
            if reserva.estado in ('Cancelada', 'Realizada'):
                messages.error(request, 'Esta reserva ya no se puede cancelar.')
            else:
                reserva.estado = 'Cancelada'
                reserva.save(update_fields=['estado'])
                if reserva.pago_confirmado:
                    messages.success(
                        request,
                        f'Reserva #{reserva.pk} cancelada. Recuerda gestionar la devolución correspondiente para {reserva.nombre_cliente}.',
                    )
                else:
                    messages.success(request, f'Reserva #{reserva.pk} cancelada correctamente e insumos liberados.')
            return redirect('gestion_reservas')
        if accion == 'asistencia':
            exigir_permiso(request, 'reserva.change_reserva')
            reserva = _reserva_posteada(request)
            asistencia = request.POST.get('asistencia', '')
            if asistencia not in dict(Reserva.choice_asistencia):
                messages.error(request, 'Selecciona un resultado de asistencia válido.')
            elif reserva.estado in ('Cancelada', 'Pendiente', 'Pendiente de pago'):
                messages.error(request, 'Confirma la reserva antes de registrar asistencia.')
            else:
                reserva.asistencia = asistencia
                reserva.estado = 'Realizada' if asistencia == 'Asistió' else 'No asistió'
                reserva.fecha_asistencia = timezone.now()
                reserva.save(update_fields=['asistencia', 'estado', 'fecha_asistencia'])
                messages.success(request, f'Asistencia de la reserva #{reserva.pk} registrada: {asistencia}.')
            return redirect('gestion_reservas')
        messages.error(request, 'No se reconoció la acción solicitada.')

    edit_id = request.GET.get('editar', '')
    reserva_editar = None
    if edit_id:
        if not edit_id.isdecimal() or len(edit_id) > 18:
            raise Http404
        exigir_permiso(request, 'reserva.change_reserva')
        reserva_editar = get_object_or_404(Reserva, pk=int(edit_id))
    return _render_gestion_reservas(request, reserva_editar=reserva_editar)


def _reserva_posteada(request):
    reserva_id = request.POST.get('reserva_id', '')
    if not reserva_id.isdecimal() or len(reserva_id) > 18:
        raise Http404
    return get_object_or_404(Reserva, pk=int(reserva_id))


@login_required(login_url='login')
@user_passes_test(_es_administrador, login_url='login')
@require_http_methods(['GET'])
def consultar_notificacion_reserva(request, pk):
    exigir_permiso(request, 'reserva.view_reserva')
    reserva = get_object_or_404(Reserva, pk=pk)
    reserva.notificacion_consultada = True
    reserva.save(update_fields=['notificacion_consultada'])
    return redirect(
        f'{reverse("gestion_reservas")}?q={quote(reserva.telefono)}'
    )


def _render_gestion_reservas(request, reserva_editar=None):
    todas_las_reservas = Reserva.objects.all()
    reservas = todas_las_reservas.prefetch_related('lineas').order_by(
        '-fecha_reserva', '-hora', '-pk'
    )
    query = request.GET.get('q', '').strip()[:100]
    fecha = request.GET.get('fecha', '').strip()
    estado = request.GET.get('estado', '').strip()
    modalidad = request.GET.get('modalidad', '').strip()
    solo_nuevas = request.GET.get('notif') == 'nuevas'
    if solo_nuevas:
        reservas = reservas.filter(notificacion_consultada=False)
    if query:
        reservas = reservas.filter(
            Q(nombre_cliente__icontains=query)
            | Q(telefono__icontains=query)
            | Q(detalles__icontains=query)
        ).distinct()
    if fecha:
        try:
            date.fromisoformat(fecha)
        except ValueError:
            fecha = ''
        if fecha:
            reservas = reservas.filter(fecha_reserva=fecha)
    if estado in dict(Reserva.choices_estado):
        reservas = reservas.filter(estado=estado)
    else:
        estado = ''
    if modalidad in dict(Reserva.choices_tipo_reserva):
        reservas = reservas.filter(tipo_reserva=modalidad)
    else:
        modalidad = ''
    total_recaudado = sum(
        (
            reserva.total
            for reserva in todas_las_reservas.filter(
                pago_confirmado=True,
            ).prefetch_related('lineas')
        ),
        start=Decimal('0.00'),
    )
    return _render_reserva_form(
        request,
        'reservas/gestion.html',
        reservas=reservas,
        total_pendientes=todas_las_reservas.filter(estado='Pendiente').count(),
        total_pendientes_pago=todas_las_reservas.filter(estado='Pendiente de pago').count(),
        total_confirmadas=todas_las_reservas.filter(estado='Confirmada').count(),
        total_alertas_nuevas=Reserva.objects.filter(notificacion_consultada=False).count(),
        alertas_recientes=Reserva.objects.filter(
            notificacion_consultada=False,
        ).order_by('-pk')[:5],
        canales_reserva=Reserva.choices_canal,
        total_recaudado=total_recaudado,
        reserva_editar=reserva_editar,
        slots_editables=_slots_editables(reserva_editar),
        query=query,
        fecha_filtro=fecha,
        estado_filtro=estado,
        modalidad_filtro=modalidad,
        solo_nuevas=solo_nuevas,
        puede_crear=usuario_puede_acceder(request.user, 'reserva.add_reserva'),
        puede_editar=usuario_puede_acceder(request.user, 'reserva.change_reserva'),
    )
