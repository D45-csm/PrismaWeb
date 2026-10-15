from datetime import date, timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Reserva


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
        self.assertEqual(reserva.postre, 'Café Chocolate')
        self.assertEqual(reserva.cantidad, 2)
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
