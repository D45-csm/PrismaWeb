from django.test import TestCase
from django.urls import reverse

from APP.inventario.models import Movimiento
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

    def test_admin_ve_panel_de_categorias_y_busqueda(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestión de insumos')
        self.assertContains(response, 'class="admin-page-heading"')
        self.assertContains(response, 'insumo-active-summary')
        self.assertContains(response, 'css/admin_crud.css')
        self.assertContains(response, 'js/admin_crud.js')
        self.assertContains(response, 'class="admin-crud-sidebar insumo-sidebar"')
        self.assertContains(response, 'class="admin-crud-main insumo-main-panel"')
        self.assertContains(response, f'action="{self.url}"')
        self.assertContains(response, 'class="insumo-filter-bar"')
        self.assertContains(response, 'admin-status-filter')
        self.assertContains(response, 'admin-status-options')
        self.assertContains(response, 'Lácteos')
        self.assertContains(response, 'Crear categoría')
        self.assertContains(response, 'id="insumoCreateDialog"')
        self.assertContains(response, 'admin-crud-editor-dialog')
        self.assertContains(response, 'data-open-insumo-create')
        self.assertContains(response, 'Encuentra un insumo')
        self.assertNotContains(response, 'data-insumo-row=')
        self.assertContains(response, 'Tamaño / unidad')

    def test_busqueda_por_nombre_categoria_y_unidad_y_filtro_de_estado(self):
        otra_categoria = CategoriaInsumo.objects.create(nombre='Limpieza')
        Insumo.objects.create(
            nombre='Detergente',
            categoria=otra_categoria,
            unidad_medida='u',
        )

        response = self.client.get(
            self.url,
            {'q': 'leche', 'campo': 'nombre', 'estado': 'activos'},
        )
        self.assertEqual(
            list(response.context['insumos']),
            [self.insumo],
        )

        response = self.client.get(
            self.url,
            {'q': 'láct', 'campo': 'categoria'},
        )
        self.assertEqual(list(response.context['insumos']), [self.insumo])

        response = self.client.get(
            self.url,
            {'q': 'litro', 'campo': 'tamano'},
        )
        self.assertEqual(list(response.context['insumos']), [self.insumo])

        response = self.client.get(
            self.url,
            {'categoria': self.categoria.pk, 'q': 'detergente', 'estado': 'activos'},
        )
        self.assertEqual(
            list(response.context['insumos'].values_list('nombre', flat=True)),
            ['Detergente'],
        )

        self.insumo.activo = False
        self.insumo.save(update_fields=['activo'])
        response = self.client.get(self.url, {'estado': 'inactivos'})
        self.assertEqual(list(response.context['insumos']), [self.insumo])

    def test_categoria_no_filtra_insumos_y_edicion_abre_formulario_modal(self):
        response = self.client.get(self.url, {'categoria': self.categoria.pk})

        self.assertContains(response, 'id="insumoDialog"')
        self.assertNotContains(response, 'data-insumo-row=')
        response = self.client.get(self.url, {'editar_categoria': self.categoria.pk})
        self.assertEqual(response.context['categoria_modal'], 'editar')
        self.assertContains(response, 'data-category-edit-form')
        self.assertContains(response, 'Editar categoría')
        self.assertContains(
            self.client.get(self.url, {'q': 'leche'}),
            f'data-insumo-url="{reverse("detalle_insumo", args=[self.insumo.pk])}"',
        )
        self.assertNotContains(response, 'insumo-row-image')

    def test_detalle_insumo_entrega_datos_para_la_ficha_modal(self):
        response = self.client.get(reverse('detalle_insumo', args=[self.insumo.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nombre'], 'Leche entera')
        self.assertEqual(response.json()['categoria'], 'Lácteos')
        self.assertTrue(response.json()['activo'])
        self.assertIn({'id': 'l', 'nombre': 'Litro'}, response.json()['unidades'])
        management_response = self.client.get(self.url)
        self.assertContains(management_response, 'insumo-dialog-delete')
        self.assertContains(management_response, 'id="deleteInsumoDialog"')

    def test_modal_actualiza_y_switch_activa_o_desactiva_insumo(self):
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
        self.assertEqual(
            response.json()['message'],
            'Insumo actualizado correctamente.',
        )

        page = self.client.get(self.url)
        self.assertContains(page, 'js/admin_messages.js')
        self.assertContains(page, 'js/insumos.js?v=1')

        response = self.client.post(
            url,
            {'accion': 'cambiar_disponibilidad', 'activo': 'false'},
        )

        self.assertEqual(response.status_code, 200)
        self.insumo.refresh_from_db()
        self.assertFalse(self.insumo.activo)
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())

        response = self.client.post(
            url,
            {'accion': 'cambiar_disponibilidad', 'activo': 'true'},
        )
        self.assertEqual(response.status_code, 200)
        self.insumo.refresh_from_db()
        self.assertTrue(self.insumo.activo)

        response = self.client.post(
            url,
            {'accion': 'cambiar_disponibilidad', 'activo': 'invalid'},
        )
        self.assertEqual(response.status_code, 400)

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

    def test_admin_puede_eliminar_insumo_desde_su_ficha(self):
        response = self.client.post(
            reverse('detalle_insumo', args=[self.insumo.pk]),
            {'accion': 'eliminar_insumo'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['deleted'])
        self.assertFalse(Insumo.objects.filter(pk=self.insumo.pk).exists())

    def test_no_se_puede_eliminar_insumo_con_movimientos_de_inventario(self):
        Movimiento.objects.create(
            origen='AJUSTE',
            accion='ENTRADA',
            insumo=self.insumo,
            cantidad='1.000',
            unidad_medida='l',
        )

        response = self.client.post(
            reverse('detalle_insumo', args=[self.insumo.pk]),
            {'accion': 'eliminar_insumo'},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn('movimientos de inventario o compras', response.json()['error'])
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())

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
        self.assertRedirects(response, self.url)

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
        self.assertRedirects(response, self.url)

        response = self.client.post(
            self.url,
            {
                'accion': 'eliminar_categoria',
                'categoria_id': categoria.pk,
            },
        )
        self.assertFalse(CategoriaInsumo.objects.filter(pk=categoria.pk).exists())
        self.assertRedirects(response, self.url)

    def test_formulario_de_crear_insumo_abre_dialogo_si_hay_errores(self):
        response = self.client.post(
            self.url,
            {
                'accion': 'crear_insumo',
                'nombre': '',
                'descripcion': '',
                'categoria': self.categoria.pk,
                'unidad_medida': 'l',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="insumoCreateDialog"')
        self.assertContains(response, 'data-open="crear"')
        self.assertContains(response, 'data-open-insumo-create')
        self.assertTrue(response.context['insumo_form'].errors)

    def test_eliminar_categoria_usa_confirmacion_visual_no_alerta_nativa(self):
        CategoriaInsumo.objects.create(nombre='Categoría vacía')

        response = self.client.get(self.url)

        self.assertContains(response, 'id="deleteCategoryDialog"')
        self.assertContains(response, 'data-confirm-category-delete')
        self.assertNotContains(response, 'onclick="return confirm(')

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
        self.assertContains(response, 'Reasigna o desactiva sus insumos primero.')

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
        self.assertRedirects(response, f'{self.url}?q=Harina&campo=nombre')

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
        self.assertRedirects(response, self.url)

        self.client.post(
            self.url,
            {'accion': 'cambiar_disponibilidad', 'insumo_id': harina.pk, 'activo': 'false'},
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

    def test_eliminar_insumo_requiere_un_id_valido(self):
        response = self.client.post(
            reverse('detalle_insumo', args=[self.insumo.pk + 999]),
            {'accion': 'eliminar_insumo'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())
