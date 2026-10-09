import logging
import re
import smtplib
from datetime import date
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Reserva


logger = logging.getLogger(__name__)

POSTRES = {
    'Manzana Verde Cheesecake': 25000,
    'Café Chocolate': 28000,
    'Fresa Chocolate': 32000,
    'Postre Personalizado': 0,
}


@require_http_methods(['GET', 'POST'])
def reservas_view(request):
    if request.method == 'GET':
        return render(request, 'reservas/reservas.html')

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

    reserva = Reserva.objects.create(
        nombre_cliente=nombre,
        telefono=telefono,
        fecha_reserva=fecha_reserva,
        hora=None,
        postre=postre,
        cantidad=cantidad,
        detalles=detalles,
    )

    precio_unitario = POSTRES[postre]
    total = precio_unitario * cantidad
    precio_texto = f'${total:,}'.replace(',', '.') if precio_unitario else 'A cotizar'
    fecha_formateada = fecha_reserva.strftime('%d/%m/%Y')
    mensaje_whatsapp = '\n'.join([
        'RESERVA · PRISMA',
        f'Reserva #{reserva.pk}',
        f'Cliente: {nombre}',
        f'Teléfono: {telefono}',
        f'Fecha de entrega: {fecha_formateada}',
        f'Postre: {postre}',
        f'Cantidad: {cantidad}',
        f'Precio estimado: {precio_texto}',
        f'Indicaciones: {detalles or "Sin indicaciones especiales."}',
        'Quedo atento(a) a la confirmación. ¡Gracias!',
    ])
    whatsapp_url = (
        f'https://wa.me/{settings.RESERVAS_WHATSAPP_DESTINO}'
        f'?text={quote(mensaje_whatsapp)}'
    )

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

    if email_sent:
        mensaje = 'Tu reserva quedó registrada y se notificó por correo. Confirma el envío desde WhatsApp.'
    else:
        mensaje = 'Tu reserva quedó registrada, pero no se pudo enviar el correo. Confirma los datos desde WhatsApp.'

    return JsonResponse({
        'ok': True,
        'email_sent': email_sent,
        'message': mensaje,
        'whatsapp_url': whatsapp_url,
    }, status=201)
