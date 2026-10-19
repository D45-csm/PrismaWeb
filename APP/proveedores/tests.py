from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Proveedor


class ProveedorNotificacionesTests(TestCase):
    def setUp(self):
        usuario = get_user_model().objects.create_user(
            username='admin_proveedores',
            password='Clave-segura-123',
            telefono='3001234567',
            is_staff=True,
        )
        self.client.force_login(usuario)

    def test_notificacion_de_proveedor_usa_componente_comun_de_admin(self):
        response = self.client.post(
            reverse('gestion_proveedores'),
            {'nombre': 'Proveedor de prueba', 'activo': 'on'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="django-messages"')
        self.assertContains(response, 'Proveedor registrado exitosamente')
        self.assertContains(response, 'js/admin_messages.js')
        self.assertNotContains(response, 'id="mensajes-sistema"')

    def test_eliminar_proveedor_usa_confirmacion_con_estilo_comun(self):
        Proveedor.objects.create(nombre='Proveedor de prueba')

        response = self.client.get(reverse('gestion_proveedores'))

        self.assertContains(response, 'class="form-eliminar-proveedor"')
        self.assertContains(response, 'data-provider-name="Proveedor de prueba"')
        self.assertNotContains(response, 'onsubmit="return confirm(')
