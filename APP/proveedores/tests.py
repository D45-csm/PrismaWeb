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
            {
                'accion': 'crear_proveedor',
                'nombre': 'Proveedor de prueba',
                'activo': 'on',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="django-messages"')
        self.assertContains(response, 'Proveedor registrado exitosamente')
        self.assertContains(response, 'js/admin_messages.js')
        self.assertContains(response, 'css/admin_crud.css')
        self.assertContains(response, 'Proveedores')
        self.assertContains(response, 'class="admin-crud-sidebar')
        self.assertContains(response, 'class="admin-crud-main')
        self.assertContains(response, 'data-open-crud-editor')
        self.assertContains(response, 'class="insumo-list-heading"')
        self.assertNotContains(response, 'id="mensajes-sistema"')

    def test_eliminar_proveedor_usa_confirmacion_con_estilo_comun(self):
        Proveedor.objects.create(nombre='Proveedor de prueba')

        response = self.client.get(reverse('gestion_proveedores'))

        self.assertContains(response, 'class="insumo-row insumo-row--record')
        self.assertContains(response, 'data-crud-delete-url=')
        self.assertContains(response, 'data-crud-delete-name="Proveedor de prueba"')
        self.assertContains(response, 'id="crudDeleteDialog"')
        self.assertContains(response, 'js/admin_crud.js?v=8')

    def test_proveedor_se_edita_en_dialogo_y_comparte_filtros_de_insumos(self):
        proveedor = Proveedor.objects.create(nombre='Distribuidora Prisma')

        response = self.client.get(
            reverse('gestion_proveedores'),
            {'editar_proveedor': proveedor.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="supplierEditorDialog"')
        self.assertContains(response, 'admin-crud-editor-dialog')
        self.assertContains(response, 'supplier-editor-availability')
        self.assertContains(response, 'Proveedor inactivo')
        self.assertContains(response, 'data-open="editar"')
        self.assertContains(response, 'class="insumo-filter-bar"')
        self.assertContains(response, 'class="admin-crud-sidebar insumo-sidebar"')
        self.assertContains(
            response,
            f'action="{reverse("gestion_proveedores")}" class="insumo-filter-bar"',
        )

    def test_buscar_desde_edicion_no_reabre_formulario_si_no_hay_resultados(self):
        response = self.client.get(
            reverse('gestion_proveedores'),
            {'q': 'sin coincidencias'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No encontramos proveedores')
        self.assertContains(response, 'data-open=""')
        self.assertNotContains(response, 'data-open="editar"')

    def test_estado_de_proveedor_se_actualiza_con_endpoint_protegido(self):
        proveedor = Proveedor.objects.create(nombre='Distribuidora Prisma')

        response = self.client.post(
            reverse('cambiar_estado_proveedor', args=[proveedor.pk]),
            {'activo': 'false'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['activo'])
        proveedor.refresh_from_db()
        self.assertFalse(proveedor.activo)

    def test_endpoint_de_estado_no_permite_usuarios_anonimos(self):
        proveedor = Proveedor.objects.create(nombre='Distribuidora Prisma')
        self.client.logout()

        response = self.client.post(
            reverse('cambiar_estado_proveedor', args=[proveedor.pk]),
            {'activo': 'false'},
        )

        self.assertEqual(response.status_code, 302)
        proveedor.refresh_from_db()
        self.assertTrue(proveedor.activo)
