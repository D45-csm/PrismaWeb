from django.test import TestCase
from django.urls import reverse

from APP.insumos.models import CategoriaInsumo, Insumo
from APP.usuarios.models import Usuario

from .models import Proveedor


class GestionProveedoresTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
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
        self.client.force_login(self.admin)
        self.url = reverse('gestion_proveedores')

    def test_admin_consulta_formulario_proveedores_vacio(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aún no hay proveedores')
        self.assertContains(response, 'Registrar proveedor')

    def test_admin_crea_edita_y_desactiva_proveedor(self):
        response = self.client.post(
            reverse('guardar_proveedor'),
            {
                'accion': 'crear',
                'nombre': 'Lácteos del Valle',
                'direccion': 'Calle 10',
                'telefono': '3001234567',
                'email': 'ventas@example.com',
            },
        )
        proveedor = Proveedor.objects.get(nombre='Lácteos del Valle')
        self.assertRedirects(
            response,
            f'{self.url}?proveedor={proveedor.pk}',
        )

        response = self.client.get(self.url, {'proveedor': proveedor.pk})
        self.assertContains(
            response,
            f'name="proveedor-{proveedor.pk}-nombre"',
        )

        response = self.client.post(
            reverse('guardar_proveedor'),
            {
                'accion': 'editar',
                'proveedor_id': proveedor.pk,
                f'proveedor-{proveedor.pk}-nombre': 'Lácteos del Valle Norte',
                f'proveedor-{proveedor.pk}-direccion': 'Avenida 20',
                f'proveedor-{proveedor.pk}-telefono': '3007654321',
                f'proveedor-{proveedor.pk}-email': 'norte@example.com',
            },
        )
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.nombre, 'Lácteos del Valle Norte')
        self.assertEqual(proveedor.direccion, 'Avenida 20')
        self.assertRedirects(
            response,
            f'{self.url}?proveedor={proveedor.pk}',
        )

        response = self.client.post(
            reverse('cambiar_estado_proveedor', args=[proveedor.pk]),
        )
        proveedor.refresh_from_db()
        self.assertFalse(proveedor.activo)
        self.assertRedirects(response, self.url)

    def test_no_permite_nombres_de_proveedor_duplicados(self):
        Proveedor.objects.create(nombre='Distribuidor Central')

        response = self.client.post(
            reverse('guardar_proveedor'),
            {'accion': 'crear', 'nombre': ' distribuidor central '},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Proveedor.objects.count(), 1)
        self.assertContains(
            response,
            'Ya existe un proveedor con ese nombre.',
            status_code=400,
        )

    def test_proveedor_desactivado_no_se_puede_asignar_a_un_insumo_nuevo(self):
        proveedor = Proveedor.objects.create(
            nombre='Proveedor inactivo',
            activo=False,
        )
        categoria = CategoriaInsumo.objects.create(nombre='Bebidas')

        response = self.client.post(
            reverse('gestion_insumos'),
            {
                'accion': 'crear_insumo',
                'nombre': 'Leche de prueba',
                'categoria': categoria.pk,
                'proveedor_referencia': proveedor.pk,
                'unidad_medida': 'l',
            },
        )

        self.assertFalse(Insumo.objects.filter(nombre='Leche de prueba').exists())
        self.assertContains(response, 'Selecciona un proveedor activo válido.')

    def test_cliente_no_puede_administrar_proveedores(self):
        self.client.force_login(self.cliente)

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            f'{reverse("admin_login")}?next={self.url}',
        )

# Create your tests here.
