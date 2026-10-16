from django.contrib import messages
from django.test import TestCase
from django.urls import reverse

from APP.usuarios.models import Usuario

from .models import Proveedor


class ProveedorCrudTests(TestCase):
    def setUp(self):
        self.administrador = Usuario.objects.create_user(
            username='admin-proveedores',
            email='admin-proveedores@example.com',
            telefono='3001234567',
            password='Clave-segura-2026!',
            is_staff=True,
        )
        self.cliente = Usuario.objects.create_user(
            username='cliente-proveedores',
            email='cliente-proveedores@example.com',
            telefono='3007654321',
            password='Clave-segura-2026!',
        )
        self.proveedor = Proveedor.objects.create(
            nombre='Frutas del Valle',
            direccion='Calle 10',
            telefono='3001112233',
            email='ventas@example.com',
        )

    def test_lista_requiere_autenticacion(self):
        response = self.client.get(reverse('proveedores_lista'))

        self.assertRedirects(
            response,
            f'{reverse("admin_login")}?next={reverse("proveedores_lista")}',
        )

    def test_cliente_autenticado_no_puede_administrar_proveedores(self):
        self.client.force_login(self.cliente)

        response = self.client.get(reverse('proveedores_lista'))

        self.assertEqual(response.status_code, 403)

    def test_administrador_ve_lista_datatables_y_titulo_dinamico(self):
        self.client.force_login(self.administrador)

        response = self.client.get(reverse('proveedores_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestión de proveedores')
        self.assertContains(response, 'Frutas del Valle')
        self.assertContains(response, 'id="proveedoresTable"')
        self.assertContains(response, 'dataTables.min.js')
        self.assertContains(response, 'js/modulos/proveedores/listado.js')
        self.assertContains(response, 'id="proveedorDeleteForm"')
        self.assertContains(response, 'data-delete-url="/proveedores/1/eliminar/"')
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_lista_vacia_no_inyecta_una_fila_invalida_en_datatables(self):
        self.client.force_login(self.administrador)
        self.proveedor.delete()

        response = self.client.get(reverse('proveedores_lista'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'colspan="6"')

    def test_administrador_crea_proveedor(self):
        self.client.force_login(self.administrador)

        response = self.client.post(
            reverse('proveedores_crear'),
            {
                'nombre': 'Lácteos Andinos',
                'direccion': 'Carrera 12',
                'telefono': '3009998877',
                'email': 'contacto@lacteos.example',
                'activo': 'on',
            },
        )

        self.assertRedirects(response, reverse('proveedores_lista'))
        self.assertTrue(
            Proveedor.objects.filter(nombre='Lácteos Andinos').exists(),
        )
        self.assertIn(
            'Proveedor creado correctamente.',
            [str(message) for message in response.wsgi_request._messages],
        )

    def test_formulario_rechaza_correo_invalido(self):
        self.client.force_login(self.administrador)

        response = self.client.post(
            reverse('proveedores_crear'),
            {
                'nombre': 'Proveedor inválido',
                'email': 'no-es-correo',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escribe una dirección de correo válida.')
        self.assertFalse(
            Proveedor.objects.filter(nombre='Proveedor inválido').exists(),
        )

    def test_administrador_edita_proveedor(self):
        self.client.force_login(self.administrador)

        response = self.client.post(
            reverse('proveedores_editar', args=[self.proveedor.pk]),
            {
                'nombre': 'Frutas del Valle Actualizado',
                'direccion': 'Avenida 20',
                'telefono': '3004445566',
                'email': 'nuevo@example.com',
                'activo': 'on',
            },
        )

        self.assertRedirects(response, reverse('proveedores_lista'))
        self.proveedor.refresh_from_db()
        self.assertEqual(self.proveedor.nombre, 'Frutas del Valle Actualizado')
        self.assertEqual(self.proveedor.direccion, 'Avenida 20')

    def test_eliminar_requiere_confirmacion_post(self):
        self.client.force_login(self.administrador)

        response = self.client.get(
            reverse('proveedores_eliminar', args=[self.proveedor.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-confirm-post')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertTrue(Proveedor.objects.filter(pk=self.proveedor.pk).exists())

        response = self.client.post(
            reverse('proveedores_eliminar', args=[self.proveedor.pk]),
        )

        self.assertRedirects(response, reverse('proveedores_lista'))
        self.assertFalse(Proveedor.objects.filter(pk=self.proveedor.pk).exists())
        self.assertEqual(
            list(response.wsgi_request._messages)[0].level,
            messages.SUCCESS,
        )
