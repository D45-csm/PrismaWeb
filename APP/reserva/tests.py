from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import unquote

from django.core import mail
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

    def test_reserva_is_saved_emailed_and_returns_whatsapp_link(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('reservas'),
            self.valid_data(),
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['email_sent'])
        self.assertIn('wa.me/573118689862', response.json()['whatsapp_url'])
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.nombre_cliente, 'Cliente Prisma')
        detalle = reserva.lineas.get()
        self.assertEqual(detalle.nombre_producto, 'Café Chocolate')
        self.assertEqual(detalle.cantidad, 2)
        self.assertEqual(detalle.precio_unitario, Decimal('15000'))
        self.assertEqual(reserva.hora, None)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['reservas@example.com'])

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
    def test_missing_email_credentials_are_reported_without_losing_reserva(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('reservas'),
            self.valid_data(),
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['email_sent'])
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertIn('Completa tu pago', response.json()['message'])


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

    def test_public_reservation_and_lookup_pages_render(self):
        response = self.client.get(reverse('reservas'))
        lookup_response = self.client.get(reverse('consultar_reserva'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Planea tu visita')
        self.assertContains(response, 'name="hora"')
        self.assertContains(response, 'Elige tu postre')
        self.assertContains(response, f'href="{reverse("productos")}#productosGrid"')
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
        self.assertContains(
            response,
            reverse('reserva_cliente', args=[own_reservation.pk]),
        )
        self.assertNotContains(response, 'Reserva de otra persona')

    def test_public_reservation_saves_products_and_sends_notification(self):
        response = self.client.post(
            reverse('reservas'),
            self.datos_reserva(),
            HTTP_ACCEPT='application/json',
        )

        self.assertEqual(response.status_code, 201)
        reserva = Reserva.objects.get()
        self.assertEqual(reserva.numero_personas, 4)
        self.assertEqual(reserva.tipo_reserva, 'Mesa')
        self.assertEqual(reserva.estado, 'Pendiente')
        self.assertEqual(reserva.lineas.get().cantidad, 2)
        self.assertIn(f'/reserva/consultar/{reserva.pk}/', response.json()['next_url'])
        self.assertIn('SOLICITUD DE RESERVA DE MESA', unquote(response.json()['whatsapp_url']))
        self.assertEqual(response.json()['reservation_id'], reserva.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f'Reserva #{reserva.pk}', mail.outbox[0].body)
        detail_response = self.client.get(response.json()['next_url'])
        self.assertContains(detail_response, 'Reserva de mesa sin prepago')
        self.assertContains(detail_response, 'Enviar solicitud por WhatsApp')

    def test_anonymous_takeaway_is_rejected_requiring_login(self):
        data = self.datos_reserva()
        data.update(tipo_reserva='Para llevar', numero_personas='')
        response = self.client.post(
            reverse('reservas'),
            data,
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.json()['require_login'])

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
        self.assertEqual(reserva.estado, 'Pendiente de pago')
        self.assertFalse(reserva.pago_confirmado)
        self.assertEqual(reserva.total, Decimal('50000.00'))
        self.assertIn('completa tu pago', response.json()['message'].lower())
        self.assertIn('Total del pedido: $50.000 COP', unquote(response.json()['whatsapp_url']))
        detail_response = self.client.get(response.json()['next_url'])
        self.assertContains(detail_response, 'Pago anticipado pendiente')
        self.assertContains(detail_response, 'Coordinar pago por WhatsApp')
        self.assertContains(detail_response, 'Cancelar reserva')

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

    def test_customer_can_complete_payment_and_receives_sweet_confirmation_message(self):
        self.client.force_login(self.user)
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

        # Complete payment
        payment_response = self.client.post(
            reverse('pagar_reserva_cliente', args=[reserva.pk]),
            {'metodo_pago': 'Nequi', 'referencia': '123456'},
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(payment_response.status_code, 200)
        self.assertTrue(payment_response.json()['ok'])
        self.assertTrue(payment_response.json()['pago_confirmado'])
        self.assertIn('Pago recibido con éxito', payment_response.json()['message'])
        self.assertIn('Nequi', payment_response.json()['metodo_pago'])

        reserva.refresh_from_db()
        self.assertTrue(reserva.pago_confirmado)
        self.assertEqual(reserva.estado, 'Confirmada')
        self.assertEqual(reserva.metodo_pago, 'Nequi')
        self.assertIsNotNone(reserva.fecha_pago_confirmado)

    def test_past_reservation_is_rejected(self):
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

    def test_reservation_rejects_times_outside_business_hours(self):
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
        confirm_response = self.client.post(
            reverse('gestion_reservas'),
            {
                'accion': 'estado',
                'reserva_id': str(reserva.pk),
                'estado': 'Confirmada',
            },
        )
        self.assertRedirects(confirm_response, reverse('gestion_reservas'))
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('confirmada', mail.outbox[1].subject)

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

        response = self.client.post(
            reverse('gestion_reservas'),
            {'accion': 'confirmar_pago', 'reserva_id': str(reserva.pk)},
        )

        self.assertRedirects(response, reverse('gestion_reservas'))
        reserva.refresh_from_db()
        self.assertTrue(reserva.pago_confirmado)
        self.assertIsNotNone(reserva.fecha_pago_confirmado)
        self.assertEqual(reserva.estado, 'Confirmada')
        self.assertEqual(len(mail.outbox), 2)

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
