from datetime import date, timedelta
from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from APP.productos.models import CategoriaProducto, Producto
from APP.ventas.models import Comprobante

from .models import DetalleReserva, Reserva


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='sender@example.com',
    EMAIL_HOST_PASSWORD='test-password',
    DEFAULT_FROM_EMAIL='sender@example.com',
    RESERVAS_EMAIL_DESTINO='reservas@example.com',
)
class ReservaSubmissionTests(TestCase):
    def valid_data(self):
        return {
            'nombre': 'Cliente Prisma',
            'telefono': '311 868 9862',
            'fecha': (date.today() + timedelta(days=3)).isoformat(),
            'postre': 'Café Chocolate',
            'cantidad': '2',
            'detalles': 'Para cumpleaños',
        }

    def test_reserva_is_saved_emailed_and_returns_whatsapp_link(self):
        response = self.client.post(reverse('reservas'), self.valid_data())

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['email_sent'])
        self.assertIn('wa.me/573118689862', response.json()['whatsapp_url'])
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.nombre_cliente, 'Cliente Prisma')
        detalle = reserva.lineas.get()
        self.assertEqual(detalle.nombre_producto, 'Café Chocolate')
        self.assertEqual(detalle.cantidad, 2)
        self.assertEqual(detalle.precio_unitario, Decimal('28000'))
        self.assertEqual(reserva.hora, None)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['reservas@example.com'])

    def test_invalid_reserva_does_not_save_or_send_email(self):
        data = self.valid_data()
        data['cantidad'] = '51'

        response = self.client.post(reverse('reservas'), data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='')
    def test_missing_email_credentials_are_reported_without_losing_reserva(self):
        response = self.client.post(reverse('reservas'), self.valid_data())

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['email_sent'])
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertIn('no se pudo enviar el correo', response.json()['message'])


class ReservaRelationsTests(TestCase):
    def test_reservation_can_have_multiple_product_lines_and_receipts(self):
        categoria = CategoriaProducto.objects.create(nombre='Postres')
        producto_a = Producto.objects.create(
            categoria=categoria,
            nombre='Cheesecake',
            descripcion='Cheesecake artesanal',
            precio=Decimal('25000.00'),
        )
        producto_b = Producto.objects.create(
            categoria=categoria,
            nombre='Brownie',
            descripcion='Brownie de chocolate',
            precio=Decimal('18000.00'),
        )
        reserva = Reserva.objects.create(
            nombre_cliente='Cliente Prisma',
            fecha_reserva=date.today(),
        )
        detalle_a = DetalleReserva.objects.create(
            reserva=reserva,
            producto=producto_a,
            cantidad=2,
            precio_unitario=Decimal('25000.00'),
        )
        DetalleReserva.objects.create(
            reserva=reserva,
            producto=producto_b,
            cantidad=1,
            precio_unitario=Decimal('18000.00'),
        )
        comprobante = Comprobante.objects.create(
            direccion_comprobante='comprobantes/reserva.pdf',
            reserva=reserva,
        )

        self.assertEqual(reserva.lineas.count(), 2)
        self.assertEqual(reserva.comprobantes.get(), comprobante)
        self.assertEqual(detalle_a.subtotal, Decimal('50000.00'))
