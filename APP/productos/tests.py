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
