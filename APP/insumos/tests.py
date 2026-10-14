from django.test import TestCase
from django.urls import reverse

from APP.insumos.models import CategoriaInsumo, Insumo
from APP.usuarios.models import Usuario


class GestionInsumosTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username='admin-insumos',
            email='admin-insumos@example.com',
            password='Clave-segura-2026!',
            telefono='3001234567',
            is_staff=True,
        )
        self.cliente = Usuario.objects.create_user(
            username='cliente-insumos',
            email='cliente-insumos@example.com',
            password='Clave-segura-2026!',
            telefono='3007654321',
        )
        self.categoria = CategoriaInsumo.objects.create(
            nombre='Lácteos',
            descripcion='Ingredientes refrigerados',
        )
        self.insumo = Insumo.objects.create(
            nombre='Leche entera',
            descripcion='Leche fresca',
            categoria=self.categoria,
            unidad_medida='l',
        )
        self.client.force_login(self.admin)
        self.url = reverse('gestion_insumos')

    def test_admin_ve_panel_con_categorias_lista_y_filtros(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestión de insumos')
        self.assertContains(response, 'Lácteos')
        self.assertContains(response, 'Leche entera')
        self.assertContains(response, 'Buscar por nombre o descripción')

    def test_busqueda_categoria_y_estado_filtran_la_lista(self):
        otra_categoria = CategoriaInsumo.objects.create(nombre='Limpieza')
        Insumo.objects.create(
            nombre='Detergente',
            categoria=otra_categoria,
            unidad_medida='u',
        )

        response = self.client.get(
            self.url,
            {'categoria': self.categoria.pk, 'q': 'leche', 'estado': 'activos'},
        )
        self.assertEqual(
            list(response.context['insumos']),
            [self.insumo],
        )

        self.insumo.activo = False
        self.insumo.save(update_fields=['activo'])
        response = self.client.get(self.url, {'estado': 'inactivos'})
        self.assertEqual(list(response.context['insumos']), [self.insumo])

    def test_categoria_no_abre_detalle_hasta_pulsar_la_flecha(self):
        response = self.client.get(self.url, {'categoria': self.categoria.pk})

        self.assertContains(response, 'id="insumoDialog"')
        self.assertContains(
            response,
            f'data-insumo-url="{reverse("detalle_insumo", args=[self.insumo.pk])}"',
        )
        self.assertNotContains(response, '?insumo=')
        self.assertNotContains(response, 'insumo-row-image')

    def test_detalle_insumo_entrega_datos_para_la_ficha_modal(self):
        response = self.client.get(reverse('detalle_insumo', args=[self.insumo.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nombre'], 'Leche entera')
        self.assertEqual(response.json()['categoria'], 'Lácteos')
        self.assertTrue(response.json()['activo'])
        self.assertIn({'id': 'l', 'nombre': 'Litro'}, response.json()['unidades'])

    def test_modal_actualiza_y_desactiva_insumo_sin_perder_historial(self):
        url = reverse('detalle_insumo', args=[self.insumo.pk])
        response = self.client.post(url, {
            'accion': 'editar_insumo',
            f'insumo-{self.insumo.pk}-nombre': 'Leche deslactosada',
            f'insumo-{self.insumo.pk}-descripcion': 'Leche fresca',
            f'insumo-{self.insumo.pk}-categoria': self.categoria.pk,
            f'insumo-{self.insumo.pk}-unidad_medida': 'l',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nombre'], 'Leche deslactosada')

        response = self.client.post(url, {'accion': 'eliminar_insumo'})

        self.assertEqual(response.status_code, 200)
        self.insumo.refresh_from_db()
        self.assertFalse(self.insumo.activo)
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())

    def test_cliente_no_puede_consultar_ni_modificar_detalle_insumo(self):
        self.client.force_login(self.cliente)

        response = self.client.get(reverse('detalle_insumo', args=[self.insumo.pk]))

        self.assertRedirects(
            response,
            f'{reverse("admin_login")}?next={reverse("detalle_insumo", args=[self.insumo.pk])}',
        )
        response = self.client.post(
            reverse('detalle_insumo', args=[self.insumo.pk]),
            {'accion': 'eliminar_insumo'},
        )
        self.assertEqual(response.status_code, 302)
        self.insumo.refresh_from_db()
        self.assertTrue(self.insumo.activo)

    def test_busqueda_de_categorias_filtra_el_panel_izquierdo(self):
        CategoriaInsumo.objects.create(nombre='Limpieza')

        response = self.client.get(self.url, {'categoria_q': 'láct'})

        self.assertEqual(
            list(response.context['categorias'].values_list('nombre', flat=True)),
            ['Lácteos'],
        )
        self.assertEqual(response.context['total_categorias'], 2)

    def test_crea_edita_y_elimina_categoria_vacia(self):
        response = self.client.post(
            self.url,
            {
                'accion': 'crear_categoria',
                'nombre': 'Frutas',
                'descripcion': 'Frutas frescas',
            },
        )
        categoria = CategoriaInsumo.objects.get(nombre='Frutas')
        self.assertRedirects(
            response,
            f'{self.url}?categoria={categoria.pk}',
        )

        response = self.client.post(
            self.url,
            {
                'accion': 'editar_categoria',
                'categoria_id': categoria.pk,
                f'categoria-{categoria.pk}-nombre': 'Frutas frescas',
                f'categoria-{categoria.pk}-descripcion': 'Fruta de temporada',
            },
        )
        categoria.refresh_from_db()
        self.assertEqual(categoria.nombre, 'Frutas frescas')
        self.assertRedirects(
            response,
            f'{self.url}?categoria={categoria.pk}',
        )

        response = self.client.post(
            self.url,
            {
                'accion': 'eliminar_categoria',
                'categoria_id': categoria.pk,
            },
        )
        self.assertFalse(CategoriaInsumo.objects.filter(pk=categoria.pk).exists())
        self.assertRedirects(response, self.url)

    def test_categoria_con_insumos_no_se_puede_eliminar(self):
        response = self.client.post(
            self.url,
            {
                'accion': 'eliminar_categoria',
                'categoria_id': self.categoria.pk,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], self.url)
        self.assertTrue(CategoriaInsumo.objects.filter(pk=self.categoria.pk).exists())
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())
        self.assertContains(response, 'Mueve o elimina sus insumos primero.')

    def test_crea_edita_y_desactiva_insumo_sin_perderlo(self):
        otra_categoria = CategoriaInsumo.objects.create(nombre='Repostería')
        response = self.client.post(
            self.url,
            {
                'accion': 'crear_insumo',
                'nombre': 'Harina',
                'descripcion': 'Harina de trigo',
                'categoria': otra_categoria.pk,
                'unidad_medida': 'kg',
            },
        )
        harina = Insumo.objects.get(nombre='Harina')
        self.assertRedirects(
            response,
            f'{self.url}?categoria={otra_categoria.pk}',
        )

        response = self.client.post(
            self.url,
            {
                'accion': 'editar_insumo',
                'insumo_id': harina.pk,
                f'insumo-{harina.pk}-nombre': 'Harina integral',
                f'insumo-{harina.pk}-descripcion': 'Harina integral de trigo',
                f'insumo-{harina.pk}-categoria': otra_categoria.pk,
                f'insumo-{harina.pk}-unidad_medida': 'kg',
            },
        )
        harina.refresh_from_db()
        self.assertEqual(harina.nombre, 'Harina integral')
        self.assertRedirects(
            response,
            f'{self.url}?categoria={otra_categoria.pk}',
        )

        self.client.post(
            self.url,
            {'accion': 'eliminar_insumo', 'insumo_id': harina.pk},
        )
        harina.refresh_from_db()
        self.assertFalse(harina.activo)

        self.client.post(
            self.url,
            {'accion': 'restaurar_insumo', 'insumo_id': harina.pk},
        )
        harina.refresh_from_db()
        self.assertTrue(harina.activo)

    def test_cliente_no_puede_acceder_al_modulo(self):
        self.client.force_login(self.cliente)

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            f'{reverse("admin_login")}?next={self.url}',
        )

    def test_ids_invalidos_no_modifican_datos(self):
        response = self.client.post(
            self.url,
            {'accion': 'eliminar_insumo', 'insumo_id': 'no-es-un-id'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())
