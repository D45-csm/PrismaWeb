from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import unquote

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from APP.productos.models import CategoriaProducto, Producto
from APP.usuarios.models import Usuario
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
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='cliente_takeaway',
            email='cliente@example.com',
            password='password123',
        )

    def valid_data(self):
        return {
            'nombre': 'Cliente Prisma',
            'telefono': '311 868 9862',
            'fecha': (date.today() + timedelta(days=3)).isoformat(),
            'postre': 'Café Chocolate',
            'cantidad': '2',
            'detalles': 'Para cumpleaños',
        }

    def test_unauthenticated_takeaway_requires_login(self):
        response = self.client.post(
            reverse('reservas'),
            self.valid_data(),
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.json()['require_login'])
        self.assertIn('iniciar sesión', response.json()['error'])

    def test_reserva_is_saved_without_email_until_receipt_is_sent(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('reservas'),
            self.valid_data(),
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['email_sent'])
        self.assertTrue(response.json()['email_pending'])
        self.assertIn('wa.me/573118689862', response.json()['whatsapp_url'])
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.nombre_cliente, 'Cliente Prisma')
        detalle = reserva.lineas.get()
        self.assertEqual(detalle.nombre_producto, 'Café Chocolate')
        self.assertEqual(detalle.cantidad, 2)
        self.assertEqual(detalle.precio_unitario, Decimal('15000'))
        self.assertEqual(reserva.hora, None)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_reserva_does_not_save_or_send_email(self):
        self.client.force_login(self.user)
        data = self.valid_data()
        data['cantidad'] = '51'

        response = self.client.post(
            reverse('reservas'),
            data,
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='')
    def test_missing_email_credentials_do_not_send_before_receipt(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('reservas'),
            self.valid_data(),
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['email_sent'])
        self.assertTrue(response.json()['email_pending'])
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)


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


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='sender@example.com',
    EMAIL_HOST_PASSWORD='test-password',
    DEFAULT_FROM_EMAIL='sender@example.com',
    RESERVAS_EMAIL_DESTINO='reservas@example.com',
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class ReservaWorkflowTests(TestCase):
    def setUp(self):
        categoria = CategoriaProducto.objects.create(nombre='Postres')
        self.producto = Producto.objects.create(
            categoria=categoria,
            nombre='Cheesecake',
            descripcion='Cheesecake artesanal',
            precio=Decimal('25000.00'),
        )
        self.user = Usuario.objects.create_user(
            username='cliente_workflow',
            email='workflow@example.com',
            password='password123',
            telefono='3118689862',
        )

    def datos_reserva(self):
        return {
            'nombre': 'Cliente Prisma',
            'telefono': '311 868 9862',
            'fecha': (date.today() + timedelta(days=2)).isoformat(),
            'hora': '14:30',
            'tipo_reserva': 'Mesa',
            'numero_personas': '4',
            'producto_id_1': str(self.producto.pk),
            'cantidad_1': '2',
            'detalles': 'Celebración familiar',
        }

    def archivo_comprobante(self, name='pago.png', contenido=b'\x89PNG\r\n\x1a\ncontenido'):
        content_type = (
            'application/pdf' if name.lower().endswith('.pdf')
            else 'image/jpeg' if name.lower().endswith(('.jpg', '.jpeg'))
            else 'image/png'
        )
        return SimpleUploadedFile(name, contenido, content_type=content_type)

    def crear_reserva_con_comprobante(self, tipo_reserva='Mesa'):
        self.client.force_login(self.user)
        data = self.datos_reserva()
        data.update(
            tipo_reserva=tipo_reserva,
            numero_personas='4' if tipo_reserva == 'Mesa' else '',
        )
        response = self.client.post(
            reverse('reservas'),
            data,
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 201)
        reserva = Reserva.objects.get()
        pago_response = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {
                'metodo_pago': 'Nequi',
                'referencia': 'ref-pendiente-123',
                'comprobante_archivo': self.archivo_comprobante(),
            },
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(pago_response.status_code, 200)
        return reserva, reserva.comprobantes.get()

    def test_public_reservation_and_lookup_pages_render(self):
        response = self.client.get(reverse('reservas'))
        lookup_response = self.client.get(reverse('consultar_reserva'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Planea tu visita')
        self.assertContains(response, 'name="hora"')
        self.assertContains(response, 'Elige tu postre')
        self.assertContains(response, f'href="{reverse("productos")}#productosGrid"')
        self.assertContains(response, '3026493531')
        self.assertContains(response, '3143983857')
        self.assertContains(response, 'data-copy-payment', count=3)
        self.assertContains(response, 'name="comprobante_archivo"')
        self.assertContains(response, 'accept=".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf"')
        self.assertNotContains(response, 'Tarjeta')
        self.assertNotContains(response, 'Bancolombia')
        self.assertEqual(lookup_response.status_code, 200)
        self.assertContains(lookup_response, 'Consulta tu reserva')

    def test_my_reservations_requires_customer_login(self):
        response = self.client.get(reverse('mis_reservas'))

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("mis_reservas")}',
        )

    def test_customer_sees_only_own_reservations_in_backup_list(self):
        own_reservation = Reserva.objects.create(
            usuario=self.user,
            nombre_cliente='Mi reserva',
            telefono='311 868 9862',
            fecha_reserva=date.today() + timedelta(days=2),
            hora='14:30',
            tipo_reserva='Mesa',
            numero_personas=2,
        )
        DetalleReserva.objects.create(
            reserva=own_reservation,
            producto=self.producto,
            nombre_producto=self.producto.nombre,
            cantidad=1,
            precio_unitario=self.producto.precio,
        )
        Reserva.objects.create(
            nombre_cliente='Reserva de otra persona',
            telefono='3001234567',
            fecha_reserva=date.today() + timedelta(days=2),
            hora='15:00',
            tipo_reserva='Mesa',
            numero_personas=4,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('mis_reservas'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['reservas']), [own_reservation])
        self.assertContains(response, f'Reserva #{own_reservation.pk}')
        self.assertContains(response, 'Ver más detalles')
        self.assertContains(
            response,
            reverse('reserva_cliente', args=[own_reservation.pk]),
        )
        self.assertNotContains(response, 'Reserva de otra persona')
        detalle = self.client.get(reverse('reserva_cliente', args=[own_reservation.pk]))
        self.assertContains(detalle, own_reservation.nombre_cliente)
        self.assertContains(detalle, own_reservation.telefono)
        self.assertContains(detalle, self.user.email)
        self.assertContains(detalle, self.producto.nombre)

    def test_authenticated_customer_reserves_a_table_and_must_pay(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('reservas'),
            self.datos_reserva(),
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 201)
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.numero_personas, 4)
        self.assertEqual(reserva.tipo_reserva, 'Mesa')
        self.assertEqual(reserva.estado, 'Pendiente de pago')
        self.assertFalse(reserva.pago_confirmado)
        self.assertTrue(response.json()['require_payment'])
        self.assertEqual(
            response.json()['payment_url'],
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
        )
        self.assertEqual(reserva.lineas.get().cantidad, 2)
        self.assertIn(f'/reserva/consultar/{reserva.pk}/', response.json()['next_url'])
        self.assertIn('SOLICITUD DE RESERVA DE MESA', unquote(response.json()['whatsapp_url']))
        self.assertEqual(response.json()['reservation_id'], reserva.pk)
        self.assertEqual(len(mail.outbox), 0)
        detail_response = self.client.get(response.json()['next_url'])
        self.assertContains(detail_response, 'Pago anticipado pendiente')
        self.assertContains(detail_response, 'inlinePayForm')
        self.assertContains(detail_response, 'data-copy-payment', count=3)

        payment_response = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {
                'metodo_pago': 'Daviplata',
                'referencia': 'mesa-ref-456',
                'comprobante_archivo': self.archivo_comprobante(
                    'pago.pdf',
                    b'%PDF-1.7\ncontenido',
                ),
            },
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(payment_response.status_code, 200)
        self.assertFalse(payment_response.json()['pago_confirmado'])
        self.assertTrue(payment_response.json()['email_sent'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f'reserva #{reserva.pk}', mail.outbox[0].body.lower())
        self.assertEqual(reserva.comprobantes.get().referencia, 'mesa-ref-456')
        comprobante = reserva.comprobantes.get()
        self.assertTrue(comprobante.direccion_comprobante.name.endswith('.pdf'))
        self.assertContains(
            self.client.get(response.json()['next_url']),
            reverse('ver_comprobante_cliente', args=[comprobante.pk]),
        )
        archivo_response = self.client.get(
            reverse('ver_comprobante_cliente', args=[comprobante.pk]),
        )
        self.assertEqual(archivo_response.status_code, 200)
        self.assertEqual(archivo_response['Content-Type'], 'application/pdf')

    def test_anonymous_cannot_reserve_a_table_or_takeaway(self):
        for modalidad in ('Mesa', 'Para llevar'):
            with self.subTest(modalidad=modalidad):
                data = self.datos_reserva()
                data.update(
                    tipo_reserva=modalidad,
                    numero_personas='4' if modalidad == 'Mesa' else '',
                )
                response = self.client.post(
                    reverse('reservas'),
                    data,
                    HTTP_ACCEPT='application/json',
                )
                self.assertEqual(response.status_code, 401)
                self.assertTrue(response.json()['require_login'])
        self.assertEqual(Reserva.objects.count(), 0)

    def test_takeaway_reservation_requires_advance_payment_and_builds_whatsapp_summary(self):
        self.client.force_login(self.user)
        data = self.datos_reserva()
        data.update(tipo_reserva='Para llevar', numero_personas='')

        response = self.client.post(
            reverse('reservas'),
            data,
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 201)
        reserva = Reserva.objects.get()
        self.assertEqual(
            response.json()['payment_url'],
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
        )
        self.assertEqual(reserva.estado, 'Pendiente de pago')
        self.assertFalse(reserva.pago_confirmado)
        self.assertEqual(reserva.total, Decimal('50000.00'))
        self.assertIn('completa tu pago', response.json()['message'].lower())
        self.assertIn('Total del pedido: $50.000 COP', unquote(response.json()['whatsapp_url']))
        detail_response = self.client.get(response.json()['next_url'])
        self.assertContains(detail_response, 'Pago anticipado pendiente')
        self.assertContains(detail_response, '3026493531')
        self.assertContains(detail_response, 'name="comprobante_archivo"')
        self.assertContains(detail_response, 'accept=".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf"')
        self.assertContains(detail_response, '3143983857')
        self.assertContains(detail_response, 'data-payment-account="Nequi"')
        self.assertContains(detail_response, 'data-payment-account="Llave"')
        self.assertContains(detail_response, 'data-payment-account="Daviplata"')
        self.assertContains(detail_response, 'data-copy-payment', count=3)
        self.assertNotContains(detail_response, 'Tarjeta')
        self.assertNotContains(detail_response, 'Bancolombia')
        self.assertContains(detail_response, 'Coordinar pago por WhatsApp')
        self.assertContains(detail_response, 'Cancelar reserva')

    def test_customer_can_submit_payment_using_llave(self):
        self.client.force_login(self.user)
        data = self.datos_reserva()
        data.update(tipo_reserva='Para llevar', numero_personas='')
        self.client.post(reverse('reservas'), data, HTTP_ACCEPT='application/json')
        reserva = Reserva.objects.get()

        invalid_method = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {'metodo_pago': 'Tarjeta', 'referencia': 'ref-123'},
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(invalid_method.status_code, 400)
        self.assertEqual(reserva.comprobantes.count(), 0)

        missing_file = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {'metodo_pago': 'Llave', 'referencia': 'llave-123'},
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(missing_file.status_code, 400)
        self.assertIn('Adjunta el comprobante', missing_file.json()['error'])

        invalid_file = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {
                'metodo_pago': 'Llave',
                'referencia': 'llave-123',
                'comprobante_archivo': self.archivo_comprobante(
                    'pago.png',
                    b'no es una imagen PNG',
                ),
            },
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(invalid_file.status_code, 400)
        self.assertIn('no coincide', invalid_file.json()['error'])

        response = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {
                'metodo_pago': 'Llave',
                'referencia': 'llave-123',
                'comprobante_archivo': self.archivo_comprobante(),
            },
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['metodo_pago'], 'Llave')
        comprobante = reserva.comprobantes.get()
        self.assertEqual(comprobante.referencia, 'llave-123')
        self.assertEqual(response.json()['title'], '¡Comprobante enviado con éxito!')

        archivo_response = self.client.get(
            reverse('ver_comprobante_cliente', args=[comprobante.pk]),
        )
        self.assertEqual(archivo_response.status_code, 200)
        self.assertEqual(archivo_response['Content-Type'], 'image/png')
        self.assertIn('attachment', archivo_response['Content-Disposition'])

        otro_usuario = Usuario.objects.create_user(
            username='otro-cliente',
            email='otro@example.com',
            password='password123',
        )
        self.client.force_login(otro_usuario)
        acceso_denegado = self.client.get(
            reverse('ver_comprobante_cliente', args=[comprobante.pk]),
        )
        self.assertRedirects(acceso_denegado, reverse('consultar_reserva'))

    def test_customer_upload_succeeds_with_filesystem_storage(self):
        self.client.force_login(self.user)
        reservation_response = self.client.post(
            reverse('reservas'),
            self.datos_reserva(),
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(reservation_response.status_code, 201)
        reserva = Reserva.objects.get()

        with TemporaryDirectory() as media_root:
            with override_settings(
                MEDIA_ROOT=media_root,
                STORAGES={
                    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
                },
            ):
                response = self.client.post(
                    reverse('pagar_reserva_cliente', args=[reserva.pk]),
                    {
                        'metodo_pago': 'Nequi',
                        'referencia': 'fs-upload-123',
                        'comprobante_archivo': self.archivo_comprobante(),
                    },
                    HTTP_ACCEPT='application/json',
                )
                self.assertEqual(response.status_code, 200, response.content.decode())
                comprobante = reserva.comprobantes.get()
                self.assertTrue(os.path.isfile(
                    os.path.join(media_root, comprobante.direccion_comprobante.name),
                ))

    def test_customer_can_cancel_pending_payment_and_reopen_the_saved_reservation(self):
        self.client.force_login(self.user)
        data = self.datos_reserva()
        data.update(tipo_reserva='Para llevar', numero_personas='')
        submission = self.client.post(
            reverse('reservas'),
            data,
            HTTP_ACCEPT='application/json',
        )
        reserva = Reserva.objects.get()
        detail_url = reverse('reserva_cliente', args=[reserva.pk])

        self.assertEqual(submission.status_code, 201)
        self.assertEqual(submission.json()['reservation_id'], reserva.pk)
        self.assertContains(self.client.get(detail_url), 'Cancelar reserva')

        cancellation = self.client.post(detail_url, {'accion': 'cancelar'})
        self.assertRedirects(cancellation, detail_url)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'Cancelada')
        self.assertFalse(reserva.pago_confirmado)
        self.assertEqual(reserva.lineas.count(), 1)
        self.assertEqual(Reserva.objects.count(), 1)

        cancelled_detail = self.client.get(detail_url)
        self.assertContains(cancelled_detail, 'Reserva cancelada')
        self.assertContains(cancelled_detail, 'no necesitas completar el pago')
        self.assertNotContains(cancelled_detail, 'Cancelar reserva')
        self.assertNotContains(cancelled_detail, 'Coordinar pago por WhatsApp')
        self.assertNotContains(cancelled_detail, 'Completa tu pago')

        self.client.session.flush()
        lookup = self.client.post(reverse('consultar_reserva'), {
            'reserva_id': str(reserva.pk),
            'telefono': data['telefono'],
        })
        self.assertRedirects(lookup, detail_url)
        reopened_detail = self.client.get(detail_url)
        self.assertContains(reopened_detail, 'Reserva cancelada')
        self.assertEqual(Reserva.objects.count(), 1)

    def test_customer_submits_payment_reference_for_staff_validation(self):
        from django.contrib.auth.models import Permission

        self.client.force_login(self.user)
        encargado = Usuario.objects.create_user(
            username='encargado_pago',
            email='encargado@example.com',
            password='password123',
        )
        encargado.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='reserva',
                codename='view_reserva',
            ),
        )
        self.assertTrue(encargado.has_perm('reserva.view_reserva'))
        data = self.datos_reserva()
        data.update(tipo_reserva='Para llevar', numero_personas='')
        submission = self.client.post(
            reverse('reservas'),
            data,
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(submission.status_code, 201)
        reserva = Reserva.objects.get()
        self.assertFalse(reserva.pago_confirmado)
        comprobante_legacy = Comprobante.objects.create(
            reserva=reserva,
            referencia='referencia-anterior',
        )

        # Complete payment
        payment_response = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {
                'metodo_pago': 'Nequi',
                'referencia': '123456',
                'comprobante_archivo': self.archivo_comprobante('pago.jpg', b'\xff\xd8\xffcontenido'),
            },
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(payment_response.status_code, 200)
        self.assertTrue(payment_response.json()['ok'])
        self.assertFalse(payment_response.json()['pago_confirmado'])
        self.assertIn('pendiente de validación', payment_response.json()['message'])
        self.assertIn('Nequi', payment_response.json()['metodo_pago'])
        self.assertTrue(payment_response.json()['email_sent'])
        self.assertEqual(len(mail.outbox), 1)

        reserva.refresh_from_db()
        self.assertFalse(reserva.pago_confirmado)
        self.assertEqual(reserva.estado, 'Pendiente de pago')
        self.assertEqual(reserva.metodo_pago, 'Nequi')
        self.assertIsNone(reserva.fecha_pago_confirmado)
        comprobante = reserva.comprobantes.get()
        self.assertEqual(comprobante.pk, comprobante_legacy.pk)
        self.assertEqual(comprobante.estado, 'Pendiente de confirmación')
        self.assertEqual(comprobante.referencia, '123456')
        self.assertTrue(comprobante.direccion_comprobante.name.endswith('.jpg'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            set(mail.outbox[0].to),
            {'reservas@example.com', 'encargado@example.com'},
        )
        self.assertIn(f'/reserva/consultar/{reserva.pk}/', mail.outbox[0].body)
        self.assertIn(
            reverse('ver_comprobante_cliente', args=[comprobante.pk]),
            mail.outbox[0].body,
        )

        detalle = self.client.get(reverse('reserva_cliente', args=[reserva.pk]))
        self.assertContains(detalle, '¡Comprobante enviado correctamente!')
        self.assertContains(detalle, 'pendiente de validación')
        self.assertNotContains(detalle, 'inlinePayForm')

        duplicate_response = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {'metodo_pago': 'Nequi', 'referencia': '123456'},
            HTTP_ACCEPT='application/json',
        )
        self.assertTrue(duplicate_response.json()['ok'])
        self.assertEqual(reserva.comprobantes.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_past_reservation_is_rejected(self):
        self.client.force_login(self.user)
        datos = self.datos_reserva()
        datos['fecha'] = (date.today() - timedelta(days=1)).isoformat()

        response = self.client.post(
            reverse('reservas'),
            datos,
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_two_pm_today_is_not_mistaken_for_past_in_bogota(self):
        self.client.force_login(self.user)
        datos = self.datos_reserva()
        datos.update(fecha='2026-11-19', hora='14:00')
        ahora_utc = datetime(2026, 11, 19, 15, 12, tzinfo=timezone.utc)

        with patch('django.utils.timezone.now', return_value=ahora_utc):
            response = self.client.post(
                reverse('reservas'),
                datos,
                HTTP_ACCEPT='application/json',
            )

        self.assertEqual(response.status_code, 201, response.content.decode())
        self.assertEqual(Reserva.objects.get().hora.isoformat(), '14:00:00')

    def test_reservation_rejects_times_outside_business_hours(self):
        self.client.force_login(self.user)
        for hora in ('13:59', '18:31'):
            with self.subTest(hora=hora):
                response = self.client.post(
                    reverse('reservas'),
                    {**self.datos_reserva(), 'hora': hora},
                    HTTP_ACCEPT='application/json',
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn('2:00 PM a 6:30 PM', response.json()['error'])
        self.assertEqual(Reserva.objects.count(), 0)

    def test_customer_can_update_and_cancel_with_reservation_id_and_phone(self):
        reserva = Reserva.objects.create(
            nombre_cliente='Cliente Prisma',
            telefono='311 868 9862',
            fecha_reserva=date.today() + timedelta(days=2),
            hora='14:30',
            numero_personas=4,
            tipo_reserva='Mesa',
        )
        DetalleReserva.objects.create(
            reserva=reserva,
            producto=self.producto,
            nombre_producto=self.producto.nombre,
            cantidad=1,
            precio_unitario=self.producto.precio,
        )

        lookup = self.client.post(reverse('consultar_reserva'), {
            'reserva_id': str(reserva.pk),
            'telefono': '3118689862',
        })
        self.assertRedirects(
            lookup,
            reverse('reserva_cliente', args=[reserva.pk]),
        )
        detail_response = self.client.get(
            reverse('reserva_cliente', args=[reserva.pk]),
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Tu reserva, en un solo lugar')
        datos = self.datos_reserva()
        datos['accion'] = 'editar'
        datos['cantidad_1'] = '3'
        updated = self.client.post(
            reverse('reserva_cliente', args=[reserva.pk]),
            datos,
        )
        self.assertRedirects(
            updated,
            reverse('reserva_cliente', args=[reserva.pk]),
        )
        reserva.refresh_from_db()
        self.assertEqual(reserva.lineas.get().cantidad, 3)

        cancelled = self.client.post(
            reverse('reserva_cliente', args=[reserva.pk]),
            {'accion': 'cancelar'},
        )
        self.assertRedirects(
            cancelled,
            reverse('reserva_cliente', args=[reserva.pk]),
        )
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'Cancelada')

    def test_admin_can_create_reservation_and_register_attendance(self):
        from APP.usuarios.models import Usuario

        admin = Usuario.objects.create_superuser(
            username='reservas-admin',
            email='admin@example.com',
            password='test-password',
            telefono='3118689862',
        )
        self.client.force_login(admin)
        dashboard_response = self.client.get(reverse('gestion_reservas'))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'Reservas y pedidos')
        self.assertContains(dashboard_response, 'data-admin-nav-toggle')

        create_response = self.client.post(
            reverse('gestion_reservas'),
            {'accion': 'crear', **self.datos_reserva()},
        )
        self.assertRedirects(create_response, reverse('gestion_reservas'))
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.estado, 'Pendiente de pago')
        confirm_response = self.client.post(
            reverse('gestion_reservas'),
            {
                'accion': 'estado',
                'reserva_id': str(reserva.pk),
                'estado': 'Confirmada',
            },
        )
        self.assertRedirects(confirm_response, reverse('gestion_reservas'))
        reserva.refresh_from_db()
        self.assertFalse(reserva.pago_confirmado)
        self.assertEqual(reserva.estado, 'Pendiente de pago')

        comprobante = Comprobante.objects.create(
            reserva=reserva,
            referencia='mesa-ref-123',
            direccion_comprobante=self.archivo_comprobante(),
        )
        self.client.post(
            reverse('gestion_reservas'),
            {'accion': 'confirmar_pago', 'reserva_id': str(reserva.pk)},
        )
        reserva.refresh_from_db()
        comprobante.refresh_from_db()
        self.assertTrue(reserva.pago_confirmado)
        self.assertEqual(reserva.estado, 'Confirmada')
        self.assertEqual(comprobante.estado, 'Confirmado')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('confirmada', mail.outbox[0].subject)

        attendance_response = self.client.post(
            reverse('gestion_reservas'),
            {
                'accion': 'asistencia',
                'reserva_id': str(reserva.pk),
                'asistencia': 'Asistió',
            },
        )

        self.assertRedirects(attendance_response, reverse('gestion_reservas'))
        reserva.refresh_from_db()
        self.assertEqual(reserva.asistencia, 'Asistió')
        self.assertEqual(reserva.estado, 'Realizada')
        self.assertIsNotNone(reserva.fecha_asistencia)
        self.assertFalse(reserva.notificacion_consultada)
        self.assertIn(
            reverse('consultar_notificacion_reserva', args=[reserva.pk]),
            mail.outbox[0].body,
        )

        notification_response = self.client.get(
            reverse('consultar_notificacion_reserva', args=[reserva.pk]),
        )
        self.assertRedirects(
            notification_response,
            f'{reverse("gestion_reservas")}?q=311%20868%209862',
        )
        reserva.refresh_from_db()
        self.assertTrue(reserva.notificacion_consultada)

    def test_admin_reservation_metrics_remain_global_when_list_is_filtered(self):
        admin = Usuario.objects.create_superuser(
            username='metrics-admin',
            email='metrics-admin@example.com',
            password='test-password',
        )
        pendiente = Reserva.objects.create(
            nombre_cliente='Pendiente',
            telefono='3118689862',
            fecha_reserva=date.today() + timedelta(days=2),
            hora='14:30',
            tipo_reserva='Mesa',
            estado='Pendiente',
        )
        pagada = Reserva.objects.create(
            nombre_cliente='Confirmada',
            telefono='3118689862',
            fecha_reserva=date.today() + timedelta(days=2),
            hora='15:00',
            tipo_reserva='Para llevar',
            estado='Confirmada',
            pago_confirmado=True,
        )
        DetalleReserva.objects.create(
            reserva=pagada,
            producto=self.producto,
            nombre_producto=self.producto.nombre,
            cantidad=1,
            precio_unitario=self.producto.precio,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('gestion_reservas'), {'estado': 'Pendiente'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['reservas']), [pendiente])
        self.assertEqual(response.context['total_pendientes'], 1)
        self.assertEqual(response.context['total_confirmadas'], 1)
        self.assertEqual(response.context['total_recaudado'], self.producto.precio)

    def test_admin_can_filter_unreviewed_reservation_notifications(self):
        admin = Usuario.objects.create_superuser(
            username='notifications-admin',
            email='notifications-admin@example.com',
            password='test-password',
        )
        new_reservation = Reserva.objects.create(
            nombre_cliente='Reserva por revisar',
            telefono='3118689862',
            fecha_reserva=date.today() + timedelta(days=2),
            notificacion_consultada=False,
        )
        Reserva.objects.create(
            nombre_cliente='Reserva ya revisada',
            telefono='3001234567',
            fecha_reserva=date.today() + timedelta(days=2),
            notificacion_consultada=True,
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse('gestion_reservas'),
            {'notif': 'nuevas'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['solo_nuevas'])
        self.assertEqual(list(response.context['reservas']), [new_reservation])
        self.assertContains(response, 'Reservas nuevas sin revisar')
        self.assertContains(response, 'Reserva por revisar')
        self.assertNotContains(response, 'Reserva ya revisada')

    def test_admin_cannot_register_reservation_outside_business_hours(self):
        admin = Usuario.objects.create_superuser(
            username='hours-admin',
            email='hours-admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin)

        for hora in ('13:59', '18:31'):
            with self.subTest(hora=hora):
                response = self.client.post(
                    reverse('gestion_reservas'),
                    {
                        'accion': 'crear',
                        **self.datos_reserva(),
                        'hora': hora,
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'El horario de reservas es de 2:00 PM a 6:30 PM.')
        self.assertEqual(Reserva.objects.count(), 0)

    def test_admin_must_verify_takeaway_payment_before_confirming(self):
        from APP.usuarios.models import Usuario

        admin = Usuario.objects.create_superuser(
            username='payment-admin',
            email='payment-admin@example.com',
            password='test-password',
            telefono='3118689862',
        )
        self.client.force_login(admin)
        data = self.datos_reserva()
        data.update(tipo_reserva='Para llevar', numero_personas='')
        self.client.post(reverse('gestion_reservas'), {'accion': 'crear', **data})
        reserva = Reserva.objects.get()

        self.client.post(
            reverse('gestion_reservas'),
            {'accion': 'estado', 'reserva_id': str(reserva.pk), 'estado': 'Confirmada'},
        )
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'Pendiente de pago')
        self.assertFalse(reserva.pago_confirmado)
        self.assertEqual(len(mail.outbox), 0)
        without_comprobante = self.client.get(reverse('gestion_reservas'))
        self.assertContains(without_comprobante, 'Esperando comprobante adjunto')
        self.assertNotContains(without_comprobante, 'data-confirm-receipt-action')

        rejected_confirmation = self.client.post(
            reverse('gestion_reservas'),
            {'accion': 'confirmar_pago', 'reserva_id': str(reserva.pk)},
            follow=True,
        )
        self.assertContains(
            rejected_confirmation,
            'No se puede aprobar la reserva hasta recibir un comprobante pendiente con archivo adjunto.',
        )
        reserva.refresh_from_db()
        self.assertFalse(reserva.pago_confirmado)

        comprobante = Comprobante.objects.create(
            reserva=reserva,
            referencia='ref-admin-123',
            direccion_comprobante=self.archivo_comprobante(),
        )
        self.assertEqual(comprobante.estado, 'Pendiente de confirmación')
        notification_response = self.client.get(reverse('gestion_reservas'))
        self.assertContains(notification_response, 'pendiente(s) de validación')
        self.assertContains(notification_response, 'Aprobar')
        self.assertContains(notification_response, 'Rechazar')
        self.assertContains(notification_response, 'data-confirm-receipt-action="approve"')
        self.assertContains(notification_response, 'data-confirm-receipt-action="reject"')
        self.assertContains(notification_response, 'name="motivo_rechazo"')
        self.assertContains(notification_response, 'maxlength="500"')
        self.assertContains(
            notification_response,
            reverse('reserva_cliente', args=[reserva.pk]),
        )
        self.assertContains(
            notification_response,
            reverse('ver_comprobante_cliente', args=[comprobante.pk]),
        )
        archivo_response = self.client.get(
            reverse('ver_comprobante_cliente', args=[comprobante.pk]),
        )
        self.assertEqual(archivo_response.status_code, 200)
        self.assertEqual(archivo_response['Content-Type'], 'image/png')

        response = self.client.post(
            reverse('gestion_reservas'),
            {
                'accion': 'aprobar_comprobante',
                'comprobante_id': str(comprobante.pk),
            },
        )

        self.assertRedirects(response, reverse('gestion_reservas'))
        reserva.refresh_from_db()
        self.assertTrue(reserva.pago_confirmado)
        self.assertIsNotNone(reserva.fecha_pago_confirmado)
        self.assertEqual(reserva.estado, 'Confirmada')
        self.assertEqual(len(mail.outbox), 1)
        comprobante.refresh_from_db()
        self.assertEqual(comprobante.estado, 'Confirmado')

        edit_data = self.datos_reserva()
        edit_data.update(
            accion='editar',
            reserva_id=str(reserva.pk),
            tipo_reserva='Para llevar',
            numero_personas='',
            cantidad_1='3',
        )
        self.client.post(reverse('gestion_reservas'), edit_data)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'Pendiente de pago')
        self.assertFalse(reserva.pago_confirmado)
        self.assertIsNone(reserva.fecha_pago_confirmado)
        self.assertEqual(reserva.total, Decimal('75000.00'))
        comprobante.refresh_from_db()
        self.assertEqual(comprobante.estado, 'Rechazado')

    def test_customer_sees_approval_notification_after_admin_approves_receipt(self):
        reserva, comprobante = self.crear_reserva_con_comprobante('Mesa')
        admin = Usuario.objects.create_superuser(
            username='receipt-approval-admin',
            email='receipt-approval-admin@example.com',
            password='test-password',
            telefono='3118689863',
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse('gestion_reservas'),
            {
                'accion': 'aprobar_comprobante',
                'comprobante_id': str(comprobante.pk),
            },
        )

        self.assertRedirects(response, reverse('gestion_reservas'))
        self.client.force_login(self.user)
        detalle = self.client.get(reverse('reserva_cliente', args=[reserva.pk]))
        self.assertContains(detalle, '¡Comprobante aprobado correctamente!')
        self.assertNotContains(detalle, 'inlinePayForm')
        correo_cliente = mail.outbox[-1]
        self.assertEqual(correo_cliente.to, [self.user.email])
        self.assertIn('aprobado', correo_cliente.subject)
        self.assertIn('Ver los detalles de mi reserva', correo_cliente.alternatives[0].content)
        self.assertIn(
            reverse('reserva_cliente', args=[reserva.pk]),
            correo_cliente.body,
        )

    def test_admin_can_reject_and_customer_can_resubmit_comprobante(self):
        reserva, comprobante = self.crear_reserva_con_comprobante('Para llevar')
        admin = Usuario.objects.create_superuser(
            username='receipt-review-admin',
            email='receipt-review-admin@example.com',
            password='test-password',
            telefono='3118689862',
        )
        self.client.force_login(admin)

        respuesta_sin_motivo = self.client.post(
            reverse('gestion_reservas'),
            {
                'accion': 'rechazar_comprobante',
                'comprobante_id': str(comprobante.pk),
            },
            follow=True,
        )
        self.assertContains(
            respuesta_sin_motivo,
            'Escribe el motivo del rechazo para informar al cliente.',
        )
        comprobante.refresh_from_db()
        self.assertEqual(comprobante.estado, 'Pendiente de confirmación')

        response = self.client.post(
            reverse('gestion_reservas'),
            {
                'accion': 'rechazar_comprobante',
                'comprobante_id': str(comprobante.pk),
                'motivo_rechazo': 'La referencia no coincide con el pago recibido.',
            },
            follow=True,
        )

        self.assertContains(response, f'Comprobante de la reserva #{reserva.pk} rechazado; se informó al cliente.')
        comprobante.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(comprobante.estado, 'Rechazado')
        self.assertEqual(
            comprobante.motivo_rechazo,
            'La referencia no coincide con el pago recibido.',
        )
        self.assertFalse(reserva.pago_confirmado)
        self.assertEqual(reserva.estado, 'Pendiente de pago')
        correo_cliente = mail.outbox[-1]
        self.assertEqual(correo_cliente.to, [self.user.email])
        self.assertIn('rechazado', correo_cliente.subject)
        self.assertIn(
            'La referencia no coincide con el pago recibido.',
            correo_cliente.alternatives[0].content,
        )
        self.assertIn(
            'Ver los detalles de mi reserva',
            correo_cliente.alternatives[0].content,
        )

        self.client.force_login(self.user)
        detalle = self.client.get(reverse('reserva_cliente', args=[reserva.pk]))
        self.assertContains(detalle, 'Comprobante rechazado')
        self.assertContains(detalle, 'La referencia no coincide con el pago recibido.')
        self.assertContains(detalle, 'Enviar un nuevo comprobante')
        self.assertContains(detalle, 'inlinePayForm')
        historial = self.client.get(reverse('mis_reservas'))
        self.assertContains(historial, 'Comprobante: Rechazado')
        self.assertContains(historial, 'La referencia no coincide con el pago recibido.')

        reenvio = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {
                'metodo_pago': 'Nequi',
                'referencia': 'ref-corregida-456',
                'comprobante_archivo': self.archivo_comprobante('corregido.jpg', b'\xff\xd8\xffcontenido'),
            },
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(reenvio.status_code, 200)
        self.assertEqual(reserva.comprobantes.count(), 2)
        detalle_actualizado = self.client.get(reverse('reserva_cliente', args=[reserva.pk]))
        self.assertContains(detalle_actualizado, 'Comprobante enviado correctamente')
        self.assertNotContains(detalle_actualizado, 'Comprobante rechazado')

    def test_admin_can_cancel_any_reservation_and_registers_channel(self):
        admin = Usuario.objects.create_superuser(
            username='channel-admin',
            email='channel-admin@example.com',
            password='test-password',
            telefono='3118689862',
        )
        self.client.force_login(admin)
        data = self.datos_reserva()
        data['canal_origen'] = 'Llamada telefónica'
        self.client.post(reverse('gestion_reservas'), {'accion': 'crear', **data})
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.canal_origen, 'Llamada telefónica')

        cancel_resp = self.client.post(
            reverse('gestion_reservas'),
            {'accion': 'cancelar', 'reserva_id': str(reserva.pk)},
        )
        self.assertRedirects(cancel_resp, reverse('gestion_reservas'))
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'Cancelada')
