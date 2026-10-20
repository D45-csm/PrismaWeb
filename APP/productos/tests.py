from io import BytesIO
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .forms import ProductoForm
from .models import CategoriaProducto, Producto, DEFAULT_PRODUCT_IMAGE


class ProductoImagenesOpcionalesTests(TestCase):
    def setUp(self):
        usuario_model = get_user_model()
        self.admin = usuario_model.objects.create_user(
            username='admin_productos',
            password='Clave-segura-123',
            telefono='3001234567',
            is_staff=True,
        )
        self.client.force_login(self.admin)
        self.categoria = CategoriaProducto.objects.create(
            nombre='Postres',
            descripcion='Postres de prueba',
        )

    def datos_producto(self):
        return {
            'nombre': 'Torta de prueba',
            'descripcion': 'Producto de prueba',
            'precio': '12000',
            'categoria': str(self.categoria.id),
        }

    def test_crear_producto_sin_imagenes_usa_imagen_predeterminada(self):
        response = self.client.post(
            reverse('crear_producto'),
            self.datos_producto(),
        )

        self.assertRedirects(response, reverse('lista_productos'))
        producto = Producto.objects.get(nombre='Torta de prueba')
        self.assertEqual(producto.imagen_principal.name, DEFAULT_PRODUCT_IMAGE)
        self.assertFalse(producto.imagen_2)
        self.assertFalse(producto.imagen_3)
        self.assertFalse(producto.imagen_4)

    def test_editar_producto_sin_imagenes_nuevas_es_valido(self):
        producto = Producto.objects.create(
            categoria=self.categoria,
            nombre='Torta anterior',
            descripcion='Descripción anterior',
            precio='10000.00',
        )

        datos = self.datos_producto()
        response = self.client.post(
            reverse('editar_producto', args=[producto.id]),
            datos,
        )

        self.assertRedirects(response, reverse('lista_productos'))
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, 'Torta de prueba')
        self.assertEqual(producto.imagen_principal.name, DEFAULT_PRODUCT_IMAGE)


