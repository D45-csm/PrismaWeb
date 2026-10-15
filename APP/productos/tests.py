from django.test import TestCase
from django.urls import reverse
from .models import CategoriaProducto, Producto, DEFAULT_PRODUCT_IMAGE


class ProductoImagenesOpcionalesTests(TestCase):
    def setUp(self):
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
