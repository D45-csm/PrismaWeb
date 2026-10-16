import logging
import smtplib
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .forms import POSTRES, ReservaForm


logger = logging.getLogger(__name__)

@require_http_methods(['GET', 'POST'])
def reservas_view(request):
    if request.method == 'GET':
        return render(
            request,
            'reservas/reservas.html',
            {'reserva_form': ReservaForm()},
        )

    post_data = request.POST.copy()
    for legacy_name, form_name in (
        ('nombre', 'nombre_cliente'),
        ('fecha', 'fecha_reserva'),
    ):
        if form_name not in post_data and legacy_name in post_data:
            post_data[form_name] = post_data[legacy_name]

    form = ReservaForm(post_data)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return JsonResponse({'ok': False, 'error': first_error}, status=400)

    reserva = form.save()
    nombre = reserva.nombre_cliente
    telefono = reserva.telefono
    fecha_reserva = reserva.fecha_reserva
    postre = reserva.postre
    cantidad = reserva.cantidad
    detalles = reserva.detalles

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