class ProductoSeguridadTests(TestCase):
    def setUp(self):
        self.categoria = CategoriaProducto.objects.create(
            nombre='Postres',
            descripcion='Postres de prueba',
        )
        self.producto = Producto.objects.create(
            categoria=self.categoria,
            nombre='Torta',
            descripcion='Producto de prueba',
            precio='10000.00',
        )

    def test_crud_de_productos_usa_plantilla_y_estilos_compartidos(self):
        admin = get_user_model().objects.create_user(
            username='admin_productos_crud',
            password='Clave-segura-123',
            telefono='3005678123',
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('lista_productos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'insumo-dashboard product-admin-page')
        self.assertContains(response, 'class="admin-crud-sidebar insumo-sidebar"')
        self.assertContains(response, 'class="admin-crud-main insumo-main-panel"')
        self.assertContains(response, 'class="admin-page-heading"')
        self.assertContains(response, 'Crear producto')
        self.assertContains(response, 'css/admin_crud.css')
        self.assertContains(response, 'class="insumo-filter-bar"')
        self.assertContains(response, 'class="insumo-row insumo-row--record')
        self.assertContains(response, 'id="crudDetailDialog"')
        self.assertContains(response, 'id="crudDeleteDialog"')
        self.assertContains(response, 'data-open-crud-editor')
        self.assertContains(response, 'class="insumo-list-heading"')

        response = self.client.get(reverse('editar_producto', args=[self.producto.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="productEditorDialog"')
        self.assertContains(response, 'data-open="editar"')
        self.assertContains(response, 'name="imagen_principal"')
        self.assertContains(
            response,
            f'action="{reverse("lista_productos")}" class="insumo-filter-bar"',
        )

    def test_buscar_desde_editor_no_reabre_editor_cuando_no_hay_resultados(self):
        admin = get_user_model().objects.create_user(
            username='admin_productos_busqueda',
            password='Clave-segura-123',
            telefono='3005678126',
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse('lista_productos'),
            {'q': 'sin coincidencias', 'estado': 'activos'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No encontramos productos')
        self.assertContains(response, 'id="productEditorDialog"')
        self.assertContains(response, 'data-open=""')
        self.assertNotContains(response, 'data-open="editar"')

    def test_lista_publica_conserva_sus_estilos_de_productos(self):
        response = self.client.get(reverse('lista_productos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'css/gestion_productos.css')

    def test_ficha_y_estado_de_producto_siguen_el_patron_de_insumos(self):
        admin = get_user_model().objects.create_user(
            username='admin_productos_dialogos',
            password='Clave-segura-123',
            telefono='3005678124',
            is_staff=True,
        )
        self.client.force_login(admin)

        detail_url = reverse('detalle_producto', args=[self.producto.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nombre'], self.producto.nombre)
        self.assertEqual(response.json()['meta'][0], self.categoria.nombre)

        response = self.client.post(detail_url, {'activo': 'false'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['activo'])
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)

    def test_endpoint_de_estado_no_permite_usuarios_anonimos(self):
        response = self.client.post(
            reverse('detalle_producto', args=[self.producto.pk]),
            {'activo': 'false'},
        )

        self.assertEqual(response.status_code, 302)
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)

    def test_busqueda_y_filtro_de_categoria_en_el_listado_de_productos(self):
        admin = get_user_model().objects.create_user(
            username='admin_productos_filtros',
            password='Clave-segura-123',
            telefono='3005678125',
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse('lista_productos'),
            {'q': 'Torta', 'categoria': self.categoria.pk, 'estado': 'activos'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['productos']), [self.producto])

    def test_visitante_no_puede_abrir_vistas_de_escritura(self):
        rutas = (
            ('crear_producto', []),
            ('editar_producto', [self.producto.id]),
        )
        for nombre_ruta, args in rutas:
            with self.subTest(ruta=nombre_ruta):
                response = self.client.get(reverse(nombre_ruta, args=args))
                self.assertRedirects(
                    response,
                    f"{reverse('admin_login')}?next={reverse(nombre_ruta, args=args)}",
                    fetch_redirect_response=False,
                )

    def test_visitante_no_puede_modificar_producto_por_post(self):
        response = self.client.post(
            reverse('editar_producto', args=[self.producto.id]),
            {
                'nombre': 'Producto alterado',
                'descripcion': 'Descripción alterada',
                'precio': '1.00',
                'categoria': str(self.categoria.id),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Torta')

    def test_visitante_no_puede_eliminar_producto_por_post(self):
        response = self.client.post(
            reverse('eliminar_producto', args=[self.producto.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())

    def test_usuario_no_administrador_no_puede_crear_producto(self):
        usuario = get_user_model().objects.create_user(
            username='cliente_productos',
            password='Clave-segura-123',
            telefono='3007654321',
        )
        self.client.force_login(usuario)

        response = self.client.post(
            reverse('crear_producto'),
            {
                'nombre': 'Torta nueva',
                'descripcion': 'Descripción',
                'precio': '12000.00',
                'categoria': str(self.categoria.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Producto.objects.filter(nombre='Torta nueva').exists())

    def test_eliminar_producto_requiere_post_y_usuario_administrador(self):
        usuario_model = get_user_model()
        admin = usuario_model.objects.create_user(
            username='admin_productos_delete',
            password='Clave-segura-123',
            telefono='3001122334',
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse('eliminar_producto', args=[self.producto.id])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())

        response = self.client.post(
            reverse('eliminar_producto', args=[self.producto.id])
        )

        self.assertRedirects(response, reverse('lista_productos'))
        self.assertFalse(Producto.objects.filter(pk=self.producto.pk).exists())

    def test_formulario_rechaza_archivo_que_no_es_imagen(self):
        usuario_model = get_user_model()
        admin = usuario_model.objects.create_user(
            username='admin_productos_upload',
            password='Clave-segura-123',
            telefono='3009988776',
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse('crear_producto'),
            {
                'nombre': 'Producto inseguro',
                'descripcion': 'Prueba de carga',
                'precio': '12000.00',
                'categoria': str(self.categoria.id),
                'imagen_principal': SimpleUploadedFile(
                    'archivo.png',
                    b'<script>alert(1)</script>',
                    content_type='image/png',
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Producto.objects.filter(nombre='Producto inseguro').exists()
        )
        self.assertIn(
            'imagen_principal',
            response.context['form'].errors,
        )

    def test_formulario_normaliza_extension_segun_el_contenido_de_imagen(self):
        buffer = BytesIO()
        Image.new('RGB', (1, 1), color='red').save(buffer, format='PNG')
        form = ProductoForm(
            data={
                'nombre': 'Producto con imagen',
                'descripcion': 'Imagen válida',
                'precio': '12000.00',
                'categoria': str(self.categoria.id),
            },
            files={
                'imagen_principal': SimpleUploadedFile(
                    'archivo.jpg',
                    buffer.getvalue(),
                    content_type='image/png',
                ),
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertRegex(
            form.cleaned_data['imagen_principal'].name,
            r'^[0-9a-f]{32}\.png$',
        )
